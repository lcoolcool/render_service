# API 接口设计文档

> 渲染服务 REST API 规范
> 版本: v2.0
> 更新日期: 2025-11-04
> 基础框架: FastAPI

---

## 1. 设计原则

### 1.1 RESTful 规范

✅ **资源导向** - URL 表示资源，HTTP 方法表示操作
✅ **无状态** - 每个请求包含完整信息
✅ **统一接口** - GET/POST/PUT/DELETE 语义明确
✅ **分层系统** - API 网关 → 业务逻辑 → 数据层

### 1.2 命名规范

- **URL**: 小写 + 连字符 (如 `/api/tasks/scene-analyse`)
- **JSON 字段**: 小写 + 下划线 (如 `scene_file`, `created_at`)
- **枚举值**: 小写 + 下划线 (如 `task_status: "rendering"`)

### 1.3 版本控制

- 当前版本: **v1** (保持向后兼容)
- URL 前缀: `/api/` (未来可扩展为 `/api/v2/`)

---

## 2. 通用规范

### 2.1 请求头

```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>  (未来添加)
```

### 2.2 响应格式

#### 成功响应

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    // 业务数据
  }
}
```

#### 错误响应

```json
{
  "code": 400,
  "message": "参数错误",
  "detail": "test_frames 字段格式不正确",
  "errors": [
    {
      "field": "test_frames",
      "message": "必须是数字或逗号分隔的数字列表"
    }
  ]
}
```

### 2.3 HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | GET/PUT/DELETE 成功 |
| 201 | 已创建 | POST 创建资源成功 |
| 202 | 已接受 | 异步任务已接受 |
| 400 | 请求错误 | 参数校验失败 |
| 404 | 未找到 | 资源不存在 |
| 409 | 冲突 | 资源已存在 |
| 500 | 服务器错误 | 内部错误 |

### 2.4 分页规范

```
GET /api/tasks?page=1&page_size=20&sort_by=created_at&order=desc
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

## 3. 现有 API (保持不变)

### 3.1 创建渲染任务

```
POST /api/tasks/
```

**请求 Body**:

```json
{
  "unionid": "user123",
  "oss_file_path": "projects/user123/scene.ma.gz",
  "is_compressed": true,
  "render_engine": "maya",
  "task_info": {
    "renderer": "arnold",
    "source_dir": "source",
    "project_dir": "project",
    "renders_dir": "Sys_Default_Renders"
  },
  "total_frames": 100,
  "priority": 5
}
```

**响应**:

```json
{
  "code": 201,
  "message": "任务创建成功",
  "data": {
    "id": 123,
    "unionid": "user123",
    "status": "queued",
    "celery_task_id": "abc-123-def-456",
    "created_at": "2025-11-04T10:30:00Z"
  }
}
```

---

### 3.2 查询任务状态

```
GET /api/tasks/{id}/status
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "id": 123,
    "status": "rendering",
    "progress": 45.5,
    "total_frames": 100,
    "completed_frames": 45,
    "failed_frames": 1,
    "created_at": "2025-11-04T10:30:00Z",
    "started_at": "2025-11-04T10:31:00Z",
    "estimated_completion": "2025-11-04T12:00:00Z"
  }
}
```

---

### 3.3 取消任务

```
POST /api/tasks/{id}/cancel
```

**响应**:

```json
{
  "code": 200,
  "message": "任务取消成功",
  "data": {
    "id": 123,
    "status": "cancelled"
  }
}
```

---

## 4. 新增 API

### 4.1 场景分析

#### 分析场景文件

```
POST /api/scene/analyse
```

**功能**: 上传或指定场景文件,分析渲染设置和依赖资产

**请求 Body**:

```json
{
  "scene_file": "C:/Project/wolf.ma",  // 本地路径
  // 或
  "oss_file_path": "projects/user123/wolf.ma",  // OSS 路径
  "unionid": "user123"
}
```

**响应**:

