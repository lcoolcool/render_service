"""Celery异步任务定义"""
import asyncio
import logging
import time
import threading
from pathlib import Path
from celery import Task
from celery.exceptions import Ignore
from app.celery_app.celery import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """支持数据库操作的任务基类"""
    _db_initialized = False
    _init_lock = threading.Lock()  # 线程锁，确保数据库初始化的线程安全

    def before_start(self, task_id, args, kwargs):
        """任务开始前初始化数据库连接"""
        # 使用双重检查锁定模式（Double-Checked Locking）
        if not self._db_initialized:
            with self._init_lock:
                # 再次检查，避免重复初始化
                if not self._db_initialized:
                    from tortoise import Tortoise
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(
                        Tortoise.init(
                            db_url=settings.database_url,
                            modules={"models": ["app.models.task", "app.models.frame"]}
                        )
                    )
                    self._db_initialized = True


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.render_task",
    acks_late=True
)
def render_task(self, task_id: int):
    """
    主渲染任务

    Args:
        task_id: 渲染任务ID
    """
    from app.models.task import RenderTask, TaskStatus
    from app.models.frame import RenderFrame, FrameStatus
    from app.services.renderer import get_renderer

    loop = asyncio.get_event_loop()

    # 获取任务信息
    task = loop.run_until_complete(
        RenderTask.get(id=task_id).prefetch_related("frames")
    )

    # 检查任务是否被取消
    if task.status == TaskStatus.CANCELLED:
        raise Ignore()

    # 更新任务状态为运行中
    task.status = TaskStatus.RUNNING
    task.celery_task_id = self.request.id
    loop.run_until_complete(task.save())

    # 初始化文件准备服务（在try块外部，确保在所有分支中都可用）
    from app.services.file_preparation import FilePreparationService
    file_prep_service = FilePreparationService()

    try:
        # 1. 准备工程文件（从OSS下载并解压）

        try:
            project_file, workspace_dir, renders_dir, thumbnails_dir = file_prep_service.prepare_project_files(
                unionid=task.unionid,
                task_id=task.id,
                oss_file_path=task.oss_file_path,
                is_compressed=task.is_compressed,
                render_engine=task.render_engine
            )

            # 更新任务的本地文件路径和工作空间
            task.project_file = str(project_file)
            task.workspace_dir = str(workspace_dir)
            task.renders_dir = str(renders_dir)
            task.thumbnails_dir = str(thumbnails_dir)
            loop.run_until_complete(task.save())

        except Exception as e:
            # 文件准备失败
            task.status = TaskStatus.FAILED
            task.error_message = f"文件准备失败: {str(e)}"
            loop.run_until_complete(task.save())
            raise Ignore()

        # 2. 获取渲染引擎
        renderer = get_renderer(task.render_engine)

        # 3. 获取所有待渲染的帧
        frames = loop.run_until_complete(
            RenderFrame.filter(task_id=task_id, status=FrameStatus.PENDING).all()
        )

        # 逐帧渲染
        for frame in frames:
            # 再次检查是否被取消
            task = loop.run_until_complete(RenderTask.get(id=task_id))
            if task.status == TaskStatus.CANCELLED:
                raise Ignore()

            # 更新帧状态为渲染中
            frame.status = FrameStatus.RENDERING
            loop.run_until_complete(frame.save())

            try:
                # 执行渲染
                start_time = time.time()
                output_path, stdout, stderr = renderer.render_frame(
                    project_file=task.project_file,
                    frame_number=frame.frame_number,
                    output_dir=Path(task.renders_dir),
                    engine_conf=task.render_engine_conf
                )
                render_time = time.time() - start_time

                # 更新帧信息
                frame.status = FrameStatus.COMPLETED
                frame.output_path = str(output_path)
                frame.render_time = render_time
                frame.stdout = stdout
                frame.stderr = stderr
                loop.run_until_complete(frame.save())

                # 异步生成缩略图（传递必要的上下文信息）
                generate_thumbnail.delay(frame.id, task.unionid, task.id)

                # 更新任务进度
                task.completed_frames += 1
                loop.run_until_complete(task.save())

            except Exception as e:
                # 帧渲染失败
                frame.status = FrameStatus.FAILED
                frame.error_message = str(e)
                # 尝试保存渲染日志（如果有的话）
                # 注意：异常时可能没有日志，但也可能是在后续步骤失败
                loop.run_until_complete(frame.save())

                # 记录错误但继续渲染其他帧
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "frame": frame.frame_number,
                        "status": "failed",
                        "error": str(e)
                    }
                )

        # 检查是否所有帧都完成
        completed_count = loop.run_until_complete(
            RenderFrame.filter(task_id=task_id, status=FrameStatus.COMPLETED).count()
        )

        if completed_count == task.total_frames:
            task.status = TaskStatus.COMPLETED
        elif completed_count > 0:
            task.status = TaskStatus.COMPLETED  # 部分完成也算完成
        else:
            task.status = TaskStatus.FAILED
            task.error_message = "所有帧渲染失败"

        loop.run_until_complete(task.save())

        logger.info(f"任务 {task_id} 完成，工作空间保留在: {task.workspace_dir}")

    except Ignore:
        # 任务被取消
        task.status = TaskStatus.CANCELLED
        loop.run_until_complete(task.save())
        logger.info(f"任务 {task_id} 已取消，工作空间保留在: {task.workspace_dir}")
        raise

    except Exception as e:
        # 任务失败
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        loop.run_until_complete(task.save())
        logger.error(f"任务 {task_id} 失败，工作空间保留在: {task.workspace_dir}")

        # 重新抛出原始异常，让Celery记录错误
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.generate_thumbnail",
    max_retries=3,
    default_retry_delay=5  # 5秒后重试
)
def generate_thumbnail(self, frame_id: int, unionid: str = None, task_id: int = None):
    """
    生成缩略图任务

    Args:
        frame_id: 渲染帧ID
        unionid: 用户ID（用于目录隔离）
        task_id: 任务ID（用于目录隔离）
    """
    from app.models.frame import RenderFrame
    from app.services.thumbnail import ThumbnailService

    loop = asyncio.get_event_loop()

    try:
        # 获取帧信息
        frame = loop.run_until_complete(RenderFrame.get(id=frame_id))

        if not frame.output_path:
            logger.warning(f"帧 {frame_id} 没有输出路径，跳过缩略图生成")
            return

        output_path = Path(frame.output_path)

        # 检查文件是否存在（添加重试机制以处理文件系统延迟）
        if not output_path.exists():
            logger.warning(f"渲染文件暂不存在: {output_path}，尝试重试...")
            # 抛出异常触发自动重试
            raise FileNotFoundError(f"渲染结果文件不存在: {frame.output_path}")

        # 获取任务信息以获取缩略图目录
        from app.models.task import RenderTask
        task = loop.run_until_complete(RenderTask.get(id=frame.task_id))

        # 生成缩略图
        thumbnail_service = ThumbnailService()
        thumbnail_path = thumbnail_service.generate(
            image_path=output_path,
            output_dir=Path(task.thumbnails_dir),
            size=settings.thumbnail_size,
            frame_id=frame_id,
            unionid=unionid,
            task_id=task_id
        )

        # 更新帧信息
        frame.thumbnail_path = str(thumbnail_path)
        loop.run_until_complete(frame.save())

        logger.info(f"成功为帧 {frame_id} 生成缩略图: {thumbnail_path}")

    except FileNotFoundError as e:
        # 文件不存在，尝试重试
        logger.warning(f"缩略图生成失败（文件不存在），将在 5 秒后重试: {str(e)}")
        raise self.retry(exc=e, countdown=5)

    except Exception as e:
        # 其他错误，记录日志但不影响主任务
        logger.error(f"缩略图生成失败（帧 {frame_id}）: {str(e)}", exc_info=True)

        # 如果还有重试次数，尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"将重试缩略图生成（第 {self.request.retries + 1}/{self.max_retries} 次）")
            raise self.retry(exc=e, countdown=10)
        else:
            # 达到最大重试次数，记录但不抛出异常（避免影响主任务）
            logger.error(f"缩略图生成达到最大重试次数，放弃生成（帧 {frame_id}）")
            self.update_state(
                state="FAILURE",
                meta={"error": str(e), "frame_id": frame_id}
            )


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.retry_render_frame",
    max_retries=3,
    default_retry_delay=60
)
def retry_render_frame(self, task_id: int, frame_number: int):
    """
    重新渲染单个失败的帧

    Args:
        task_id: 任务ID
        frame_number: 帧号
    """
    from app.models.task import RenderTask, TaskStatus
    from app.models.frame import RenderFrame, FrameStatus
    from app.services.renderer import get_renderer

    loop = asyncio.get_event_loop()

    try:
        # 获取任务信息
        task = loop.run_until_complete(RenderTask.get(id=task_id))

        # 检查任务状态
        if task.status == TaskStatus.CANCELLED:
            logger.warning(f"任务 {task_id} 已取消，跳过帧 {frame_number} 的重试")
            return

        # 获取帧信息
        frame = loop.run_until_complete(
            RenderFrame.get(task_id=task_id, frame_number=frame_number)
        )

        # 更新帧状态为渲染中
        frame.status = FrameStatus.RENDERING
        frame.error_message = None
        loop.run_until_complete(frame.save())

        logger.info(f"开始重试渲染：任务 {task_id}，帧 {frame_number}")

        # 获取渲染引擎
        renderer = get_renderer(task.render_engine)

        # 执行渲染
        start_time = time.time()
        output_path, stdout, stderr = renderer.render_frame(
            project_file=task.project_file,
            frame_number=frame.frame_number,
            output_dir=Path(task.renders_dir),
            engine_conf=task.render_engine_conf
        )
        render_time = time.time() - start_time

        # 更新帧信息
        frame.status = FrameStatus.COMPLETED
        frame.output_path = str(output_path)
        frame.render_time = render_time
        frame.stdout = stdout
        frame.stderr = stderr
        loop.run_until_complete(frame.save())

        # 更新任务的已完成帧数
        task.completed_frames = loop.run_until_complete(
            RenderFrame.filter(task_id=task_id, status=FrameStatus.COMPLETED).count()
        )

        # 如果所有帧都完成了，更新任务状态
        if task.completed_frames == task.total_frames:
            task.status = TaskStatus.COMPLETED
        elif task.status == TaskStatus.FAILED:
            # 如果之前是失败状态，现在改为部分完成
            task.status = TaskStatus.COMPLETED

        loop.run_until_complete(task.save())

        # 异步生成缩略图
        generate_thumbnail.delay(frame.id, task.unionid, task.id)

        logger.info(f"成功重试渲染：任务 {task_id}，帧 {frame_number}")

    except Exception as e:
        # 渲染失败
        logger.error(f"重试渲染失败：任务 {task_id}，帧 {frame_number}，错误: {str(e)}")

        frame = loop.run_until_complete(
            RenderFrame.get(task_id=task_id, frame_number=frame_number)
        )
        frame.status = FrameStatus.FAILED
        frame.error_message = str(e)
        loop.run_until_complete(frame.save())

        # 如果还有重试次数，继续重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在60秒后重试（第 {self.request.retries + 1}/{self.max_retries} 次）")
            raise self.retry(exc=e, countdown=60)
        else:
            logger.error(f"达到最大重试次数，放弃渲染帧 {frame_number}")
            raise
