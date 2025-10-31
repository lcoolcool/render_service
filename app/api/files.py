"""文件下载API路由"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.models.frame import RenderFrame

router = APIRouter(prefix="/api/files", tags=["文件管理"])


@router.get("/download/{frame_id}", summary="下载渲染结果")
async def download_render_output(frame_id: int):
    """
    下载指定帧的渲染结果文件

    - **frame_id**: 渲染帧ID
    """
    # 获取帧信息
    frame = await RenderFrame.get_or_none(id=frame_id)

    if not frame:
        raise HTTPException(status_code=404, detail=f"渲染帧不存在: {frame_id}")

    if not frame.output_path:
        raise HTTPException(status_code=404, detail="该帧还没有渲染结果")

    output_path = Path(frame.output_path)

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="渲染结果文件不存在")

    # 返回文件
    return FileResponse(
        path=str(output_path),
        filename=output_path.name,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{output_path.name}"'
        }
    )


@router.get("/thumbnail/{frame_id}", summary="获取缩略图")
async def get_thumbnail(frame_id: int):
    """
    获取指定帧的缩略图

    - **frame_id**: 渲染帧ID
    """
    # 获取帧信息
    frame = await RenderFrame.get_or_none(id=frame_id)

    if not frame:
        raise HTTPException(status_code=404, detail=f"渲染帧不存在: {frame_id}")

    if not frame.thumbnail_path:
        raise HTTPException(status_code=404, detail="该帧还没有缩略图")

    thumbnail_path = Path(frame.thumbnail_path)

    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="缩略图文件不存在")

    # 返回图片文件
    return FileResponse(
        path=str(thumbnail_path),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400"  # 缓存1天
        }
    )


@router.get("/preview/{frame_id}", summary="在线预览渲染结果")
async def preview_render_output(frame_id: int):
    """
    在线预览渲染结果（适用于图像文件）

    - **frame_id**: 渲染帧ID
    """
    # 获取帧信息
    frame = await RenderFrame.get_or_none(id=frame_id)

    if not frame:
        raise HTTPException(status_code=404, detail=f"渲染帧不存在: {frame_id}")

    if not frame.output_path:
        raise HTTPException(status_code=404, detail="该帧还没有渲染结果")

    output_path = Path(frame.output_path)

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="渲染结果文件不存在")

    # 根据文件扩展名确定MIME类型
    ext = output_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".exr": "image/x-exr",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }

    media_type = mime_types.get(ext, "application/octet-stream")

    # 返回文件用于在线预览
    return FileResponse(
        path=str(output_path),
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600"  # 缓存1小时
        }
    )
