"""FastAPI主应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from app.config import settings
from app.api import tasks, files


# 数据库配置
TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "models": {
            "models": ["app.models.task", "app.models.frame", "aerich.models"],
            "default_connection": "default",
        },
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await Tortoise.init(
        db_url=settings.database_url,
        modules={"models": ["app.models.task", "app.models.frame"]}
    )
    # 自动生成数据库表
    await Tortoise.generate_schemas()

    print("数据库初始化完成")
    print(f"渲染输出目录: {settings.render_output_dir}")
    print(f"缩略图目录: {settings.thumbnail_dir}")

    yield

    # 关闭时清理资源
    await Tortoise.close_connections()
    print("数据库连接已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="渲染服务API",
    description="Maya/UE渲染任务管理服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks.router)
app.include_router(files.router)


@app.get("/", summary="根路径")
async def root():
    """API根路径，返回服务信息"""
    return {
        "service": "渲染服务API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", summary="健康检查")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "database": "connected"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True  # 开发模式，生产环境应设为False
    )
