"""渲染引擎适配器"""
import re
import subprocess
import logging

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.config import settings
from app.models.task import RenderEngine

logger = logging.getLogger(__name__)


class BaseRenderer(ABC):
    """渲染器基类"""

    def __init__(self, executable: Path):
        self.executable = executable
        if not executable.exists():
            raise FileNotFoundError(f"渲染引擎可执行文件不存在: {executable}")

    @abstractmethod
    def render_frame(
        self,
        project_file: str,
        frame_number: int,
        output_dir: Path,
        engine_conf: Optional[dict] = None
    ) -> tuple[Path, str, str]:
        """
        渲染单帧

        Args:
            project_file: 工程文件路径
            frame_number: 帧序号
            output_dir: 输出目录
            engine_conf: 引擎配置字典

        Returns:
            (渲染结果文件路径, stdout日志, stderr日志)
        """
        pass

    def _run_command(self, command: list[str], timeout: Optional[int] = None) -> tuple[str, str]:
        """
        执行命令并捕获输出

        Args:
            command: 命令列表
            timeout: 超时时间（秒）

        Returns:
            (stdout, stderr)
        """
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            stdout, stderr = process.communicate(timeout=timeout)

            if process.returncode != 0:
                raise RuntimeError(f"渲染命令执行失败: {stderr}")

            return stdout, stderr

        except subprocess.TimeoutExpired:
            process.kill()
            raise RuntimeError(f"渲染超时（{timeout}秒）")
        except Exception as e:
            raise RuntimeError(f"执行渲染命令时出错: {str(e)}")


class MayaRenderer(BaseRenderer):
    """Maya渲染器"""

    def render_frame(
        self,
        project_file: str,
        frame_number: int,
        output_dir: Path,
        engine_conf: Optional[dict] = None
    ) -> tuple[Path, str, str]:
        """使用Maya批处理模式渲染单帧"""

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 从配置中获取渲染器类型，默认使用Arnold
        if engine_conf is None:
            engine_conf = {}
        renderer = engine_conf.get("renderer", "arnold")

        # 构建Maya渲染命令
        # "C:\SoftWare\Maya\maya2025\Maya 2025.3.1\Maya2025\bin\Render.exe" -r arnold -rd C:\Project\WJMRender\Render -s 1 -e 24 -b 1 "C:\Project\WJMRender\MayaProject\scenes\Qiu_Test_v001.ma"
        # mayabatch -file <project.ma> -render <renderer> -s <start> -e <end> -rd <output_dir>
        command = [
            str(self.executable),
            "-r", renderer,  # 从配置中获取渲染器类型
            "-rd", str(output_dir),  # 输出目录
            "-s", str(frame_number),  # 起始帧
            "-e", str(frame_number),  # 结束帧
            "-b", "1",  # 帧步长
            project_file,
        ]

        # 执行渲染
        stdout, stderr = self._run_command(command, timeout=3600)  # 1小时超时

        # 解析输出，查找生成的文件
        output_file = self._find_output_file(output_dir, frame_number, stdout, project_file)


        if not output_file or not output_file.exists():
            raise RuntimeError(f"未找到渲染输出文件，帧号: {frame_number}")

        return output_file, stdout, stderr

    def _find_output_file(self, output_dir: Path, frame_number: int, stdout: str, project_file: str) -> Optional[Path]:
        """
        从Maya输出中查找渲染结果文件

        查找策略（按优先级）：
        1. 从stdout日志解析文件路径（最可靠）
        2. 在多个可能的目录中查找匹配帧号的图片文件：
           - 指定的output_dir（通过-rd参数传递）
           - 工程文件所在目录及其常见子目录（处理相对路径情况）
        """

        # 策略1: 从stdout解析文件路径
        # Maya常见输出格式：
        # - "Rendering: C:/path/to/image.0001.exr"
        # - "Result: /path/to/scene.exr.0001"
        # - "Writing file: scene_0001.png"
        output_file = self._parse_output_from_stdout(stdout)
        if output_file and output_file.exists():
            logger.info(f"从stdout解析到输出文件: {output_file}")
            return output_file
        logger.info("未从stdout解析到输出文件，尝试从任务目录中查找匹配的文件")

        # 策略2: 在多个可能的目录中查找匹配的文件
        # 获取所有可能的输出目录（包括处理用户设置的相对路径）
        possible_dirs = self._get_possible_output_directories(output_dir, project_file)

        for search_dir in possible_dirs:
            if not search_dir.exists():
                continue

            output_file = self._search_output_in_directory(search_dir, frame_number)
            if output_file:
                logger.info(f"在目录 {search_dir} 中找到输出文件: {output_file}")
                return output_file

        logger.warning(f"在所有可能的目录中都未找到帧 {frame_number} 的输出文件")
        return None

    def _get_possible_output_directories(self, output_dir: Path, project_file: str) -> list[Path]:
        """
        获取所有可能的输出目录列表（处理用户在工程文件中设置相对路径的情况）

        Args:
            output_dir: 我们通过-rd参数指定的输出目录
            project_file: Maya工程文件路径

        Returns:
            按优先级排序的可能输出目录列表
        """
        possible_dirs = []

        # 优先级1: 指定的输出目录
        possible_dirs.append(output_dir)

        return possible_dirs

    def _parse_output_from_stdout(self, stdout: str) -> Optional[Path]:
        """
        从Maya的stdout日志中解析输出文件路径

        支持的Maya输出格式：
        - Maya 2025 Arnold: | [driver_exr] writing file `path.exr'
        - 旧版本: Rendering: path.exr
        - 其他: Writing file: path.png
        """

        # 匹配常见的输出模式，按优先级排序（支持多种图片格式）
        patterns = [
            # Maya 2025 Arnold格式: | [driver_exr] writing file `path.exr'
            # 匹配反引号包围的路径，反引号后可能是单引号或反引号
            r'writing\s+file\s+[`\']([^`\'\n\r]+\.(?:exr|png|jpg|jpeg|tif|tiff|tga|bmp|iff))',

            # 通用格式: Writing file: path
            r'(?:Rendering|Result|Writing\s+file):\s*([^\n\r]+\.(?:exr|png|jpg|jpeg|tif|tiff|tga|bmp|iff))',

            # 简化格式: Writing path
            r'Writing\s+([^\n\r]+\.(?:exr|png|jpg|jpeg|tif|tiff|tga|bmp|iff))',

            # 完成格式: File written: path
            r'File\s+written:\s*([^\n\r]+\.(?:exr|png|jpg|jpeg|tif|tiff|tga|bmp|iff))',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, stdout, re.IGNORECASE)
            if matches:
                # 返回最后一个匹配（通常是最终的输出文件）
                file_path_str = matches[-1].strip()
                # 清理可能的引号、反引号和空白字符
                file_path_str = file_path_str.strip('"\'`')
                logger.debug(f"从stdout解析到文件路径: {file_path_str} (使用模式: {pattern})")
                return Path(file_path_str)

        logger.debug("未能从stdout解析出文件路径")
        return None

    def _search_output_in_directory(self, output_dir: Path, frame_number: int) -> Optional[Path]:
        """
        在输出目录中查找渲染文件（假设输出目录中只有一个渲染文件）
        """

        supported_exts = ('.exr', '.png', '.deepexr', '.jpeg', '.tif', '.maya')

        # 遍历输出目录，找到第一个支持格式的图片文件
        for file_path in output_dir.iterdir():
            if not file_path.is_file():
                continue

            file_name_lower = file_path.name.lower()

            # 检查是否为支持的图片格式
            if any(file_name_lower.endswith(ext) for ext in supported_exts):
                logger.info(f"找到渲染输出文件: {file_path.name}")
                return file_path

        logger.warning(f"在目录 {output_dir} 中未找到支持格式的渲染文件")
        return None