```json
{
  "code": 200,
  "message": "场景分析完成",
  "data": {
    "scene_file": "C:/Project/wolf.ma",
    "scene_file_size": 841968626,
    "scene_file_hash": "6e57efc1fb88700dfc4820e160348f07",

    "scene_info": {
      "renderer": "arnold",
      "start_frame": 1,
      "end_frame": 100,
      "width": 2048,
      "height": 1152,
      "image_format": "exr",
      "render_camera": ["cameraShape1"],
      "sampling": {
        "camera": 7,
        "diffuse": 5,
        "specular": 5
      }
    },

    "asset_summary": {
      "total_count": 33,
      "total_size": 23748328,
      "missing_count": 92
    },

    "assets": [
      {
        "path": "C:/textures/wood.jpg",
        "size": 1024000,
        "type": "texture",
        "exists": true
      },
      {
        "path": "Y:/Render_Test/missing.jpg",
        "size": null,
        "type": "texture",
        "exists": false
      }
    ],

    "missing": [
      {
        "node": "file1",
        "path": "Y:/Render_Test/missing.jpg",
        "reason": "file_not_found"
      }
    ],

    "analyzed_at": "2025-11-04T10:30:00Z"
  }
}
```

**错误响应**:

```json
{
  "code": 400,
  "message": "场景文件不存在",
  "detail": "文件路径 'C:/Project/wolf.ma' 无法访问"
}
```

---

#### 获取缓存的分析结果

```
GET /api/scene/analyse/{scene_hash}
```

**功能**: 通过场景文件的 hash 获取缓存的分析结果

**响应**: 同上 (如果缓存存在)

---

### 4.2 文件管理

#### 检查文件是否已上传

```
POST /api/files/check-hashes
```

**功能**: 批量检查文件 hash,实现增量上传

**请求 Body**:

```json
{
  "hashes": [
    "6e57efc1fb88700dfc4820e160348f07",
    "abc123def456..."
  ]
}
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "existing": [
      {
        "hash": "6e57efc1fb88700dfc4820e160348f07",
        "asset_id": 456,
        "storage_path": "assets/6e57efc1fb88700dfc4820e160348f07"
      }
    ],
    "missing": [
      "abc123def456..."
    ]
  }
}
```

---

#### 上传文件 (带去重)

```
POST /api/files/upload
```

**功能**: 上传文件到 OSS,自动去重

**请求** (multipart/form-data):

```
file: <binary>
hash: "6e57efc1fb88700dfc4820e160348f07"
xxhash: "7021565326244519815"
file_type: "texture"
unionid: "user123"
```

**响应**:

```json
{
  "code": 201,
  "message": "文件上传成功",
  "data": {
    "asset_id": 789,
    "file_hash": "6e57efc1fb88700dfc4820e160348f07",
    "storage_path": "assets/6e57efc1fb88700dfc4820e160348f07",
    "uploaded": true,  // false 表示文件已存在,跳过上传
    "file_size": 1024000
  }
}
```

---

#### 获取文件下载链接

```
GET /api/files/download-url/{asset_id}
```

**功能**: 生成 OSS 临时下载链接

**响应**:

```json
{
  "code": 200,
  "data": {
    "asset_id": 789,
    "download_url": "https://oss.aliyuncs.com/...",
    "expires_at": "2025-11-04T11:30:00Z"
  }
}
```

---

### 4.3 任务管理 (扩展)

#### 创建任务 (扩展版)

```
POST /api/tasks/
```

**请求 Body** (扩展字段):

```json
{
  // === 现有字段 ===
  "unionid": "user123",
  "oss_file_path": "projects/user123/scene.ma",
  "render_engine": "maya",
  "total_frames": 100,
  "priority": 5,

  // === 新增: 测试帧 ===
  "test_frames": "50",           // 测试帧号
  "stop_after_test": true,       // 测试失败后停止

  // === 新增: 硬件需求 ===
  "ram": 64,                     // 所需内存 (GB)
  "gpu_count": 2,                // 所需 GPU 数量
  "hardware_config_id": "high_performance",

  // === 新增: 超时控制 ===
  "frame_timeout": 43200,        // 单帧超时 (秒)
  "task_timeout": 86400,         // 任务超时 (秒)

  // === 新增: CG 软件信息 ===
  "cg_version": "2024",
  "renderer": "arnold",
  "plugins": {
    "mtoa": "5.5.1"
  }
}
```

