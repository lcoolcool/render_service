# Maya Render.exe 命令行参数详解

本文档详细列出了 Maya Render.exe（命令行批量渲染工具）的所有参数及使用说明。

## 基本用法

```bash
Render.exe [options] filename
```

其中 `filename` 是 Maya ASCII (.ma) 或 Maya Binary (.mb) 文件。

---

## 通用选项 (Common Options)

### 帮助和调试

| 参数 | 说明 |
|------|------|
| `-help` | 打印帮助信息 |
| `-test` | 打印 Mel 命令但不执行 |
| `-verb` | 在执行前打印 Mel 命令 |
| `-keepMel` | 保留临时 Mel 文件 |
| `-listRenderers` | 列出所有可用的渲染器 |

### 渲染器选择

| 参数 | 说明 | 示例 |
|------|------|------|
| `-renderer <string>` | 使用指定的渲染器 | `-renderer arnold` |
| `-r <string>` | 同 `-renderer` | `-r arnold` |

**可用渲染器**：
- `arnold` - Arnold 渲染器（推荐）
- `sw` - Maya 软件渲染器
- `hw` - Maya 硬件渲染器
- `hw2` - Maya 硬件渲染器 2
- `vr` - 矢量渲染器
- `default` / `file` - 使用文件中保存的渲染器
- `turtle` - Turtle 帧渲染器
- `turtlebake` - Turtle 表面传递渲染器

### 项目和日志

| 参数 | 说明 | 示例 |
|------|------|------|
| `-proj <string>` | 指定 Maya 项目路径 | `-proj C:/MyProject` |
| `-log <string>` | 将输出保存到指定文件 | `-log render.log` |

### Render Setup

| 参数 | 说明 |
|------|------|
| `-rendersetuptemplate <string>` | 应用 Render Setup 模板 |
| `-rst <string>` | 同 `-rendersetuptemplate` |
| `-rendersettingspreset <string>` | 导入场景渲染设置 |
| `-rsp <string>` | 同 `-rendersettingspreset` |
| `-rendersettingsaov <string>` | 从 JSON 文件导入 AOVs |
| `-rsa <string>` | 同 `-rendersettingsaov` |

### Python 版本

| 参数 | 说明 | 示例 |
|------|------|------|
| `-pythonver <int>` | 指定 Python 版本（2 或 3） | `-pythonver 3` |

---

## Arnold 渲染器专用选项

### 通用渲染标志

| 参数 | 说明 | 示例 |
|------|------|------|
| `-rd <path>` | 输出图像文件的目录 | `-rd C:/renders` |
| `-im <filename>` | 输出图像文件名 | `-im myImage` |
| `-rt <int>` | 渲染类型：0=渲染，1=导出ass，2=导出并kick | `-rt 0` |
| `-lic <boolean>` | 开启/关闭许可证检查 | `-lic on` |
| `-of <format>` | 输出图像格式（见渲染设置窗口） | `-of exr` |
| `-fnc <int>` | 文件命名规则（见渲染设置窗口） | `-fnc 1` |

### 帧序列选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `-s <float>` | 动画序列的起始帧 | `-s 1` |
| `-e <float>` | 动画序列的结束帧 | `-e 100` |
| `-seq <string>` | 帧号序列 | `-seq "2 4 6..10"` |
| `-b <float>` | 动画序列的帧步长 | `-b 1` |
| `-skipExistingFrames <boolean>` | 跳过已渲染的帧 | `-skipExistingFrames true` |
| `-pad <int>` | 输出文件帧号的数字位数 | `-pad 4` |

### 渲染层和通道

| 参数 | 说明 | 示例 |
|------|------|------|
| `-rl <boolean\|name(s)>` | 分别渲染每个渲染层 | `-rl true` |
| `-rp <boolean\|name(s)>` | 分别渲染通道，'all' 渲染所有通道 | `-rp all` |
| `-sel <boolean\|name(s)>` | 选择要渲染的物体、组或集合 | `-sel mySet` |
| `-l <boolean\|name(s)>` | 选择要渲染的显示和渲染层 | `-l layer1` |

### 相机选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `-cam <name>` | 指定要渲染的相机 | `-cam persp` |
| `-rgb <boolean>` | 开启/关闭 RGB 输出 | `-rgb true` |
| `-alpha <boolean>` | 开启/关闭 Alpha 输出 | `-alpha true` |
| `-depth <boolean>` | 开启/关闭深度输出 | `-depth false` |
| `-iip` | 忽略图像平面 | `-iip` |

