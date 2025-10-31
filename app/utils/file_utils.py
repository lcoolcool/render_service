"""文件处理工具函数"""
from pathlib import Path
from typing import Optional


def ensure_dir_exists(directory: Path) -> Path:
    """
    确保目录存在，如果不存在则创建

    Args:
        directory: 目录路径

    Returns:
        目录路径
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_file_size_mb(file_path: Path) -> float:
    """
    获取文件大小（MB）

    Args:
        file_path: 文件路径

    Returns:
        文件大小（MB）
    """
    if not file_path.exists():
        return 0.0

    size_bytes = file_path.stat().st_size
    return size_bytes / (1024 * 1024)


def get_safe_filename(filename: str) -> str:
    """
    获取安全的文件名（移除非法字符）

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    import re
    # 移除Windows文件名非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    safe_name = re.sub(illegal_chars, '_', filename)
    return safe_name


def is_image_file(file_path: Path) -> bool:
    """
    判断是否为图像文件

    Args:
        file_path: 文件路径

    Returns:
        是否为图像文件
    """
    image_extensions = {'.png', '.jpg', '.jpeg', '.exr', '.tif', '.tiff', '.bmp', '.gif'}
    return file_path.suffix.lower() in image_extensions


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的文件大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_frame_filename(
    project_name: str,
    frame_number: int,
    extension: str = ".png",
    padding: int = 4
) -> str:
    """
    生成渲染帧文件名

    Args:
        project_name: 项目名称
        frame_number: 帧序号
        extension: 文件扩展名
        padding: 帧号补齐位数

    Returns:
        文件名
    """
    safe_name = get_safe_filename(project_name)
    frame_str = str(frame_number).zfill(padding)
    return f"{safe_name}_{frame_str}{extension}"