**响应**:

```json
{
  "code": 201,
  "message": "任务创建成功",
  "data": {
    "id": 123,
    "status": "queued",
    "test_frames": "50",
    "hardware_config": {
      "id": "high_performance",
      "name": "高性能配置",
      "ram": 64,
      "gpu_count": 2
    },
    "estimated_cost": 12.5,
    "created_at": "2025-11-04T10:30:00Z"
  }
}
```

---

#### 查询任务详情 (扩展版)

```
GET /api/tasks/{id}
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "id": 123,
    "unionid": "user123",
    "status": "rendering",
    "progress": 45.5,

    // 场景信息
    "scene_file": "projects/user123/scene.ma",
    "scene_file_hash": "6e57efc1...",
    "scene_file_size": 841968626,

    // 测试帧
    "test_frames": "50",
    "stop_after_test": true,
    "test_frame_status": "completed",  // 测试帧状态

    // 硬件配置
    "ram": 64,
    "gpu_count": 2,
    "hardware_config": {
      "id": "high_performance",
      "name": "高性能配置"
    },

    // 进度统计
    "total_frames": 100,
    "completed_frames": 45,
    "failed_frames": 1,
    "rendering_frames": 5,

    // 成本
    "estimated_cost": 12.5,
    "actual_cost": 6.8,

    // 时间
    "created_at": "2025-11-04T10:30:00Z",
    "started_at": "2025-11-04T10:31:00Z",
    "completed_at": null,
    "estimated_completion": "2025-11-04T12:00:00Z"
  }
}
```

---

#### 暂停任务 (新增)

```
POST /api/tasks/{id}/pause
```

**响应**:

```json
{
  "code": 200,
  "message": "任务暂停成功",
  "data": {
    "id": 123,
    "status": "paused"
  }
}
```

---

#### 恢复任务 (新增)

```
POST /api/tasks/{id}/resume
```

**响应**:

```json
{
  "code": 200,
  "message": "任务恢复成功",
  "data": {
    "id": 123,
    "status": "rendering"
  }
}
```

---

#### 获取任务的资产列表 (新增)

```
GET /api/tasks/{id}/assets
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "task_id": 123,
    "assets": [
      {
        "asset_id": 456,
        "file_path": "C:/textures/wood.jpg",
        "file_hash": "6e57efc1...",
        "file_size": 1024000,
        "file_type": "texture",
        "local_path": "C:/textures/wood.jpg",
        "server_path": "/C/textures/wood.jpg",
        "is_missing": false
      }
    ],
    "total_count": 33,
    "missing_count": 0
  }
}
```

---

### 4.4 帧管理 (扩展)

#### 获取帧详情

```
GET /api/tasks/{task_id}/frames/{frame_number}
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "id": 1001,
    "task_id": 123,
    "frame_number": 50,
    "status": "completed",
    "is_test_frame": true,

    "output_path": "C:/workspace/user123/123/renders/frame.0050.exr",
    "output_size": 5242880,
    "output_hash": "abc123...",

    "node_id": "node_1",
    "render_time": 180,
    "retry_count": 0,

    "created_at": "2025-11-04T10:30:00Z",
    "started_at": "2025-11-04T10:31:00Z",
    "completed_at": "2025-11-04T10:34:00Z",

    "error_message": null
  }
}
```

---

### 4.5 硬件配置管理 (新增)

#### 获取所有硬件配置

```
GET /api/hardware-configs
```

**响应**:

```json
{
  "code": 200,
  "data": [
    {
      "id": "basic",
      "config_name": "基础配置",
      "ram": 16,
      "cpu_cores": 8,
      "gpu_count": 0,
      "gpu_model": null,
      "price_per_hour": 0.5,
      "is_available": true
    },
    {
      "id": "high_performance",
      "config_name": "高性能配置",
      "ram": 64,
      "cpu_cores": 24,
      "gpu_count": 2,
      "gpu_model": "RTX 4090",
      "price_per_hour": 2.5,
      "is_available": true
    }
  ]
}
```