### 分辨率选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `-x <int>` | 设置 X 轴分辨率 | `-x 1920` |
| `-y <int>` | 设置 Y 轴分辨率 | `-y 1080` |
| `-percentRes <float>` | 使用百分比分辨率渲染 | `-percentRes 50` |
| `-ard <float>` | 设备宽高比 | `-ard 1.777` |
| `-reg <int>` | 设置渲染区域 | `-reg 0 0 512 512` |

### 采样选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:as <int>` | 抗锯齿采样数 (Camera AA) | `-ai:as 4` |
| `-ai:hs <int>` | 间接漫反射采样数 | `-ai:hs 2` |
| `-ai:gs <int>` | 间接镜面反射采样数 | `-ai:gs 2` |
| `-ai:rs <int>` | 折射/透射采样数 | `-ai:rs 2` |
| `-ai:bssrdfs <int>` | SSS 采样数 | `-ai:bssrdfs 2` |

### 采样钳制 (Sample Clamping)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:cmpsv <boolean>` | 启用采样钳制 | `-ai:cmpsv true` |
| `-ai:aovsc <boolean>` | 采样钳制影响 AOVs | `-ai:aovsc true` |
| `-ai:aasc <float>` | 采样最大值 | `-ai:aasc 10.0` |
| `-ai:iasc <float>` | 间接光线采样最大值 | `-ai:iasc 5.0` |

### 深度选项 (Depth Options)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:td <int>` | 总深度 (Total Depth) | `-ai:td 10` |
| `-ai:dif <int>` | 间接漫反射深度 | `-ai:dif 2` |
| `-ai:glo <int>` | 间接镜面反射深度 | `-ai:glo 2` |
| `-ai:rfr <int>` | 折射深度 | `-ai:rfr 4` |
| `-ai:vol <int>` | 体积 GI 深度 | `-ai:vol 0` |
| `-ai:atd <int>` | 自动透明深度 | `-ai:atd 10` |

### 运动模糊 (Motion Blur)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:mben <boolean>` | 启用运动模糊 | `-ai:mben true` |
| `-ai:mbdf <boolean>` | 启用变形运动模糊 | `-ai:mbdf true` |
| `-ai:mbrt <int>` | 快门类型：0=居中，1=开始，2=结束，3=自定义 | `-ai:mbrt 0` |
| `-ai:mbfr <float>` | 快门长度 | `-ai:mbfr 0.5` |
| `-ai:mbstart <float>` | 运动开始时间 | `-ai:mbstart 0.0` |
| `-ai:mbend <float>` | 运动结束时间 | `-ai:mbend 1.0` |
| `-ai:mbms <int>` | 运动步数 | `-ai:mbms 2` |

### 灯光 (Lights)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:llth <float>` | 低光阈值 | `-ai:llth 0.001` |
| `-ai:ll <int>` | 灯光链接模式：0=无，1=Maya灯光链接 | `-ai:ll 1` |
| `-ai:sl <int>` | 阴影链接模式：0=无，1=跟随灯光，2=Maya阴影链接 | `-ai:sl 1` |

### 细分 (Subdivision)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:mxsb <int>` | 最大细分级别 | `-ai:mxsb 4` |

