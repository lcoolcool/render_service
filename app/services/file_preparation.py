"""文件准备服务（下载+解压+工程文件查找）"""
import logging
import shutil
from pathlib import Path
from typing import Tuple, Optional
from app.config import settings
from app.services.oss_storage import OSSStorageService
from app.services.file_handler import FileHandlerService
from app.models.task import RenderEngine

logger = logging.getLogger(__name__)


class FilePreparationService:
    """文件准备服务类，负责任务的文件下载和解压"""

    def __init__(self):
        self.oss_service = OSSStorageService()
        self.file_handler = FileHandlerService()

    def prepare_project_files(
        self,
        unionid: str,
        task_id: int,
        oss_file_path: Optional[str],
        file_path: Optional[str],
        is_compressed: bool,
        render_engine: RenderEngine,
        task_info: Optional[dict] = None
    ) -> Tuple[Path, Path, Path]:
        """
        准备渲染工程文件（完整流程）

        流程:
        - 如果提供了file_path（本地文件），直接使用本地文件
        - 如果提供了oss_file_path（OSS文件），则：
          1. 创建任务隔离的工作空间目录
          4. 查找工程文件路径
          5. 返回工程文件路径、工作空间路径和渲染输出目录（系统统一配置）

        Args:
            unionid: 用户ID（用于目录隔离）
            task_id: 任务ID（用于目录隔离）
            oss_file_path: OSS文件路径（可选）
            file_path: 本地文件路径（可选）
            is_compressed: 是否为压缩文件
            render_engine: 渲染引擎类型（用于确定工程文件扩展名）
            task_info: 任务配置信息（用于渲染引擎特定参数）

        Returns:
            (工程文件路径, 工作空间目录路径, 渲染输出目录)

        Raises:
            FileNotFoundError: 文件下载或查找失败
            ValueError: 解压失败或不支持的格式
        """
        task_info = task_info or {}

        # 使用本地文件
        if file_path:
            return self._prepare_local_file(unionid, task_id, file_path, is_compressed, render_engine, task_info)
        # 使用OSS文件
        elif oss_file_path:
            return self._prepare_oss_file(unionid, task_id, oss_file_path, is_compressed, render_engine, task_info)
        else:
            raise ValueError("必须提供 oss_file_path 或 file_path 其中之一")

    def _prepare_local_file(
        self,
        unionid: str,
        task_id: int,
        file_path: str,
        is_compressed: bool,
        render_engine: RenderEngine,
        task_info: dict
    ) -> Tuple[Path, Path, Path]:
        """
        准备本地文件（无需从OSS下载）

        流程:
        1. 创建任务隔离的工作空间目录
        2. 如果是压缩文件，复制到工作空间目录并解压到工作空间目录
        3. 如果不是压缩文件，复制到工作空间目录
        4. 查找工程文件路径
        5. 返回工程文件路径、工作空间路径和渲染输出目录

        Args:
            unionid: 用户ID
            task_id: 任务ID
            file_path: 本地文件路径
            is_compressed: 是否为压缩文件
            render_engine: 渲染引擎类型
            task_info: 任务配置信息

        Returns:
            (工程文件路径, 工作空间目录路径, 渲染输出目录)

        Raises:
            FileNotFoundError: 文件不存在或查找失败
            ValueError: 解压失败或不支持的格式
        """
        try:
            # 验证本地文件是否存在
            local_file = Path(file_path)
            if not local_file.exists():
                raise FileNotFoundError(f"本地文件不存在: {file_path}")

            # 1. 创建任务工作空间目录结构（使用系统配置的固定目录名）
            task_workspace_dir = self._create_task_workspace(unionid, task_id)
            renders_dir_name = settings.renders_dir_name

            renders_dir = task_workspace_dir / renders_dir_name
            renders_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"创建任务工作目录: {task_workspace_dir}")
            logger.info(f"使用本地文件: {file_path}")

            # 2. 处理压缩文件
            if is_compressed:
                copied_file = task_workspace_dir / local_file.name
                shutil.copy2(str(local_file), str(copied_file))
                logger.info(f"文件为压缩格式，已复制到任务工作目录，开始解压...")

                # 解压到project目录
                self.file_handler.decompress_file(
                    compressed_file=local_file,
                    output_dir=task_workspace_dir,
                    delete_after=False  # 保留原压缩文件
                )
            else:
                # 非压缩文件，直接复制到project目录
                logger.info(f"文件无需解压，直接复制")
                shutil.copy2(str(local_file), str(task_workspace_dir / local_file.name))

            # 3. 查找工程文件
            project_file = self._find_project_file(task_workspace_dir, render_engine)
            if not project_file:
                raise FileNotFoundError(
                    f"在 {task_workspace_dir} 中未找到有效的工程文件"
                )

            logger.info(f"文件准备完成: {project_file}")
            return project_file, task_workspace_dir, renders_dir

        except Exception as e:
            logger.error(f"本地文件准备失败: {e}")
            # 清理失败的工作空间
            if 'workspace_dir' in locals():
                self.cleanup_workspace(task_workspace_dir)
            raise

    def _prepare_oss_file(
        self,
        unionid: str,
        task_id: int,
        oss_file_path: str,
        is_compressed: bool,
        render_engine: RenderEngine,
        task_info: dict
    ) -> Tuple[Path, Path, Path]:
        """
        准备OSS文件（仿照本地文件准备流程）

        流程:
        1. 创建任务隔离的工作空间目录
        2. 从OSS下载文件到工作空间目录
        3. 如果是压缩文件，解压到工作空间目录
        4. 查找工程文件路径
        5. 返回工程文件路径、工作空间路径和渲染输出目录

        Args:
            unionid: 用户ID
            task_id: 任务ID
            oss_file_path: OSS文件路径
            is_compressed: 是否为压缩文件
            render_engine: 渲染引擎类型
            task_info: 任务配置信息

        Returns:
            (工程文件路径, 工作空间目录路径, 渲染输出目录)

        Raises:
            FileNotFoundError: 文件下载或查找失败
            ValueError: 解压失败或不支持的格式
        """
        try:
            # 1. 创建任务工作空间目录结构（使用系统配置的固定目录名）
            task_workspace_dir = self._create_task_workspace(unionid, task_id)
            renders_dir_name = settings.renders_dir_name or "Renders"

            renders_dir = task_workspace_dir / renders_dir_name
            renders_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"创建任务工作目录: {task_workspace_dir}")

            # 2. 从OSS下载文件到工作空间目录
            filename = Path(oss_file_path).name
            downloaded_file = task_workspace_dir / filename

            logger.info(f"从OSS下载文件: {oss_file_path}")
            self.oss_service.download_file(
                oss_path=oss_file_path,
                local_path=downloaded_file
            )

            # 3. 处理压缩文件
            if is_compressed:
                logger.info(f"文件为压缩格式，开始解压...")
                # 解压到工作空间目录
                self.file_handler.decompress_file(
                    compressed_file=downloaded_file,
                    output_dir=task_workspace_dir,
                    delete_after=False
                )
            else:
                # 非压缩文件，已经在工作空间目录中，无需移动
                logger.info(f"文件无需解压，直接使用")

            # 4. 查找工程文件
            project_file = self._find_project_file(task_workspace_dir, render_engine)
            if not project_file:
                raise FileNotFoundError(
                    f"在 {task_workspace_dir} 中未找到有效的工程文件"
                )

            logger.info(f"文件准备完成: {project_file}")
            return project_file, task_workspace_dir, renders_dir

        except Exception as e:
            logger.error(f"OSS文件准备失败: {e}")
            # 清理失败的工作空间
            if 'task_workspace_dir' in locals():
                self.cleanup_workspace(task_workspace_dir)
            raise

    def _create_task_workspace(self, unionid: str, task_id: int) -> Path:
        """
        创建任务工作空间目录

        目录结构:
        workspace_root/
          └── {unionid}/
              └── {task_id}/

        Args:
            unionid: 用户ID
            task_id: 任务ID

        Returns:
            工作空间目录路径
        """
        workspace_dir = settings.workspace_root_dir / unionid / str(task_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir

    def _find_project_file(
        self,
        project_dir: Path,
        render_engine: RenderEngine
    ) -> Optional[Path]:
        """
        根据渲染引擎类型查找工程文件

        Args:
            project_dir: 工程目录
            render_engine: 渲染引擎类型

        Returns:
            工程文件路径，如果未找到返回None
        """
        # 根据渲染引擎确定文件扩展名
        if render_engine == RenderEngine.MAYA:
            extensions = ['.ma', '.mb']  # Maya ASCII 和 Binary 格式
        elif render_engine == RenderEngine.UE:
            extensions = ['.uproject']  # Unreal Engine 工程文件
        else:
            raise ValueError(f"不支持的渲染引擎: {render_engine}")

        # 查找工程文件
        project_file = self.file_handler.find_project_file(
            directory=project_dir,
            extensions=extensions
        )

        return project_file

    def cleanup_workspace(self, workspace_dir: Path) -> bool:
        """
        清理任务工作空间

        Args:
            workspace_dir: 工作空间目录路径

        Returns:
            是否清理成功
        """
        try:
            logger.info(f"清理工作空间: {workspace_dir}")
            return self.file_handler.cleanup_directory(workspace_dir)
        except Exception as e:
            logger.error(f"清理工作空间失败: {e}")
            return False

    def get_workspace_size(self, workspace_dir: Path) -> int:
        """
        获取工作空间大小

        Args:
            workspace_dir: 工作空间目录路径

        Returns:
            工作空间大小（字节）
        """
        return self.file_handler.get_directory_size(workspace_dir)