---

#### 根据需求匹配硬件配置

```
POST /api/hardware-configs/match
```

**请求 Body**:

```json
{
  "ram": 64,
  "gpu_count": 2
}
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "recommended": {
      "id": "high_performance",
      "config_name": "高性能配置",
      "ram": 64,
      "gpu_count": 2,
      "price_per_hour": 2.5
    },
    "alternatives": [
      {
        "id": "ultra_high",
        "config_name": "超高性能配置",
        "ram": 128,
        "gpu_count": 4,
        "price_per_hour": 5.0
      }
    ]
  }
}
```

---

## 5. 错误处理

### 5.1 错误码定义

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| 1000 | 参数错误 | 400 |
| 1001 | 必填字段缺失 | 400 |
| 1002 | 字段格式错误 | 400 |
| 2000 | 资源不存在 | 404 |
| 2001 | 任务不存在 | 404 |
| 2002 | 文件不存在 | 404 |
| 3000 | 资源冲突 | 409 |
| 3001 | 任务已存在 | 409 |
| 4000 | 权限不足 | 403 |
| 4001 | 无权访问该任务 | 403 |
| 5000 | 服务器内部错误 | 500 |
| 5001 | 数据库错误 | 500 |
| 5002 | OSS 错误 | 500 |
| 5003 | 渲染引擎错误 | 500 |

### 5.2 错误响应示例

```json
{
  "code": 1002,
  "message": "字段格式错误",
  "detail": "test_frames 字段必须是数字或逗号分隔的数字列表",
  "errors": [
    {
      "field": "test_frames",
      "value": "abc",
      "expected": "数字或 '1,2,3' 格式"
    }
  ]
}
```

---

## 6. 请求校验

### 6.1 使用 Pydantic 模型

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class CreateTaskRequest(BaseModel):
    """创建任务请求"""

    unionid: str = Field(..., min_length=1, max_length=100)
    oss_file_path: str = Field(..., min_length=1)
    render_engine: str = Field(..., regex="^(maya|ue)$")
    total_frames: int = Field(1, ge=1, le=10000)
    priority: int = Field(5, ge=0, le=10)

    # 新增字段
    test_frames: Optional[str] = Field(None, max_length=100)
    stop_after_test: bool = False
    ram: Optional[int] = Field(None, ge=4, le=512)
    gpu_count: int = Field(0, ge=0, le=8)
    hardware_config_id: Optional[str] = None

    @validator("test_frames")
    def validate_test_frames(cls, v):
        if v is None:
            return v
        # 验证格式: "50" 或 "10,20,30"
        try:
            frames = [int(f.strip()) for f in v.split(",")]
            if any(f <= 0 for f in frames):
                raise ValueError("帧号必须大于 0")
            return v
        except ValueError:
            raise ValueError("test_frames 格式错误,应为数字或逗号分隔的数字")

class TaskResponse(BaseModel):
    """任务响应"""

    id: int
    unionid: str
    status: str
    progress: float
    test_frames: Optional[str]
    hardware_config_id: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True  # 支持从 ORM 模型转换
```

---

## 7. API 使用示例

### 7.1 完整工作流程

#### 步骤 1: 分析场景

```bash
curl -X POST http://localhost:8000/api/scene/analyse \
  -H "Content-Type: application/json" \
  -d '{
    "scene_file": "C:/Project/wolf.ma",
    "unionid": "user123"
  }'
```

**响应**: 获取场景信息和资产列表

---

#### 步骤 2: 检查文件是否已上传

```bash
curl -X POST http://localhost:8000/api/files/check-hashes \
  -H "Content-Type: application/json" \
  -d '{
    "hashes": ["6e57efc1...", "abc123..."]
  }'
