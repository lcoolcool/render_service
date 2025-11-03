"""渲染任务模型"""
from enum import Enum
from tortoise import fields
from tortoise.models import Model


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"  # 待处理
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class RenderEngine(str, Enum):
    """渲染引擎枚举"""
    MAYA = "maya"
    UE = "ue"


class RenderTask(Model):
    """渲染任务模型"""

    id = fields.IntField(pk=True)
    # 用户ID
    unionid = fields.CharField(max_length=255)
    # OSS文件路径（原始存储位置）
    oss_file_path = fields.CharField(max_length=500, null=True)
    # 本地文件路径（直接使用本地文件，无需从OSS下载）
    file_path = fields.CharField(max_length=500, null=True)
    # 是否为压缩文件
    is_compressed = fields.BooleanField(default=False)
    # 渲染引擎
    render_engine = fields.CharEnumField(RenderEngine, max_length=20)
    # 任务信息（包含执行任务所需的所有配置）
    task_info = fields.JSONField(default=dict)
    # 任务状态
    status = fields.CharEnumField(TaskStatus, max_length=20, default=TaskStatus.PENDING)
    # 总帧数
    total_frames = fields.IntField(default=0)
    # 已完成帧数
    completed_frames = fields.IntField(default=0)
    # Celery任务ID（用于取消任务）
    celery_task_id = fields.CharField(max_length=255, null=True)
    # 错误信息
    error_message = fields.TextField(null=True)
    # 是否已删除（软删除）
    is_deleted = fields.BooleanField(default=False)
    # 分区日期（用于数据分区管理，自动获取创建日期）
    p_date = fields.DateField(auto_now_add=True, index=True, null=True)
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关联的渲染帧
    frames: fields.ReverseRelation["RenderFrame"]

    class Meta:
        table = "render_tasks"
        ordering = ["-created_at"]  # 创建时间晚的在前

    def __str__(self):
        return f"RenderTask({self.id}, {self.render_engine}, {self.status})"

    @property
    def progress_percentage(self) -> float:
        """计算进度百分比"""
        if self.total_frames == 0:
            return 0.0
        return (self.completed_frames / self.total_frames) * 100
