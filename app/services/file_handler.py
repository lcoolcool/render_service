"""文件处理服务（解压、清理等）"""
import gzip
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class FileHandlerService:
    """文件处理服务类"""

    @staticmethod
    def decompress_file(
        compressed_file: Path,
        output_dir: Path,
        delete_after: bool = False
    ) -> Path:
        """
        解压文件到指定目录

        支持的格式:
        - .gz (gzip)
        - .zip (zip)

        Args:
            compressed_file: 压缩文件路径
            output_dir: 解压目标目录
            delete_after: 解压后是否删除原压缩文件

        Returns:
            解压后的文件/目录路径

        Raises:
            ValueError: 不支持的压缩格式
            FileNotFoundError: 压缩文件不存在
        """
        if not compressed_file.exists():
            raise FileNotFoundError(f"压缩文件不存在: {compressed_file}")

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        suffix = compressed_file.suffix.lower()
        logger.info(f"开始解压文件: {compressed_file} -> {output_dir}")

        try:
            if suffix == '.gz':
                # 处理 .gz 文件
                return FileHandlerService._decompress_gzip(
                    compressed_file, output_dir, delete_after
                )
            elif suffix == '.zip':
                # 处理 .zip 文件
                return FileHandlerService._decompress_zip(
                    compressed_file, output_dir, delete_after
                )
            else:
                raise ValueError(f"不支持的压缩格式: {suffix}")

        except Exception as e:
            logger.error(f"解压文件时发生错误: {e}")
            raise

    @staticmethod
    def _decompress_gzip(
        gz_file: Path,
        output_dir: Path,
        delete_after: bool
    ) -> Path:
        """
        解压gzip文件

        Args:
            gz_file: .gz文件路径
            output_dir: 输出目录
            delete_after: 是否删除原文件

        Returns:
            解压后的文件路径
        """
        # 去除 .gz 后缀得到原文件名
        # 例如: scene.ma.gz -> scene.ma
        original_filename = gz_file.stem
        output_file = output_dir / original_filename

        logger.info(f"解压 gzip 文件: {gz_file.name} -> {output_file.name}")

        try:
            with gzip.open(gz_file, 'rb') as f_in:
                with open(output_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            logger.info(f"gzip 解压成功: {output_file}")

            # 删除原压缩文件
            if delete_after:
                gz_file.unlink()
                logger.info(f"已删除原压缩文件: {gz_file}")

            return output_file

        except Exception as e:
            logger.error(f"解压 gzip 文件失败: {e}")
            # 清理可能部分解压的文件
            if output_file.exists():
                output_file.unlink()
            raise

    @staticmethod
    def _decompress_zip(
        zip_file: Path,
        output_dir: Path,
        delete_after: bool
    ) -> Path:
        """
        解压zip文件

        Args:
            zip_file: .zip文件路径
            output_dir: 输出目录
            delete_after: 是否删除原文件

        Returns:
            解压后的目录路径
        """
        logger.info(f"解压 zip 文件: {zip_file.name} -> {output_dir}")

        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # 获取zip内的文件列表
                file_list = zip_ref.namelist()
                logger.info(f"zip 文件包含 {len(file_list)} 个文件")

                # 解压所有文件
                zip_ref.extractall(output_dir)

            logger.info(f"zip 解压成功: {output_dir}")

            # 删除原压缩文件
            if delete_after:
                zip_file.unlink()
                logger.info(f"已删除原压缩文件: {zip_file}")

            return output_dir

        except Exception as e:
            logger.error(f"解压 zip 文件失败: {e}")
            raise

    @staticmethod
    def find_project_file(
        directory: Path,
        extensions: List[str]
    ) -> Optional[Path]:
        """
        在目录中查找指定扩展名的工程文件

        Args:
            directory: 搜索目录
            extensions: 文件扩展名列表（例如: ['.ma', '.mb', '.uproject']）

        Returns:
            找到的第一个匹配文件路径，如果没找到返回None
        """
        logger.info(f"在目录中查找工程文件: {directory}, 扩展名: {extensions}")

        for ext in extensions:
            # 使用 glob 递归查找
            files = list(directory.rglob(f"*{ext}"))
            if files:
                logger.info(f"找到工程文件: {files[0]}")
                return files[0]

        logger.warning(f"未找到工程文件，扩展名: {extensions}")
        return None

    @staticmethod
    def cleanup_directory(directory: Path) -> bool:
        """
        清理（删除）整个目录及其内容

        Args:
            directory: 要删除的目录路径

        Returns:
            是否清理成功
        """
        if not directory.exists():
            logger.warning(f"目录不存在，跳过清理: {directory}")
            return True

        try:
            logger.info(f"开始清理目录: {directory}")
            shutil.rmtree(directory)
            logger.info(f"目录清理成功: {directory}")
            return True

        except Exception as e:
            logger.error(f"清理目录时发生错误: {e}")
            return False

    @staticmethod
    def get_directory_size(directory: Path) -> int:
        """
        计算目录的总大小（字节）

        Args:
            directory: 目录路径

        Returns:
            目录总大小（字节）
        """
        total_size = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
            return total_size
        except Exception as e:
            logger.error(f"计算目录大小时发生错误: {e}")
            return 0
