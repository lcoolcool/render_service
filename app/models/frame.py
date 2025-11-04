"""渲染帧模型"""
from enum import Enum
from tortoise import fields
from tortoise.models import Model


class FrameStatus(str, Enum):
    """帧状态枚举"""
    PENDING = "pending"  # 待渲染
    RENDERING = "rendering"  # 渲染中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class RenderFrame(Model):
    """渲染帧模型"""

    id = fields.IntField(pk=True)
    # 关联的任务
    task = fields.ForeignKeyField("models.RenderTask", related_name="frames", on_delete=fields.CASCADE)
    # 帧序号
    frame_number = fields.IntField()
    # 帧状态
    status = fields.CharEnumField(FrameStatus, max_length=20, default=FrameStatus.PENDING)
    # 渲染结果文件路径（本地）
    output_path = fields.CharField(max_length=500, null=True)
    # 渲染结果文件路径（OSS）
    oss_output_path = fields.CharField(max_length=500, null=True)
    # 渲染耗时（秒）
    render_time = fields.FloatField(null=True)
    # 错误信息
    error_message = fields.TextField(null=True)
    # 渲染日志
    stdout = fields.TextField(null=True)
    stderr = fields.TextField(null=True)
    # 是否已删除（软删除）
    is_deleted = fields.BooleanField(default=False)
    # 分区日期（用于数据分区管理，自动获取创建日期）
    p_date = fields.DateField(auto_now_add=True, index=True)
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "render_frames"
        ordering = ["frame_number"]  # 按帧序号排序
        unique_together = (("task", "frame_number"),)  # 同一任务的帧序号唯一

    def __str__(self):
        return f"RenderFrame({self.id}, task={self.task_id}, frame={self.frame_number}, {self.status})"
