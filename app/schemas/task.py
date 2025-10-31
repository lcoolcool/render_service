"""任务相关的Pydantic schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.task import TaskStatus, RenderEngine


class TaskCreate(BaseModel):
    """创建任务的请求模型"""
    project_file: str = Field(..., description="工程文件路径")
    render_engine: RenderEngine = Field(..., description="渲染引擎类型 (maya/ue)")
    priority: int = Field(default=5, ge=0, le=10, description="任务优先级 (0-10)")
    total_frames: int = Field(..., gt=0, description="总帧数")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")

    class Config:
        json_schema_extra = {
            "example": {
                "project_file": "C:/uploads/my_project.ma",
                "render_engine": "maya",
                "priority": 7,
                "total_frames": 100,
                "max_retries": 3
            }
        }


class TaskResponse(BaseModel):
    """任务响应模型"""
    id: int
    project_file: str
    render_engine: str
    status: str
    priority: int
    total_frames: int
    completed_frames: int
    progress_percentage: float
    retry_count: int
    max_retries: int
    celery_task_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    """任务状态响应模型（简化版）"""
    id: int
    status: str
    progress_percentage: float
    completed_frames: int
    total_frames: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    total: int
    tasks: list[TaskResponse]