```

**响应**: 获取需要上传的文件列表

---

#### 步骤 3: 上传缺失文件

```bash
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@C:/textures/wood.jpg" \
  -F "hash=6e57efc1..." \
  -F "file_type=texture" \
  -F "unionid=user123"
```

**响应**: 文件上传成功,获取 asset_id

---

#### 步骤 4: 创建渲染任务 (带测试帧)

```bash
curl -X POST http://localhost:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "unionid": "user123",
    "oss_file_path": "projects/user123/wolf.ma",
    "render_engine": "maya",
    "total_frames": 100,
    "test_frames": "50",
    "stop_after_test": true,
    "ram": 64,
    "gpu_count": 2,
    "hardware_config_id": "high_performance"
  }'
```

**响应**: 任务创建成功,获取 task_id

---

#### 步骤 5: 轮询任务状态

```bash
curl http://localhost:8000/api/tasks/123/status
```

**响应**: 获取任务进度

---

#### 步骤 6: 下载渲染结果

```bash
curl http://localhost:8000/api/files/download/1001
```

**响应**: 下载指定帧的渲染结果

---

## 8. API 版本兼容性

### 8.1 向后兼容策略

- ✅ 现有 API 保持不变
- ✅ 新增字段为可选 (Optional)
- ✅ 不删除已有字段
- ✅ 不修改已有字段的数据类型

### 8.2 废弃 API 处理

如果需要废弃某个 API:

1. **标记为 Deprecated** (响应头添加 `X-Deprecated: true`)
2. **保留 6 个月** (给用户迁移时间)
3. **提供替代方案** (文档说明新 API)
4. **最终移除** (发布新版本 v2)

---

## 9. 性能优化

### 9.1 分页

所有列表接口都支持分页:

```
GET /api/tasks?page=1&page_size=20
```

### 9.2 字段过滤

支持只返回需要的字段:

```
GET /api/tasks/123?fields=id,status,progress
```

**响应**:

```json
{
  "code": 200,
  "data": {
    "id": 123,
    "status": "rendering",
    "progress": 45.5
  }
}
```

### 9.3 批量操作

支持批量查询:

```
POST /api/tasks/batch-status
Body: {
  "task_ids": [123, 124, 125]
}
```

---

## 10. 安全性

### 10.1 认证 (未来实现)

使用 JWT 令牌:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 10.2 访问控制

- 用户只能访问自己的任务
- 管理员可以访问所有任务

### 10.3 速率限制 (未来实现)

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1730721600
```

---

## 11. 总结

### 11.1 API 清单

#### 现有 API (保持不变)

- ✅ `POST /api/tasks/` - 创建任务
- ✅ `GET /api/tasks/{id}/status` - 查询状态
- ✅ `POST /api/tasks/{id}/cancel` - 取消任务
- ✅ `POST /api/tasks/{id}/cleanup` - 清理工作空间
- ✅ `POST /api/tasks/{id}/frames/{frame_number}/retry` - 重试帧

#### 新增 API

- 🆕 `POST /api/scene/analyse` - 场景分析
- 🆕 `GET /api/scene/analyse/{scene_hash}` - 获取缓存分析
- 🆕 `POST /api/files/check-hashes` - 检查文件哈希
- 🆕 `POST /api/files/upload` - 上传文件 (带去重)
- 🆕 `GET /api/files/download-url/{asset_id}` - 获取下载链接
- 🆕 `GET /api/tasks/{id}` - 获取任务详情 (扩展版)
- 🆕 `POST /api/tasks/{id}/pause` - 暂停任务
- 🆕 `POST /api/tasks/{id}/resume` - 恢复任务
- 🆕 `GET /api/tasks/{id}/assets` - 获取任务资产
- 🆕 `GET /api/tasks/{task_id}/frames/{frame_number}` - 获取帧详情
- 🆕 `GET /api/hardware-configs` - 获取硬件配置
- 🆕 `POST /api/hardware-configs/match` - 匹配硬件配置

### 11.2 下一步

查看 [实现步骤.md](./实现步骤.md) 了解如何逐步实现这些 API