class UERenderer(BaseRenderer):
    """Unreal Engine渲染器"""

    def render_frame(
        self,
        project_file: str,
        frame_number: int,
        output_dir: Path,
        engine_conf: Optional[dict] = None
    ) -> tuple[Path, str, str]:
        """使用UE命令行模式渲染单帧"""

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 从配置中获取参数（可选）
        if engine_conf is None:
            engine_conf = {}
        res_x = engine_conf.get("resolution_x", 1920)
        res_y = engine_conf.get("resolution_y", 1080)
        quality = engine_conf.get("quality", 100)

        # 构建UE渲染命令
        # UnrealEditor-Cmd.exe <project.uproject> -game -MovieSceneCaptureType=... -Frame=<frame>
        output_file = output_dir / f"frame_{frame_number:04d}.png"

        command = [
            str(self.executable),
            project_file,
            "-game",
            "-NOTEXTURESTREAMING",
            "-MovieSceneCaptureType=/Script/MovieSceneCapture.AutomatedLevelSequenceCapture",
            f"-LevelSequence=/Game/Sequences/MasterSequence",  # 需要根据实际项目调整
            f"-MovieFrameStart={frame_number}",
            f"-MovieFrameEnd={frame_number}",
            f"-MovieFolder={output_dir}",
            "-MovieFormat=PNG",
            f"-MovieQuality={quality}",
            f"-ResX={res_x}",
            f"-ResY={res_y}",
            "-ForceRes",
            "-Windowed",
            "-NoLoadingScreen",
            "-NoSplash",
            "-Unattended",
            "-NullRHI",  # 使用空渲染，在某些情况下更稳定
        ]

        # 执行渲染
        stdout, stderr = self._run_command(command, timeout=3600)

        # 查找输出文件
        output_file = self._find_output_file(output_dir, frame_number)

        if not output_file or not output_file.exists():
            raise RuntimeError(f"未找到UE渲染输出文件，帧号: {frame_number}")

        return output_file, stdout, stderr

    def _find_output_file(self, output_dir: Path, frame_number: int) -> Optional[Path]:
        """查找UE渲染输出文件"""

        frame_str = f"{frame_number:04d}"

        # UE通常输出格式：<sequence_name>.<frame>.png
        possible_patterns = [
            f"*{frame_str}.png",
            f"frame_{frame_str}.png",
            f"*{frame_number}.png",
        ]

        for pattern in possible_patterns:
            files = list(output_dir.glob(pattern))
            if files:
                return files[0]

        return None


def get_renderer(engine: RenderEngine) -> BaseRenderer:
    """
    获取渲染器实例

    Args:
        engine: 渲染引擎类型

    Returns:
        渲染器实例
    """
    if engine == RenderEngine.MAYA:
        return MayaRenderer(settings.maya_executable)
    elif engine == RenderEngine.UE:
        return UERenderer(settings.ue_executable)
    else:
        raise ValueError(f"不支持的渲染引擎: {engine}")
