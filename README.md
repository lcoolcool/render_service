# 渲染服务 API

一个基于 FastAPI + Celery 的异步渲染任务管理服务，支持 Maya 和 Unreal Engine 渲染任务。

## 功能特性

- ✅ **异步任务处理**: 使用 Celery 实现异步渲染，不阻塞 API 请求
- ✅ **多渲染引擎支持**: 支持 Maya 和 Unreal Engine
- ✅ **任务优先级队列**: 支持高、中、低三级优先级
- ✅ **逐帧进度跟踪**: 每渲染完成一帧都会记录，支持实时查询
- ✅ **自动缩略图生成**: 渲染完成后自动生成预览缩略图
- ✅ **失败自动重试**: 支持配置自动重试次数
- ✅ **任务取消功能**: 可随时取消正在执行的任务
- ✅ **Windows 原生支持**: 针对 Windows 系统优化

## 系统架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   用户请求   │─────▶│  FastAPI API  │─────▶│    Redis    │
└─────────────┘      └──────────────┘      └─────────────┘
                            │                      │
                            │                      ▼
                            │              ┌─────────────┐
                            │              │Celery Worker│
                            │              └─────────────┘
                            │                      │
                            ▼                      ▼
                    ┌──────────────┐      ┌─────────────┐
                    │SQLite数据库   │      │Maya/UE引擎   │
                    └──────────────┘      └─────────────┘
```

## 技术栈
- **Web框架**: FastAPI
- **异步任务**: Celery + Redis
- **数据库**: Tortoise ORM + SQLite
- **数据验证**: Pydantic
- **图像处理**: Pillow

## 快速开始

### 1. 环境要求

- Python 3.8+
- Redis for Windows
- Maya 或 Unreal Engine（根据需要）

### 2. 安装 uv 和依赖

**传统方式（如果不使用 uv）：**
```bash
pip install -r requirements.txt
```

### 3. 安装 Redis

下载 Redis for Windows：
https://github.com/microsoftarchive/redis/releases

解压后运行 `redis-server.exe`

### 4. 配置环境变量

编辑 `.env` 文件，配置渲染引擎路径和其他参数：

```env
# 数据库配置
DATABASE_URL=sqlite://db.sqlite3

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 文件存储配置
# 工作空间根目录（每个任务都会创建独立的子目录：{unionid}/{task_id}/）
# 默认包含：source/、project/、Sys_Default_Renders/ 三个子目录
# 可通过 task_info 自定义目录名称
WORKSPACE_ROOT_DIR=C:/workspace

# 渲染引擎配置（根据实际安装路径修改）
MAYA_EXECUTABLE=C:/Program Files/Autodesk/Maya2024/bin/mayabatch.exe
UE_EXECUTABLE=C:/Program Files/Epic Games/UE_5.3/Engine/Binaries/Win64/UnrealEditor-Cmd.exe

# 任务配置
MAX_RETRIES=3
DEFAULT_PRIORITY=5
```

### 5. 启动服务

**启动 API 服务**（使用虚拟环境）：
```bash
# 启动 API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 Worker（新开一个终端）
celery -A app.celery_app.celery worker --pool=solo --loglevel=info -Q high_priority,default,low_priority
```

## API 使用示例

### 创建渲染任务

```bash
curl -X POST "http://localhost:8000/api/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "unionid": "user123",
    "oss_file_path": "projects/user123/my_project.ma.gz",
    "is_compressed": true,
    "render_engine": "maya",
    "task_info": {
      "renderer": "arnold",
      "source_dir": "source",
      "project_dir": "project",
      "renders_dir": "Sys_Default_Renders"
    },
    "total_frames": 100
  }'
