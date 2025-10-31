"""缩略图生成服务"""
from pathlib import Path
from PIL import Image


class ThumbnailService:
    """缩略图生成服务"""

    def generate(
        self,
        image_path: Path,
        output_dir: Path,
        size: int = 200
    ) -> Path:
        """
        生成缩略图

        Args:
            image_path: 原始图像路径
            output_dir: 输出目录
            size: 缩略图最大尺寸（宽高中较大者）

        Returns:
            缩略图文件路径
        """
        if not image_path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成缩略图文件名
        thumbnail_name = f"thumb_{image_path.stem}.jpg"
        thumbnail_path = output_dir / thumbnail_name

        try:
            # 打开图像
            with Image.open(image_path) as img:
                # 转换为RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    # 创建白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # 生成缩略图（保持宽高比）
                img.thumbnail((size, size), Image.Resampling.LANCZOS)

                # 保存缩略图
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)

            return thumbnail_path

        except Exception as e:
            raise RuntimeError(f"生成缩略图失败: {str(e)}")

    def batch_generate(
        self,
        image_paths: list[Path],
        output_dir: Path,
        size: int = 200
    ) -> list[Path]:
        """
        批量生成缩略图

        Args:
            image_paths: 原始图像路径列表
            output_dir: 输出目录
            size: 缩略图最大尺寸

        Returns:
            缩略图文件路径列表
        """
        thumbnail_paths = []

        for image_path in image_paths:
            try:
                thumbnail_path = self.generate(image_path, output_dir, size)
                thumbnail_paths.append(thumbnail_path)
            except Exception as e:
                # 记录错误但继续处理其他图像
                print(f"生成缩略图失败 {image_path}: {e}")
                thumbnail_paths.append(None)

        return thumbnail_paths
