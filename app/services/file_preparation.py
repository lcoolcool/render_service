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
        render_engine: RenderEngine
    ) -> Tuple[Path, Path, Path]:
        """
        准备渲染工程文件（完整流程）

        流程:
        - 如果提供了file_path（本地文件），直接使用本地文件
        - 如果提供了oss_file_path（OSS文件），则：
          1. 创建任务隔离的工作空间目录
          2. 从OSS下载文件到 source/ 目录
          3. 如果是压缩文件，解压到 project/ 目录
          4. 查找工程文件路径
          5. 返回工程文件路径、工作空间路径和渲染输出目录

        Args:
            unionid: 用户ID（用于目录隔离）
            task_id: 任务ID（用于目录隔离）
            oss_file_path: OSS文件路径（可选）
            file_path: 本地文件路径（可选）
            is_compressed: 是否为压缩文件
            render_engine: 渲染引擎类型（用于确定工程文件扩展名）

        Returns:
            (工程文件路径, 工作空间目录路径, 渲染输出目录)

        Raises:
            FileNotFoundError: 文件下载或查找失败
            ValueError: 解压失败或不支持的格式
        """
        # 使用本地文件
        if file_path:
            return self._prepare_local_file(unionid, task_id, file_path, is_compressed, render_engine)
        # 使用OSS文件
        elif oss_file_path:
            return self._prepare_oss_file(unionid, task_id, oss_file_path, is_compressed, render_engine)
        else:
            raise ValueError("必须提供 oss_file_path 或 file_path 其中之一")

    def _prepare_local_file(
        self,
        unionid: str,
        task_id: int,
        file_path: str,
        is_compressed: bool,
        render_engine: RenderEngine
    ) -> Tuple[Path, Path, Path]:
        """
        准备本地文件（无需从OSS下载）

        流程:
        1. 创建任务隔离的工作空间目录
        2. 如果是压缩文件，复制到source目录并解压到project目录
        3. 如果不是压缩文件，复制到project目录
        4. 查找工程文件路径
        5. 返回工程文件路径、工作空间路径和渲染输出目录

        Args:
            unionid: 用户ID
            task_id: 任务ID
            file_path: 本地文件路径
            is_compressed: 是否为压缩文件
            render_engine: 渲染引擎类型

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

            # 1. 创建工作空间目录结构
            workspace_dir = self._create_workspace(unionid, task_id)
            source_dir = workspace_dir / "source"
            project_dir = workspace_dir / "project"
            renders_dir = workspace_dir / "renders"

            source_dir.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            renders_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"创建工作空间: {workspace_dir}")
            logger.info(f"使用本地文件: {file_path}")

            # 2. 处理压缩文件
            if is_compressed:
                # 复制到source目录
                copied_file = source_dir / local_file.name
                shutil.copy2(str(local_file), str(copied_file))
                logger.info(f"文件为压缩格式，已复制到source目录，开始解压...")

                # 解压到project目录
                self.file_handler.decompress_file(
                    compressed_file=copied_file,
                    output_dir=project_dir,
                    delete_after=False  # 保留原压缩文件
                )
            else:
                # 非压缩文件，直接复制到project目录
                logger.info(f"文件无需解压，直接复制")
                shutil.copy2(str(local_file), str(project_dir / local_file.name))

            # 3. 查找工程文件
            project_file = self._find_project_file(project_dir, render_engine)
            if not project_file:
                raise FileNotFoundError(
                    f"在 {project_dir} 中未找到有效的工程文件"
                )

            logger.info(f"文件准备完成: {project_file}")
            return project_file, workspace_dir, renders_dir

        except Exception as e:
            logger.error(f"本地文件准备失败: {e}")
            # 清理失败的工作空间
            if 'workspace_dir' in locals():
                self.cleanup_workspace(workspace_dir)
            raise

    def _prepare_oss_file(
        self,
        unionid: str,
        task_id: int,
        oss_file_path: str,
        is_compressed: bool,
        render_engine: RenderEngine
    ) -> Tuple[Path, Path, Path]:
        """
        准备OSS文件（原有逻辑）

        流程:
        1. 创建任务隔离的工作空间目录
        2. 从OSS下载文件到 source/ 目录
        3. 如果是压缩文件，解压到 project/ 目录
        4. 查找工程文件路径
        5. 返回工程文件路径、工作空间路径和渲染输出目录

        Args:
            unionid: 用户ID
            task_id: 任务ID
            oss_file_path: OSS文件路径
            is_compressed: 是否为压缩文件
            render_engine: 渲染引擎类型

        Returns:
            (工程文件路径, 工作空间目录路径, 渲染输出目录)

        Raises:
            FileNotFoundError: 文件下载或查找失败
            ValueError: 解压失败或不支持的格式
        """
        try:
            # 1. 创建工作空间目录结构
            workspace_dir = self._create_workspace(unionid, task_id)
            source_dir = workspace_dir / "source"
            project_dir = workspace_dir / "project"
            renders_dir = workspace_dir / "renders"

            source_dir.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            renders_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"创建工作空间: {workspace_dir}")

            # 2. 从OSS下载文件
            filename = Path(oss_file_path).name
            downloaded_file = source_dir / filename

            logger.info(f"从OSS下载文件: {oss_file_path}")
            self.oss_service.download_file(
                oss_path=oss_file_path,
                local_path=downloaded_file
            )

            # 3. 处理压缩文件
            if is_compressed:
                logger.info(f"文件为压缩格式，开始解压...")
                self.file_handler.decompress_file(
                    compressed_file=downloaded_file,
                    output_dir=project_dir,
                    delete_after=True  # 解压后删除原压缩文件以节省空间
                )
            else:
                # 非压缩文件，直接移动到project目录
                logger.info(f"文件无需解压，直接使用")
                shutil.move(str(downloaded_file), str(project_dir / filename))

            # 4. 查找工程文件
            project_file = self._find_project_file(project_dir, render_engine)
            if not project_file:
                raise FileNotFoundError(
                    f"在 {project_dir} 中未找到有效的工程文件"
                )

            logger.info(f"文件准备完成: {project_file}")
            return project_file, workspace_dir, renders_dir

        except Exception as e:
            logger.error(f"文件准备失败: {e}")
            # 清理失败的工作空间
            if 'workspace_dir' in locals():
                self.cleanup_workspace(workspace_dir)
            raise

    def _create_workspace(self, unionid: str, task_id: int) -> Path:
        """
        创建任务工作空间目录

        目录结构:
        workspace_root/
          └── {unionid}/
              └── {task_id}/
                  ├── source/       # OSS下载的原始文件
                  ├── project/      # 解压后的工程文件
                  └── renders/      # 渲染输出文件

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
