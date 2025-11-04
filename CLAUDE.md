# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 FastAPI + Celery 的异步渲染任务管理服务，专门用于 Maya 和 Unreal Engine 的渲染作业调度。采用异步架构，通过 Redis 消息队列实现任务分发，支持优先级队列、逐帧进度跟踪和失败重试。

**核心特性**：
- **OSS 集成**：工程文件存储在阿里云OSS，支持自动下载和解压
- **文件隔离**：每个任务都有独立的工作空间（按用户ID和任务ID隔离，包含 source/、project/、renders/ 三个子目录）
- **手动清理**：任务完成后工作空间保留，支持失败帧重试，用户可按需清理
- **单帧重试**：支持重试失败的帧，无需重新下载文件
- **压缩支持**：支持 gzip (.gz) 和 zip 格式的压缩文件

## 核心架构

### 技术栈
- **API 层**: FastAPI + Uvicorn
- **任务队列**: Celery + Redis（使用 `--pool=solo` 以支持 Windows）
- **数据库**: Tortoise ORM + SQLite（异步 ORM）
- **对象存储**: 阿里云 OSS（oss2 SDK）
- **渲染引擎**: Maya (Arnold) 和 Unreal Engine

### 架构模式
- **异步处理**: API 接收请求后立即返回，Celery Worker 异步执行渲染
- **优先级队列**: 三个队列 (high_priority, default, low_priority)，根据任务优先级 (0-10) 自动路由
- **逐帧追踪**: 每一帧都是独立的 RenderFrame 记录，实时更新状态和进度
- **数据库连接管理**: Celery Worker 通过自定义 DatabaseTask 基类在任务开始前初始化 Tortoise ORM 连接

### 关键流程
1. 用户通过 `/api/tasks/` 创建渲染任务 → RenderTask 记录写入数据库（包含 OSS 文件路径）
2. API 层根据 priority 分发 Celery 任务到对应队列
3. Worker 获取任务，调用 `app.celery_app.tasks.render_task`
4. **文件准备阶段**：
   - 创建隔离的工作空间目录 (`workspace/{unionid}/{task_id}`)，包含 source/、project/、renders/ 三个子目录
   - 从 OSS 下载工程文件到 `source/` 目录
   - 如果是压缩文件，解压到 `project/` 目录
   - 查找并更新本地工程文件路径
5. **渲染阶段**：逐帧调用渲染引擎适配器 (`services.renderer`)，输出到 `renders/` 目录，更新 RenderFrame 状态
6. **完成阶段**：任务完成/失败/取消后，工作空间保留（支持失败帧重试）
8. 用户可通过 `/api/tasks/{id}/status` 轮询进度，失败帧可通过 `/api/tasks/{id}/frames/{frame_number}/retry` 重试

## 常用命令

### 启动服务
```bash
# 启动 FastAPI API 服务（开发模式）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 Celery Worker（Windows 必须使用 --pool=solo）
celery -A app.celery_app.celery worker --pool=solo --loglevel=info -Q high_priority,default,low_priority
```

### 依赖管理
```bash
# 安装依赖
pip install -r requirements.txt

# 如果添加新依赖，更新 requirements.txt
pip freeze > requirements.txt
```

### Redis
```bash
# 启动 Redis（Windows）
redis-server.exe

# 检查 Redis 连接
redis-cli ping
```

## 重要实现细节

### 1. Windows 兼容性
- Celery 在 Windows 下不支持 `fork`，**必须**使用 `--pool=solo` 启动 Worker
- 所有文件路径使用 `pathlib.Path` 处理，兼容 Windows 反斜杠

### 2. 数据库异步操作
- 使用 Tortoise ORM，所有数据库操作都是异步的（`await`）
- Celery 任务内部使用 `asyncio.get_event_loop().run_until_complete()` 包装异步调用
- 数据库连接在 Worker 启动时通过 `DatabaseTask.before_start()` 初始化

### 3. 任务取消机制
- 任务的 `celery_task_id` 字段保存 Celery 任务 ID
- 取消时通过 `celery_app.control.revoke(task_id, terminate=True)` 终止任务
- Worker 内部在渲染每帧前检查 `task.status == TaskStatus.CANCELLED`，如果已取消则抛出 `Ignore` 异常

