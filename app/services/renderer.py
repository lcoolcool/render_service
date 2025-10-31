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
        output_dir: Path
    ) -> Path:
        """
        渲染单帧

        Args:
            project_file: 工程文件路径
            frame_number: 帧序号
            output_dir: 输出目录

        Returns:
            渲染结果文件路径
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
        output_dir: Path
    ) -> Path:
        """使用Maya批处理模式渲染单帧"""

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 构建Maya渲染命令
        # "C:\SoftWare\Maya\maya2025\Maya 2025.3.1\Maya2025\bin\Render.exe" -r arnold -rd C:\Project\WJMRender\Render -s 1 -e 24 -b 1 "C:\Project\WJMRender\MayaProject\scenes\Qiu_Test_v001.ma"
        # mayabatch -file <project.ma> -render <renderer> -s <start> -e <end> -rd <output_dir>
        command = [
            str(self.executable),
            "-r", "arnold",  # 默认使用Arnold渲染器，可根据需要修改
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

        return output_file

    def _find_output_file(self, output_dir: Path, frame_number: int, stdout: str) -> Optional[Path]:
        """从Maya输出中查找渲染结果文件"""

        # 尝试从stdout中解析文件路径
        # Maya通常会输出类似 "Rendering: C:/path/to/image.0001.exr" 的信息
        pattern = r'(?:Rendering|Result):\s*([^\n]+\.(?:exr|png|jpg|jpeg|tif|tiff))'
        matches = re.findall(pattern, stdout, re.IGNORECASE)

        if matches:
            return Path(matches[-1].strip())

        # 如果无法从输出解析，尝试在输出目录中查找
        # 常见的Maya输出文件名格式：<scenename>.<frame>.<ext>
        frame_str = f"{frame_number:04d}"  # 补齐到4位数字

        for ext in ['.exr', '.png', '.jpg', '.jpeg', '.tif']:
            # 尝试多种可能的文件名格式
            possible_files = list(output_dir.glob(f"*{frame_str}{ext}"))
            if possible_files:
                return possible_files[0]

            possible_files = list(output_dir.glob(f"*.{frame_number}{ext}"))
            if possible_files:
                return possible_files[0]

        return None


class UERenderer(BaseRenderer):
    """Unreal Engine渲染器"""

    def render_frame(
        self,
        project_file: str,
        frame_number: int,
        output_dir: Path
    ) -> Path:
        """使用UE命令行模式渲染单帧"""

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

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
            "-MovieQuality=100",
            "-ResX=1920",
            "-ResY=1080",
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

        return output_file

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