### 渲染设置

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:threads <int>` | 线程数（0=自动） | `-ai:threads 8` |
| `-ai:bscn <int>` | 桶扫描模式：0=顶部，1=底部，2=左，3=右，4=随机，5=编织，6=螺旋，7=希尔伯特 | `-ai:bscn 5` |
| `-ai:bsz <int>` | 桶大小（Bucket Size） | `-ai:bsz 64` |
| `-ai:bass <boolean>` | 二进制 ASS 导出 | `-ai:bass true` |
| `-ai:exbb <boolean>` | 导出边界框 | `-ai:exbb false` |
| `-ai:aerr <boolean>` | 错误时中止 | `-ai:aerr true` |
| `-ai:alf <boolean>` | 许可证失败时中止 | `-ai:alf true` |
| `-ai:slc <boolean>` | 跳过许可证检查 | `-ai:slc false` |
| `-ai:device <int>` | 渲染设备：0=CPU，1=GPU | `-ai:device 0` |
| `-ai:manGpuSel <boolean>` | 手动 GPU 选择开关 | `-ai:manGpuSel false` |
| `-ai:gpu <int>` | 用于渲染的 GPU 索引（配合 manGpuSel） | `-ai:gpu 0` |
| `-ai:enas <boolean>` | 启用自适应采样 | `-ai:enas true` |
| `-ai:maxaa <int>` | AA 采样最大值 | `-ai:maxaa 16` |
| `-ai:aath <float>` | AA 自适应阈值 | `-ai:aath 0.015` |
| `-ai:uopt <string>` | 用户选项 | `-ai:uopt "custom options"` |
| `-ai:port <int>` | 批量进度驱动的命令端口 | `-ai:port 7001` |
| `-ai:ofn <string>` | 原始文件名 | `-ai:ofn scene.ma` |

### 纹理设置

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:txamm <boolean>` | 启用纹理自动 mipmap | `-ai:txamm true` |
| `-ai:txaun <boolean>` | 接受未平铺纹理 | `-ai:txaun true` |
| `-ai:txett <boolean>` | 使用现有平铺纹理 | `-ai:txett true` |
| `-ai:txaum <boolean>` | 接受无 mipmap 纹理 | `-ai:txaum true` |
| `-ai:txat <int>` | 自动平铺大小 | `-ai:txat 64` |
| `-ai:txmm <float>` | 最大纹理缓存内存（MB） | `-ai:txmm 2048` |
| `-ai:txmof <int>` | 最大打开纹理数 | `-ai:txmof 500` |
| `-ai:txpfs <boolean>` | 每文件纹理统计 | `-ai:txpfs false` |

### 功能覆盖 (Feature Overrides)

用于调试或加速预览的选项：

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:foop <boolean>` | 忽略操作符 | `-ai:foop false` |
| `-ai:fotx <boolean>` | 忽略纹理 | `-ai:fotx false` |
| `-ai:fosh <boolean>` | 忽略着色器 | `-ai:fosh false` |
| `-ai:foat <boolean>` | 忽略大气效果 | `-ai:foat false` |
| `-ai:folt <boolean>` | 忽略灯光 | `-ai:folt false` |
| `-ai:fosw <boolean>` | 忽略阴影 | `-ai:fosw false` |
| `-ai:fosd <boolean>` | 忽略细分 | `-ai:fosd false` |
| `-ai:fodp <boolean>` | 忽略置换 | `-ai:fodp false` |
| `-ai:fobp <boolean>` | 忽略凹凸 | `-ai:fobp false` |
| `-ai:fosm <boolean>` | 忽略平滑 | `-ai:fosm false` |
| `-ai:fomb <boolean>` | 忽略运动模糊 | `-ai:fomb false` |
| `-ai:fosss <boolean>` | 忽略 SSS | `-ai:fosss false` |
| `-ai:fodof <boolean>` | 忽略景深 | `-ai:fodof false` |
| `-ai:foimg <boolean>` | 忽略成像器 | `-ai:foimg false` |

### 搜索路径 (Search Paths)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:sppg <string>` | 插件搜索路径 | `-ai:sppg "C:/plugins"` |
| `-ai:sppr <string>` | 程序化对象搜索路径 | `-ai:sppr "C:/procedurals"` |
| `-ai:spsh <string>` | 着色器搜索路径 | `-ai:spsh "C:/shaders"` |
| `-ai:sptx <string>` | 纹理搜索路径 | `-ai:sptx "C:/textures"` |

### 日志设置 (Logging)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-ai:lfn <string>` | 日志文件名 | `-ai:lfn render.log` |
| `-ai:ltc <boolean>` | 输出日志到控制台 | `-ai:ltc true` |
| `-ai:ltf <boolean>` | 输出日志到文件 | `-ai:ltf true` |
| `-ai:lve <int>` | 详细级别：0=错误，1=警告，2=信息，3=调试 | `-ai:lve 2` |
| `-ai:lmw <int>` | 最大警告数 | `-ai:lmw 100` |
| `-ai:mti <boolean>` | MtoA 转换信息 | `-ai:mti false` |
| `-ai:ste <boolean>` | 启用统计 | `-ai:ste true` |
| `-ai:stf <string>` | 统计文件名 | `-ai:stf stats.json` |
| `-ai:stm <int>` | 统计模式 | `-ai:stm 0` |
| `-ai:pfe <boolean>` | 启用性能分析 | `-ai:pfe false` |
| `-ai:pff <string>` | 性能分析文件名 | `-ai:pff profile.json` |

### MEL 回调 (Mel Callbacks)

