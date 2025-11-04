"""渲染帧相关的Pydantic schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FrameResponse(BaseModel):
    """渲染帧响应模型"""
    id: int
    task_id: int
    frame_number: int
    status: str
    output_path: Optional[str]
    oss_output_path: Optional[str]
    render_time: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FrameListResponse(BaseModel):
    """渲染帧列表响应模型"""
    total: int
    frames: list[FrameResponse]
