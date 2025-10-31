"""阿里云OSS存储服务"""
import logging
from pathlib import Path
from typing import Optional
import oss2
from app.config import settings

logger = logging.getLogger(__name__)


class OSSStorageService:
    """OSS存储服务类"""

    def __init__(self):
        """初始化OSS客户端"""
        if not settings.oss_access_key_id or not settings.oss_access_key_secret:
            raise ValueError("OSS配置不完整，请检查 .env 文件中的 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET")

        # 创建认证对象
        self.auth = oss2.Auth(
            settings.oss_access_key_id,
            settings.oss_access_key_secret
        )

        # 创建Bucket对象
        self.bucket = oss2.Bucket(
            self.auth,
            settings.oss_endpoint,
            settings.oss_bucket_name
        )

    def download_file(
        self,
        oss_path: str,
        local_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Path:
        """
        从OSS下载文件到本地

        Args:
            oss_path: OSS上的文件路径（例如: "projects/user123/scene.ma.gz"）
            local_path: 本地保存路径
            progress_callback: 下载进度回调函数（可选）

        Returns:
            下载后的本地文件路径

        Raises:
            oss2.exceptions.NoSuchKey: 文件不存在
            oss2.exceptions.RequestError: 网络请求错误
        """
        try:
            # 确保本地目录存在
            local_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"开始从OSS下载文件: {oss_path} -> {local_path}")

            # 检查文件是否存在
            if not self.bucket.object_exists(oss_path):
                raise FileNotFoundError(f"OSS文件不存在: {oss_path}")

            # 获取文件大小
            file_size = self.bucket.head_object(oss_path).content_length
            logger.info(f"文件大小: {file_size / (1024**2):.2f} MB")

            # 下载文件（带进度条）
            if progress_callback:
                # 使用流式下载以支持进度回调
                result = self.bucket.get_object(oss_path)
                downloaded_size = 0
                chunk_size = 8192  # 8KB

                with open(local_path, 'wb') as f:
                    for chunk in result:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded_size, file_size)
            else:
                # 直接下载整个文件
                self.bucket.get_object_to_file(oss_path, str(local_path))

            logger.info(f"文件下载成功: {local_path}")
            return local_path

        except oss2.exceptions.NoSuchKey:
            logger.error(f"OSS文件不存在: {oss_path}")
            raise FileNotFoundError(f"OSS文件不存在: {oss_path}")

        except oss2.exceptions.RequestError as e:
            logger.error(f"OSS下载请求失败: {e}")
            raise

        except Exception as e:
            logger.error(f"下载文件时发生未知错误: {e}")
            # 清理可能部分下载的文件
            if local_path.exists():
                local_path.unlink()
            raise

    def upload_file(
        self,
        local_path: Path,
        oss_path: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        上传本地文件到OSS

        Args:
            local_path: 本地文件路径
            oss_path: OSS上的目标路径
            progress_callback: 上传进度回调函数（可选）

        Returns:
            OSS文件路径

        Raises:
            FileNotFoundError: 本地文件不存在
        """
        if not local_path.exists():
            raise FileNotFoundError(f"本地文件不存在: {local_path}")

        try:
            logger.info(f"开始上传文件到OSS: {local_path} -> {oss_path}")

            file_size = local_path.stat().st_size
            logger.info(f"文件大小: {file_size / (1024**2):.2f} MB")

            # 上传文件
            if progress_callback:
                # 使用分片上传以支持进度回调（大文件推荐）
                if file_size > 10 * 1024 * 1024:  # 大于10MB使用分片上传
                    oss2.resumable_upload(
                        self.bucket,
                        oss_path,
                        str(local_path),
                        progress_callback=progress_callback
                    )
                else:
                    with open(local_path, 'rb') as f:
                        self.bucket.put_object(oss_path, f, progress_callback=progress_callback)
            else:
                # 直接上传
                self.bucket.put_object_from_file(oss_path, str(local_path))

            logger.info(f"文件上传成功: {oss_path}")
            return oss_path

        except Exception as e:
            logger.error(f"上传文件时发生错误: {e}")
            raise

    def delete_file(self, oss_path: str) -> bool:
        """
        删除OSS上的文件

        Args:
            oss_path: OSS文件路径

        Returns:
            是否删除成功
        """
        try:
            logger.info(f"删除OSS文件: {oss_path}")
            self.bucket.delete_object(oss_path)
            logger.info(f"文件删除成功: {oss_path}")
            return True

        except Exception as e:
            logger.error(f"删除文件时发生错误: {e}")
            return False

    def file_exists(self, oss_path: str) -> bool:
        """
        检查OSS文件是否存在

        Args:
            oss_path: OSS文件路径

        Returns:
            文件是否存在
        """
        try:
            return self.bucket.object_exists(oss_path)
        except Exception as e:
            logger.error(f"检查文件存在性时发生错误: {e}")
            return False
