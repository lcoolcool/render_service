"""任务管理API路由"""
from fastapi import APIRouter, HTTPException, Query
from celery.result import AsyncResult
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusResponse, TaskListResponse
from app.schemas.frame import FrameResponse, FrameListResponse
from app.models.task import RenderTask, TaskStatus
from app.models.frame import RenderFrame, FrameStatus
from app.celery_app.celery import celery_app
from app.celery_app.tasks import render_task

router = APIRouter(prefix="/api/tasks", tags=["任务管理"])


@router.post("/", response_model=TaskResponse, summary="创建渲染任务")
async def create_task(task_data: TaskCreate):
    """
    创建新的渲染任务

    - **unionid**: 用户ID
    - **oss_file_path**: OSS上的工程文件路径
    - **is_compressed**: 文件是否为压缩格式
    - **render_engine**: 渲染引擎（maya/ue）
    - **render_engine_conf**: 渲染引擎配置
    - **priority**: 任务优先级（0-10）
    - **total_frames**: 总帧数
    - **max_retries**: 最大重试次数
    """
    try:
        # 创建任务记录
        task = await RenderTask.create(
            unionid=task_data.unionid,
            oss_file_path=task_data.oss_file_path,
            is_compressed=task_data.is_compressed,
            render_engine=task_data.render_engine,
            render_engine_conf=task_data.render_engine_conf,
            priority=task_data.priority,
            total_frames=task_data.total_frames,
            max_retries=task_data.max_retries,
            status=TaskStatus.PENDING
        )

        # 创建帧记录
        frames_data = [
            {
                "task_id": task.id,
                "frame_number": i,
                "status": FrameStatus.PENDING
            }
            for i in range(1, task_data.total_frames + 1)
        ]
        await RenderFrame.bulk_create([RenderFrame(**data) for data in frames_data])

        # 根据优先级选择队列
        if task_data.priority >= 8:
            queue_name = "high_priority"
        elif task_data.priority <= 3:
            queue_name = "low_priority"
        else:
            queue_name = "default"

        # 提交异步任务
        celery_task = render_task.apply_async(
            args=[task.id],
            queue=queue_name,
            priority=task_data.priority
        )

        # 更新celery_task_id
        task.celery_task_id = celery_task.id
        await task.save()

        # 返回任务信息
        return TaskResponse(
            id=task.id,
            unionid=task.unionid,
            oss_file_path=task.oss_file_path,
            is_compressed=task.is_compressed,
            project_file=task.project_file,
            workspace_dir=task.workspace_dir,
            render_engine=task.render_engine.value,
            render_engine_conf=task.render_engine_conf,
            status=task.status.value,
            priority=task.priority,
            total_frames=task.total_frames,
            completed_frames=task.completed_frames,
            progress_percentage=task.progress_percentage,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            celery_task_id=task.celery_task_id,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
async def get_task(task_id: int):
    """获取指定任务的详细信息"""
    task = await RenderTask.get_or_none(id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return TaskResponse(
        id=task.id,
        unionid=task.unionid,
        oss_file_path=task.oss_file_path,
        is_compressed=task.is_compressed,
        project_file=task.project_file,
        workspace_dir=task.workspace_dir,
        render_engine=task.render_engine.value,
        render_engine_conf=task.render_engine_conf,
        status=task.status.value,
        priority=task.priority,
        total_frames=task.total_frames,
        completed_frames=task.completed_frames,
        progress_percentage=task.progress_percentage,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        celery_task_id=task.celery_task_id,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.get("/{task_id}/status", response_model=TaskStatusResponse, summary="获取任务状态")
async def get_task_status(task_id: int):
    """获取任务状态（轻量级接口，用于轮询）"""
    task = await RenderTask.get_or_none(id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return TaskStatusResponse(
        id=task.id,
        status=task.status.value,
        progress_percentage=task.progress_percentage,
        completed_frames=task.completed_frames,
        total_frames=task.total_frames,
        error_message=task.error_message
    )


@router.get("/", response_model=TaskListResponse, summary="获取任务列表")
async def list_tasks(
    status: str = Query(None, description="按状态过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取任务列表，支持分页和过滤"""
    query = RenderTask.all()

    # 状态过滤
    if status:
        try:
            task_status = TaskStatus(status)
            query = query.filter(status=task_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的任务状态: {status}")

    # 获取总数
    total = await query.count()

    # 分页查询
    tasks = await query.offset(offset).limit(limit).order_by("-created_at")

    # 转换为响应模型
    task_responses = [
        TaskResponse(
            id=task.id,
            unionid=task.unionid,
            oss_file_path=task.oss_file_path,
            is_compressed=task.is_compressed,
            project_file=task.project_file,
            workspace_dir=task.workspace_dir,
            render_engine=task.render_engine.value,
            render_engine_conf=task.render_engine_conf,
            status=task.status.value,
            priority=task.priority,
            total_frames=task.total_frames,
            completed_frames=task.completed_frames,
            progress_percentage=task.progress_percentage,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            celery_task_id=task.celery_task_id,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        for task in tasks
    ]

    return TaskListResponse(total=total, tasks=task_responses)


@router.get("/{task_id}/frames", response_model=FrameListResponse, summary="获取任务的所有帧")
async def get_task_frames(
    task_id: int,
    status: str = Query(None, description="按状态过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取任务的所有渲染帧信息"""
    # 检查任务是否存在
    task = await RenderTask.get_or_none(id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 查询帧
    query = RenderFrame.filter(task_id=task_id)

    # 状态过滤
    if status:
        try:
            frame_status = FrameStatus(status)
            query = query.filter(status=frame_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的帧状态: {status}")

    # 获取总数
    total = await query.count()

    # 分页查询
    frames = await query.offset(offset).limit(limit).order_by("frame_number")

    # 转换为响应模型
    frame_responses = [
        FrameResponse(
            id=frame.id,
            task_id=frame.task_id,
            frame_number=frame.frame_number,
            status=frame.status.value,
            output_path=frame.output_path,
            thumbnail_path=frame.thumbnail_path,
            render_time=frame.render_time,
            error_message=frame.error_message,
            created_at=frame.created_at,
            updated_at=frame.updated_at
        )
        for frame in frames
    ]

    return FrameListResponse(total=total, frames=frame_responses)


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(task_id: int):
    """取消正在运行或待处理的任务"""
    task = await RenderTask.get_or_none(id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 只能取消待处理或运行中的任务
    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail=f"无法取消状态为 {task.status.value} 的任务"
        )

    # 取消Celery任务
    if task.celery_task_id:
        celery_app.control.revoke(task.celery_task_id, terminate=True, signal='SIGTERM')

    # 更新任务状态
    task.status = TaskStatus.CANCELLED
    await task.save()

    # 更新未完成帧的状态
    await RenderFrame.filter(
        task_id=task_id,
        status__in=[FrameStatus.PENDING, FrameStatus.RENDERING]
    ).update(status=FrameStatus.FAILED, error_message="任务已取消")

    return {"message": "任务已取消", "task_id": task_id}


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(task_id: int):
    """删除任务及其所有相关数据"""
    task = await RenderTask.get_or_none(id=task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 如果任务正在运行，先取消
    if task.status == TaskStatus.RUNNING and task.celery_task_id:
        celery_app.control.revoke(task.celery_task_id, terminate=True, signal='SIGTERM')

    # 删除任务（会级联删除关联的帧记录）
    await task.delete()

    return {"message": "任务已删除", "task_id": task_id}
