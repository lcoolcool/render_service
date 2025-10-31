"""缩略图生成服务"""
import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)


class ThumbnailService:
    """缩略图生成服务"""

    def generate(
        self,
        image_path: Path,
        output_dir: Path,
        size: int = 200,
        frame_id: int = None,
        unionid: str = None,
        task_id: int = None
    ) -> Path:
        """
        生成缩略图

        Args:
            image_path: 原始图像路径
            output_dir: 输出目录
            size: 缩略图最大尺寸（宽高中较大者）
            frame_id: 帧ID（用于生成唯一文件名）
            unionid: 用户ID（用于目录隔离）
            task_id: 任务ID（用于目录隔离）

        Returns:
            缩略图文件路径
        """
        if not image_path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")

        # 如果提供了用户和任务信息，使用隔离的目录结构
        if unionid and task_id:
            output_dir = output_dir / unionid / str(task_id)

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一的缩略图文件名（使用 frame_id 避免冲突）
        if frame_id:
            thumbnail_name = f"thumb_frame_{frame_id}.jpg"
        else:
            thumbnail_name = f"thumb_{image_path.stem}.jpg"
        thumbnail_path = output_dir / thumbnail_name

        try:
            # 尝试加载图像（支持多种格式）
            img = self._load_image(image_path)

            # 转换为RGB模式（如果需要）
            img = self._convert_to_rgb(img)

            # 生成缩略图（保持宽高比）
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            # 保存缩略图
            img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)

            logger.info(f"成功生成缩略图: {thumbnail_path}")
            return thumbnail_path

        except Exception as e:
            logger.error(f"生成缩略图失败 {image_path}: {str(e)}")
            raise RuntimeError(f"生成缩略图失败: {str(e)}")

    def _load_image(self, image_path: Path) -> Image.Image:
        """
        加载图像，支持多种格式（包括EXR）

        Args:
            image_path: 图像文件路径

        Returns:
            PIL Image 对象
        """
        # 先尝试使用 Pillow 直接打开（支持常见格式）
        try:
            return Image.open(image_path)
        except Exception as pil_error:
            # 如果是 EXR 格式，尝试使用专门的库
            if image_path.suffix.lower() in ['.exr', '.hdr']:
                try:
                    # 优先尝试使用 imageio（更容易安装）
                    return self._load_exr_with_imageio(image_path)
                except ImportError:
                    try:
                        # 降级到 OpenImageIO
                        return self._load_exr_with_oiio(image_path)
                    except ImportError:
                        logger.warning(
                            f"无法加载EXR格式文件，请安装 imageio 库。"
                            f"运行: pip install imageio"
                        )
                        raise RuntimeError(
                            f"不支持 EXR 格式，请安装 imageio: pip install imageio"
                        ) from pil_error
            # 其他格式的错误直接抛出
            raise

    def _load_exr_with_oiio(self, image_path: Path) -> Image.Image:
        """使用 OpenImageIO 加载 EXR 文件"""
        import OpenImageIO as oiio
        import numpy as np

        img_input = oiio.ImageInput.open(str(image_path))
        if not img_input:
            raise RuntimeError(f"无法打开EXR文件: {image_path}")

        spec = img_input.spec()
        pixels = img_input.read_image(0, 0, 0, -1, "float")
        img_input.close()

        # 转换为8位RGB
        pixels = np.clip(pixels * 255, 0, 255).astype(np.uint8)

        # 如果是RGBA，只取RGB通道
        if pixels.shape[2] == 4:
            pixels = pixels[:, :, :3]

        return Image.fromarray(pixels, 'RGB')

    def _load_exr_with_imageio(self, image_path: Path) -> Image.Image:
        """使用 imageio 加载 EXR 文件"""
        import imageio.v3 as iio
        import numpy as np

        # 读取EXR文件
        pixels = iio.imread(image_path)

        # 转换为8位RGB
        pixels = np.clip(pixels * 255, 0, 255).astype(np.uint8)

        # 如果是RGBA，只取RGB通道
        if len(pixels.shape) == 3 and pixels.shape[2] == 4:
            pixels = pixels[:, :, :3]

        return Image.fromarray(pixels, 'RGB')

    def _convert_to_rgb(self, img: Image.Image) -> Image.Image:
        """
        将图像转换为RGB模式

        Args:
            img: PIL Image 对象

        Returns:
            RGB 模式的 PIL Image 对象
        """
        if img.mode in ('RGBA', 'LA', 'P'):
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            return background
        elif img.mode != 'RGB':
            return img.convert('RGB')
        return img

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
                logger.error(f"生成缩略图失败 {image_path}: {e}")
                thumbnail_paths.append(None)

        return thumbnail_paths