```

### 查询任务状态

```bash
curl "http://localhost:8000/api/tasks/1/status"
```

响应示例：
```json
{
  "id": 1,
  "status": "running",
  "progress_percentage": 45.0,
  "completed_frames": 45,
  "total_frames": 100,
  "error_message": null
}
```

### 获取任务的所有帧

```bash
curl "http://localhost:8000/api/tasks/1/frames"
```

### 下载渲染结果

```bash
curl "http://localhost:8000/api/files/download/1" --output frame_001.png
```

### 获取缩略图

```bash
curl "http://localhost:8000/api/files/thumbnail/1" --output thumb_001.jpg
```

### 取消任务

```bash
curl -X POST "http://localhost:8000/api/tasks/1/cancel"
```

## 项目结构

```
render_service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── models/              # 数据库模型
│   │   ├── task.py          # 任务模型
│   │   └── frame.py         # 渲染帧模型
│   ├── schemas/             # Pydantic 数据验证
│   │   ├── task.py
│   │   └── frame.py
│   ├── api/                 # API 路由
│   │   ├── tasks.py         # 任务管理接口
│   │   └── files.py         # 文件下载接口
│   ├── celery_app/          # Celery 配置
│   │   ├── celery.py        # Celery 实例
│   │   └── tasks.py         # 异步任务定义
│   ├── services/            # 业务逻辑
│   │   ├── renderer.py      # 渲染引擎适配器
│   │   └── thumbnail.py     # 缩略图生成
│   └── utils/               # 工具函数
├── pyproject.toml           # 项目配置（uv）
├── requirements.txt         # 依赖包（备用）
├── .env                     # 环境变量
├── start_api.bat           # API 启动脚本
├── start_worker.bat        # Worker 启动脚本
├── install.bat             # 依赖安装脚本
└── README.md               # 项目文档
```

## 数据库模型

### RenderTask（渲染任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| project_file | str | 工程文件路径 |
| render_engine | enum | 渲染引擎（maya/ue） |
| status | enum | 状态（pending/running/completed/failed/cancelled） |
| priority | int | 优先级（0-10） |
| total_frames | int | 总帧数 |
| completed_frames | int | 已完成帧数 |
| retry_count | int | 重试次数 |
| max_retries | int | 最大重试次数 |
| celery_task_id | str | Celery 任务 ID |
| error_message | str | 错误信息 |

### RenderFrame（渲染帧）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| task_id | int | 关联的任务 ID |
| frame_number | int | 帧序号 |
| status | enum | 状态（pending/rendering/completed/failed） |
| output_path | str | 渲染结果文件路径 |
| thumbnail_path | str | 缩略图路径 |
| render_time | float | 渲染耗时（秒） |
| error_message | str | 错误信息 |

## 配置说明

### 任务优先级

- **0-3**: 低优先级队列
- **4-7**: 默认优先级队列
- **8-10**: 高优先级队列

### 重试策略

- 渲染任务失败会自动重试，重试间隔为 60 秒
- 可通过 `max_retries` 参数配置最大重试次数
- 缩略图生成失败会重试，但不影响主任务

### 任务取消

- 调用取消接口后，Celery 会向 Worker 发送终止信号
- 正在渲染的帧会被标记为失败
- 待处理的帧不会被执行

## 常见问题
### Q: Windows 下 Celery 报错 "cannot pickle ..."

A: Windows 不支持 fork，必须使用 `--pool=solo` 参数启动 Worker。启动脚本已自动配置。

### Q: 如何查看 Celery 任务日志？

A: Worker 启动后会在控制台输出日志，包括任务执行状态和错误信息。

### Q: 渲染引擎路径配置错误怎么办？

A: 编辑 `.env` 文件，修改 `MAYA_EXECUTABLE` 或 `UE_EXECUTABLE` 为实际安装路径。

### Q: 如何监控任务进度？

A: 通过轮询 `/api/tasks/{task_id}/status` 接口获取实时进度。建议轮询间隔为 2-5 秒。

### Q: 支持并发渲染吗？

A: 支持。可以启动多个 Worker 实例来提高并发能力。每个 Worker 会从队列中获取任务执行。

## 开发计划
- [ ] 支持更多渲染引擎（Blender、Cinema 4D等）
- [ ] WebSocket 实时推送进度
- [ ] 任务调度和定时执行
- [ ] 集群部署支持
- [ ] Web 管理界面

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue。