### 4. 渲染引擎适配器模式
- `services/renderer.py` 定义 `BaseRenderer` 抽象基类
- `MayaRenderer` 和 `UERenderer` 实现具体渲染逻辑
- 通过 `get_renderer(engine)` 工厂函数获取实例
- 每个渲染器负责：
  - 构建命令行参数
  - 执行子进程并捕获输出
  - 解析输出查找渲染结果文件

### 5. Maya 渲染器特殊说明
- 使用 `Render.exe`（而非 `mayabatch.exe`）
- 默认渲染器为 Arnold (`-r arnold`)
- 输出文件名由 Maya 决定，需要通过正则表达式或 glob 模式查找
- 常见输出格式：`<scene_name>.<frame>.exr`

### 6. 优先级队列路由
- 任务优先级 0-3 → `low_priority` 队列
- 任务优先级 4-7 → `default` 队列
- 任务优先级 8-10 → `high_priority` 队列
- `celery_app/celery.py` 中的 `task_routes` 配置任务到队列的映射

### 7. OSS 文件管理
- **文件存储**：工程文件存储在阿里云OSS，支持压缩格式
- **下载服务** (`services/oss_storage.py`)：封装 OSS SDK，提供下载、上传、删除等操作
- **解压服务** (`services/file_handler.py`)：支持 .gz 和 .zip 格式
- **文件准备服务** (`services/file_preparation.py`)：整合下载、解压、查找工程文件的完整流程

### 8. 文件隔离机制
- **目录结构**（所有目录名称由系统统一配置）：
  ```
  C:/workspace/
    └── {unionid}/                    # 用户级隔离
        └── {task_id}/                # 任务级隔离
            ├── source/               # OSS下载的原始文件（通过 SOURCE_DIR_NAME 设置）
            ├── project/              # 解压后的工程文件（通过 PROJECT_DIR_NAME 设置）
            └── Sys_Default_Renders/  # 渲染输出文件（通过 RENDERS_DIR_NAME 设置）
  ```
- **手动清理**：任务完成、失败或取消后工作空间保留，用户可通过 API 手动清理
- **单帧重试**：失败的帧可以重新渲染，复用已下载的工程文件，无需重新从 OSS 下载
- **批量清理**：支持按状态、时间、用户ID批量清理工作空间

## 环境配置

### 必需的环境变量（.env 文件）
```env
# 数据库
DATABASE_URL=sqlite://db.sqlite3

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 阿里云OSS配置（必需）
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name

# 文件存储
# 工作空间根目录（每个任务都会创建独立的子目录：{unionid}/{task_id}/）
# 默认包含：source/、project/、Sys_Default_Renders/ 三个子目录
WORKSPACE_ROOT_DIR=C:/workspace

# 工作空间子目录名称（系统统一配置）
SOURCE_DIR_NAME=source
PROJECT_DIR_NAME=project
RENDERS_DIR_NAME=Sys_Default_Renders

# 渲染引擎路径（必须根据实际安装路径修改）
MAYA_EXECUTABLE=C:/Program Files/Autodesk/Maya2024/bin/Render.exe
UE_EXECUTABLE=C:/Program Files/Epic Games/UE_5.3/Engine/Binaries/Win64/UnrealEditor-Cmd.exe
```

## 数据模型关系

### RenderTask (app/models/task.py)
- **主要字段**:
  - `unionid`: 用户ID
  - `oss_file_path`: OSS上的文件路径
  - `is_compressed`: 是否为压缩文件
  - `project_file`: 本地工程文件路径（下载解压后）
  - `workspace_dir`: 任务工作空间目录
  - `render_engine` (maya/ue), `status`, `priority`, `celery_task_id`
- **关系**: 一对多关联 `RenderFrame`（通过 `frames` 反向关系）
- **排序**: 按优先级和创建时间降序 (`ordering = ["-priority", "-created_at"]`)

### RenderFrame (app/models/frame.py)
- **主要字段**: `task_id`, `frame_number`, `status`, `output_path`
- **生命周期**: pending → rendering → completed/failed

## API 端点