| 参数 | 说明 | 示例 |
|------|------|------|
| `-preRender <string>` | 渲染前执行的 Mel 代码 | `-preRender "print(\"start\")"` |
| `-postRender <string>` | 渲染后执行的 Mel 代码 | `-postRender "print(\"done\")"` |
| `-preLayer <string>` | 每个渲染层前执行的 Mel 代码 | `-preLayer "..."` |
| `-postLayer <string>` | 每个渲染层后执行的 Mel 代码 | `-postLayer "..."` |
| `-preFrame <string>` | 每帧前执行的 Mel 代码 | `-preFrame "..."` |
| `-postFrame <string>` | 每帧后执行的 Mel 代码 | `-postFrame "..."` |
| `-insertPreRender <string>` | 插入渲染前执行的 Mel 代码 | `-insertPreRender "..."` |
| `-insertPostRender <string>` | 插入渲染后执行的 Mel 代码 | `-insertPostRender "..."` |
| `-insertPreLayer <string>` | 插入层前执行的 Mel 代码 | `-insertPreLayer "..."` |
| `-insertPostLayer <string>` | 插入层后执行的 Mel 代码 | `-insertPostLayer "..."` |
| `-insertPreFrame <string>` | 插入帧前执行的 Mel 代码 | `-insertPreFrame "..."` |
| `-insertPostFrame <string>` | 插入帧后执行的 Mel 代码 | `-insertPostFrame "..."` |

---

## 完整示例

### 基本渲染示例

```bash
# 使用 Arnold 渲染单帧
Render.exe -r arnold -s 1 -e 1 -rd "C:/output" "C:/scenes/myScene.ma"

# 渲染序列帧（1-100帧）
Render.exe -r arnold -s 1 -e 100 -b 1 -rd "C:/output" "C:/scenes/myScene.ma"

# 指定分辨率渲染
Render.exe -r arnold -x 1920 -y 1080 -s 1 -e 10 -rd "C:/output" "C:/scenes/myScene.ma"

# 指定相机渲染
Render.exe -r arnold -cam persp -s 1 -e 24 -rd "C:/output" "C:/scenes/myScene.ma"
```

### 高质量渲染示例

```bash
# 高质量渲染（增加采样）
Render.exe -r arnold \
  -ai:as 8 \
  -ai:hs 4 \
  -ai:gs 4 \
  -ai:rs 4 \
  -x 3840 -y 2160 \
  -s 1 -e 100 \
  -rd "C:/output" \
  "C:/scenes/myScene.ma"
```

### 快速预览示例

```bash
# 低质量快速预览
Render.exe -r arnold \
  -ai:as 1 \
  -ai:hs 0 \
  -ai:gs 0 \
  -percentRes 25 \
  -ai:fomb true \
  -s 1 -e 10 \
  -rd "C:/output" \
  "C:/scenes/myScene.ma"
```

### GPU 渲染示例

```bash
# 使用 GPU 渲染
Render.exe -r arnold \
  -ai:device 1 \
  -ai:manGpuSel true \
  -ai:gpu 0 \
  -s 1 -e 100 \
  -rd "C:/output" \
  "C:/scenes/myScene.ma"
```

### 多线程渲染示例

```bash
# 指定线程数
Render.exe -r arnold \
  -ai:threads 16 \
  -s 1 -e 100 \
  -rd "C:/output" \
  "C:/scenes/myScene.ma"
```

---

## 重要说明

1. **参数格式**：选项标志和参数值之间必须有空格
   - 正确：`-s 1`
   - 错误：`-s1`

2. **布尔值**：布尔标志接受以下值
   - TRUE: `on`, `yes`, `true`, `1`
   - FALSE: `off`, `no`, `false`, `0`

3. **路径格式**：
   - Windows: 使用双引号包含空格路径，如 `"C:/My Folder/scene.ma"`
   - 可以使用正斜杠 `/` 或反斜杠 `\`

4. **输出文件名**：
   - Maya 会根据场景设置自动生成文件名
   - 使用 `-im` 可以覆盖默认文件名
   - 使用 `-pad` 控制帧号位数（如 0001）

5. **渲染器差异**：不同渲染器支持的参数不同，使用 `-help -r <renderer>` 查看特定渲染器的参数

---

## 相关资源

- [Maya 官方文档](https://help.autodesk.com/view/MAYAUL/2022/ENU/)
- [Arnold 渲染器文档](https://docs.arnoldrenderer.com/)
- 项目中的实现：`app/services/renderer.py`

---

**最后更新**: 2025-11-03
**Maya 版本**: 2022
**适用于**: render_service 项目
