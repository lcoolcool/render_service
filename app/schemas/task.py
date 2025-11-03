"""任务相关的Pydantic schemas"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field
from app.models.task import TaskStatus, RenderEngine


class TaskCreate(BaseModel):
    """创建任务的请求模型"""
    unionid: str = Field(..., description="用户ID")
    oss_file_path: Optional[str] = Field(default=None, description="OSS上的工程文件路径")
    file_path: Optional[str] = Field(default=None, description="本地工程文件路径")
    is_compressed: bool = Field(default=False, description="文件是否为压缩格式 (支持.gz, .zip)")
    render_engine: RenderEngine = Field(..., description="渲染引擎类型 (maya/ue)")
    render_engine_conf: dict = Field(default_factory=dict, description="渲染引擎配置 (例如: Maya的renderer类型、UE的分辨率等)")
    total_frames: int = Field(..., gt=0, description="总帧数")

    def model_post_init(self, __context):
        """验证必须提供 oss_file_path 或 file_path 其中之一"""
        if not self.oss_file_path and not self.file_path:
            raise ValueError("必须提供 oss_file_path 或 file_path 其中之一")
        if self.oss_file_path and self.file_path:
            raise ValueError("只能提供 oss_file_path 或 file_path 其中之一，不能同时提供")

    class Config:
        json_schema_extra = {
            "example": {
                "unionid": "user123",
                "oss_file_path": "projects/user123/my_project.ma.gz",
                "is_compressed": True,
                "render_engine": "maya",
                "render_engine_conf": {
                    "renderer": "arnold",
                    "quality": "high"
                },
                "total_frames": 100
            }
        }


class TaskResponse(BaseModel):
    """任务响应模型"""
    id: int
    unionid: str
    oss_file_path: Optional[str]  # OSS文件路径
    file_path: Optional[str]  # 本地文件路径
    is_compressed: bool
    project_file: Optional[str]  # 本地工程文件路径（下载解压后）
    workspace_dir: Optional[str]  # 任务工作空间目录
    render_engine: str
    render_engine_conf: dict
    status: str
    total_frames: int
    completed_frames: int
    progress_percentage: float
    is_deleted: bool
    p_date: Optional[date]
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
