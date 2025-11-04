"""渲染引擎适配器"""
import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.config import settings
from app.models.task import RenderEngine


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
        output_file = self._find_output_file(output_dir, frame_number, stdout)

        if not output_file or not output_file.exists():
            raise RuntimeError(f"未找到渲染输出文件，帧号: {frame_number}")

        return output_file, stdout, stderr

    def _find_output_file(self, output_dir: Path, frame_number: int, stdout: str) -> Optional[Path]:
        """
        从Maya输出中查找渲染结果文件

        查找策略（按优先级）：
        1. 从stdout日志解析文件路径
        2. 在输出目录中查找匹配帧号的图片文件
        3. 返回最新修改的图片文件（兜底方案）
        """

        # 策略1: 从stdout解析文件路径
        # Maya常见输出格式：
        # - "Rendering: C:/path/to/image.0001.exr"
        # - "Result: /path/to/scene.exr.0001"
        # - "Writing file: scene_0001.png"
        output_file = self._parse_output_from_stdout(stdout)
        if output_file and output_file.exists():
            return output_file

        # 策略2: 在输出目录中查找匹配的文件
        output_file = self._search_output_in_directory(output_dir, frame_number)
        if output_file:
            return output_file

        # 策略3: 兜底方案 - 返回最新修改的图片文件
        output_file = self._find_latest_image(output_dir)
        if output_file:
            return output_file

        return None

    def _parse_output_from_stdout(self, stdout: str) -> Optional[Path]:
        """从Maya的stdout日志中解析输出文件路径"""

        # 匹配常见的输出模式，支持多种图片格式
        patterns = [
            r'(?:Rendering|Result|Writing\s+file):\s*([^\n\r]+\.(?:exr|png|jpg|jpeg|tif|tiff|tga|bmp|iff))',
            r'Writing\s+([^\n\r]+\.(?:exr|png|jpg|jpeg|tif|tiff|tga|bmp|iff))',
            r'File\s+written:\s*([^\n\r]+\.(?:exr|png|jpg|jpeg|tif|tiff|tga|bmp|iff))',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, stdout, re.IGNORECASE)
            if matches:
                # 返回最后一个匹配（通常是最终的输出文件）
                file_path = Path(matches[-1].strip())
                # 清理可能的引号和空白字符
                file_path_str = str(file_path).strip('"\'')
                return Path(file_path_str)

        return None

    def _search_output_in_directory(self, output_dir: Path, frame_number: int) -> Optional[Path]:
        """
        在输出目录中查找匹配帧号的渲染文件

        支持的文件名格式：
        - scene.0001.exr （扩展名在最后）
        - scene.exr.0001 （扩展名在中间）
        - scene_0001.exr （下划线分隔）
        - scene-0001.exr （连字符分隔）
        """

        supported_exts = ('.exr', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.tga', '.bmp', '.iff')

        # 准备帧号的多种格式
        frame_patterns = [
            f"{frame_number:04d}",  # 0001
            f"{frame_number:05d}",  # 00001
            f"{frame_number:06d}",  # 000001
            str(frame_number),      # 1
        ]

        # 编译正则表达式：匹配包含帧号的文件名
        # 使用单词边界确保精确匹配（避免 frame 1 匹配到 frame 10）
        regex_patterns = []
        for frame_str in frame_patterns:
            # 匹配各种分隔符：点、下划线、连字符、或直接连接
            regex_patterns.append(
                re.compile(
                    rf'(?:^|[._-])({re.escape(frame_str)})(?:[._-]|$)',
                    re.IGNORECASE
                )
            )

        # 遍历输出目录中的所有文件（只遍历一次）
        best_match = None
        best_priority = -1

        for file_path in output_dir.iterdir():
            if not file_path.is_file():
                continue

            file_name = file_path.name
            file_name_lower = file_name.lower()

            # 检查是否为支持的图片格式
            if not any(file_name_lower.endswith(ext) or ext in file_name_lower for ext in supported_exts):
                continue

            # 检查文件名是否匹配帧号
            for priority, (frame_str, regex_pattern) in enumerate(zip(frame_patterns, regex_patterns)):
                if regex_pattern.search(file_name):
                    # 优先级：4位补齐 > 5位补齐 > 6位补齐 > 无补齐
                    if priority > best_priority:
                        best_priority = priority
                        best_match = file_path
                    break  # 找到匹配后跳出内层循环

        return best_match

    def _find_latest_image(self, output_dir: Path) -> Optional[Path]:
        """查找输出目录中最新修改的图片文件（兜底方案）"""

        supported_exts = ('.exr', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.tga', '.bmp', '.iff')

        image_files = []
        for file_path in output_dir.iterdir():
            if not file_path.is_file():
                continue

            # 检查扩展名（支持扩展名在中间或最后）
            file_name_lower = file_path.name.lower()
            if any(file_name_lower.endswith(ext) or ext in file_name_lower for ext in supported_exts):
                image_files.append(file_path)

        if not image_files:
            return None

        # 按修改时间排序，返回最新的
        image_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return image_files[0]


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