### 任务管理 (app/api/tasks.py)
- `POST /api/tasks/` - 创建渲染任务
- `GET /api/tasks/{id}/status` - 查询任务状态和进度
- `GET /api/tasks/{id}/frames` - 获取所有渲染帧信息
- `POST /api/tasks/{id}/cancel` - 取消任务
- `POST /api/tasks/{id}/cleanup` - 清理单个任务的工作空间
- `POST /api/tasks/cleanup` - 批量清理任务工作空间（支持按状态、时间、用户ID过滤）
- `POST /api/tasks/{id}/frames/{frame_number}/retry` - 重试渲染失败的帧

### 文件服务 (app/api/files.py)
- `GET /api/files/download/{frame_id}` - 下载渲染结果
- `GET /api/files/preview/{frame_id}` - 在线预览渲染结果

## 开发注意事项

### 添加新的渲染引擎
1. 在 `models/task.py` 的 `RenderEngine` 枚举中添加新引擎
2. 在 `services/renderer.py` 创建新的 Renderer 类，继承 `BaseRenderer`
3. 实现 `render_frame()` 方法
4. 在 `get_renderer()` 工厂函数中添加分支
5. 在 `config.py` 添加对应的可执行文件路径配置

### 修改优先级路由逻辑
- 优先级路由在 `api/tasks.py` 的 `create_task()` 函数中决定
- 通过 `queue` 参数传递给 `render_task.apply_async()`
- 如需修改映射规则，编辑该函数的条件判断

### 调试 Celery 任务
- Worker 日志输出在控制台，包含任务 ID、状态和错误信息
- 使用 `--loglevel=debug` 获取更详细的日志
- 任务失败时错误信息会记录在 `RenderTask.error_message` 和 `RenderFrame.error_message`

### 数据库迁移
- 当前使用 `Tortoise.generate_schemas()` 自动生成表结构（仅限开发）
- 生产环境建议使用 Aerich 进行版本化迁移（已在 TORTOISE_ORM 配置中引入）

## 测试策略

### 单元测试
- 测试渲染器适配器：模拟命令行输出，验证文件查找逻辑
- 测试任务状态转换：验证 pending → running → completed 流程

### 集成测试
- 使用测试渲染引擎（或 mock）验证完整渲染流程
- 测试任务取消和重试机制

### 手动测试
```bash
# 创建测试任务（使用OSS文件路径）
curl -X POST "http://localhost:8000/api/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "unionid": "user123",
    "oss_file_path": "projects/user123/test_scene.ma.gz",
    "is_compressed": true,
    "render_engine": "maya",
    "task_info": {
      "renderer": "arnold"
    },
    "total_frames": 10
  }'

# 查询任务详情
curl "http://localhost:8000/api/tasks/1"

# 查询任务状态
curl "http://localhost:8000/api/tasks/1/status"

# 取消任务
curl -X POST "http://localhost:8000/api/tasks/1/cancel"
```

## 常见问题排查

### Worker 无法启动
- 检查 Redis 是否运行（`redis-cli ping`）
- 确认使用了 `--pool=solo` 参数（Windows 必需）
- 检查 `DATABASE_URL` 路径是否正确

### 渲染任务一直 pending
- 检查 Worker 是否正常运行并监听正确的队列
- 确认 `celery_task_id` 是否已写入数据库
- 检查 Redis 队列是否有积压（`redis-cli LLEN <queue_name>`）

### 渲染引擎报错
- 验证 `.env` 中的可执行文件路径是否正确
- 检查项目文件路径是否存在且格式正确
- 查看 Worker 日志中的完整命令行参数和错误输出

### OSS 文件下载失败
- 检查 `.env` 中的 OSS 配置是否正确（AccessKey、Bucket等）
- 确认 OSS 文件路径存在（使用 OSS 控制台或 ossutil 工具验证）
- 检查网络连接和防火墙设置
- 查看 Worker 日志中的详细错误信息

### 工作空间管理
- 任务完成/失败后，工作空间**不会自动清理**（方便失败帧重试）
- 清理单个任务：`POST /api/tasks/{id}/cleanup`
- 批量清理：`POST /api/tasks/cleanup?status=completed&days=7`（清理7天前已完成的任务）
- 手动删除：直接删除 `C:/workspace/{unionid}/{task_id}` 目录
- 定期清理建议：使用批量清理接口定期清理旧任务，避免磁盘空间不足