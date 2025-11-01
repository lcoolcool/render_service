"""应用配置管理"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    # 数据库配置
    database_url: str = "sqlite://db.sqlite3"

    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Celery配置
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # 文件存储配置
    upload_dir: Path = Path("C:/uploads")
    workspace_root_dir: Path = Path("C:/workspace")  # 任务工作空间根目录（包含所有任务的source、project、renders、thumbnails）

    # 阿里云OSS配置
    oss_endpoint: str = "oss-cn-hangzhou.aliyuncs.com"  # OSS访问域名
    oss_access_key_id: str = "your_access_key_id"  # AccessKey ID
    oss_access_key_secret: str = "your_access_key_secret"  # AccessKey Secret
    oss_bucket_name: str = "your_bucket_name"  # Bucket名称

    # 渲染引擎配置
    maya_executable: Path = Path("C:/Program Files/Autodesk/Maya2022/bin/Render.exe")
    ue_executable: Path = Path("C:/Program Files/Epic Games/UE_5.3/Engine/Binaries/Win64/UnrealEditor-Cmd.exe")

    # 任务配置
    max_retries: int = 3
    default_priority: int = 5
    thumbnail_size: int = 200

    # API配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保必要的目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_root_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
