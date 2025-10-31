"""Celery异步任务定义"""
import asyncio
import time
import threading
from pathlib import Path
from celery import Task
from celery.exceptions import Ignore
from app.celery_app.celery import celery_app
from app.config import settings


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
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},  # 60秒后重试
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
    from app.services.thumbnail import generate_thumbnail

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
            project_file, workspace_dir = file_prep_service.prepare_project_files(
                unionid=task.unionid,
                task_id=task.id,
                oss_file_path=task.oss_file_path,
                is_compressed=task.is_compressed,
                render_engine=task.render_engine
            )

            # 更新任务的本地文件路径和工作空间
            task.project_file = str(project_file)
            task.workspace_dir = str(workspace_dir)
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
                    output_dir=settings.render_output_dir,
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

                # 异步生成缩略图
                generate_thumbnail.delay(frame.id)

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

        # 清理工作空间
        if task.workspace_dir:
            from pathlib import Path
            file_prep_service.cleanup_workspace(Path(task.workspace_dir))

    except Ignore:
        # 任务被取消，清理工作空间
        task.status = TaskStatus.CANCELLED
        loop.run_until_complete(task.save())

        if task.workspace_dir:
            from pathlib import Path
            try:
                file_prep_service.cleanup_workspace(Path(task.workspace_dir))
            except:
                pass  # 清理失败不影响任务取消
        raise

    except Exception as e:
        # 任务失败
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.retry_count += 1
        loop.run_until_complete(task.save())

        # 如果没有重试次数了，清理工作空间
        if task.retry_count >= task.max_retries:
            if task.workspace_dir:
                from pathlib import Path
                try:
                    file_prep_service.cleanup_workspace(Path(task.workspace_dir))
                except:
                    pass  # 清理失败不影响任务

        # 如果还有重试次数，抛出异常触发重试
        if task.retry_count < task.max_retries:
            raise
        else:
            raise Ignore()


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.generate_thumbnail",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30}
)
def generate_thumbnail(self, frame_id: int):
    """
    生成缩略图任务

    Args:
        frame_id: 渲染帧ID
    """
    from app.models.frame import RenderFrame
    from app.services.thumbnail import ThumbnailService

    loop = asyncio.get_event_loop()

    # 获取帧信息
    frame = loop.run_until_complete(RenderFrame.get(id=frame_id))

    if not frame.output_path or not Path(frame.output_path).exists():
        raise ValueError(f"渲染结果文件不存在: {frame.output_path}")

    try:
        # 生成缩略图
        thumbnail_service = ThumbnailService()
        thumbnail_path = thumbnail_service.generate(
            image_path=Path(frame.output_path),
            output_dir=settings.thumbnail_dir,
            size=settings.thumbnail_size
        )

        # 更新帧信息
        frame.thumbnail_path = str(thumbnail_path)
        loop.run_until_complete(frame.save())

    except Exception as e:
        # 缩略图生成失败不影响主任务
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise
