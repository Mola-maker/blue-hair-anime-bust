# 处理与复现顺序

## 环境

- Blender 5.2.1 LTS（提供 `bpy` 与 NumPy）。
- Python 3.12 用于 GLB 后处理和结构校验。
- 不需要 Draco 或 MeshOptimizer；当前交付使用未压缩 GLB。

以下命令中的 `blender` 代表 Blender 的无界面 Python 启动方式。在本轮制作环境中对应 `/usr/local/bin/3dpy`。

## 1. 面部精修源码

`scripts/face_details/` 保存上一轮实际使用的源码，包括：

- `polish_features.py`：睫毛、眼神光、唇部、发丝与 PBR 材质。
- `assemble_verify.py`：合并轻量工程并检查动画跟随。
- `check_details.py`、`inspect_features.py`、`probe_features.py`：几何与权重诊断。
- `face_closeup.py`、`mouth_closeup.py`：局部渲染相机。
- `test_head_weights.py`、`test_parent.py`：眼唇权重修复验证。

这些是制作历史源码，保留了当时的工作目录常量。它们依赖面部精修前的中间检查点；当前完整 ZIP 交付的是该流程之后的成品，而不是全部历史中间文件。修改这些历史脚本时，请先调整其输入输出路径。

## 2. 服装与配色精修

对高精度、轻量面部精修检查点分别执行。输入必须包含对应主体名称、`Rig_Bust_Hair` 和 `Cloth_Cotton`。

```bash
blender --background --python scripts/refine_clothing.py -- high \
  --input /path/to/面部精修.blend \
  --output-blend models/蓝发动漫少女·服装配色精修.blend \
  --output-glb models/蓝发动漫少女·服装配色精修版.glb

blender --background --python scripts/refine_clothing.py -- low \
  --input /path/to/面部精修轻量版.blend \
  --output-blend models/蓝发动漫少女·服装配色精修轻量版.blend \
  --output-glb models/蓝发动漫少女·服装配色精修轻量版.glb
```

脚本会：

1. 只调整 `Cloth_Cotton` 的冷白蓝调色、粗糙度和 sheen。
2. 通过胸肩相机射线寻找白衣曲面，忽略前景发丝对视线路径的打断。
3. 沿路径生成横向六等分的贴面 ribbon 与细边线。
4. 通过白衣 BVH 将肩带顶点贴合曲面。
5. 仅从白衣顶点继承骨骼权重。
6. 以 `ACTIVE_ACTIONS` 模式导出单段动画，避免隐藏轻量骨骼的动作被重复导出。
7. 高精度模式渲染服装特写和整体预览。

不要在已经含有 `Detail_Clothing_Straps` 的成品上重复执行本脚本；它会再次添加肩带。应从未精修服装的面部检查点开始。

## 3. GLB 材质后处理

Blender 中保留 `Reference_Cool_White` MixRGB 节点，但 glTF 不会自动烘焙该节点，因此写入等价的材质乘法因子：

```bash
python3 scripts/finalize_glb.py \
  models/蓝发动漫少女·服装配色精修版.glb \
  models/蓝发动漫少女·服装配色精修轻量版.glb
```

## 4. 合并轻量工程并验证

```bash
blender --background --python scripts/assemble_clothing_verify.py
```

脚本默认读取 `models/` 中的两个 Blender 成品，将轻量骨骼版本放入高精度工程的隐藏集合，并验证：

- 两个版本均为 18 根骨骼。
- 眼唇、发丝和肩带权重和。
- 第 1、31、61 帧的细节位移。
- 验证报告写入 `docs/clothing_validation.json`。

该步骤会原位保存高精度 Blender 文件。

## 5. GLB 结构验证

```bash
python3 scripts/validate_glb.py \
  models/蓝发动漫少女·服装配色精修版.glb \
  models/蓝发动漫少女·服装配色精修轻量版.glb
```

脚本对骨骼数、动画数、动画通道、全部 primitive 的蒙皮属性和白衣颜色因子执行断言。

## 6. 网页资源与可读源码

静态网页默认读取 `web/model.glb` 和 `web/model-hires.glb`。更新模型后，将对应 GLB 复制到这两个路径；`web/reference.jpg` 是服装配色参考图。静态网页不需要构建。

可读源码位于 `viewer-source/`：

```bash
cd viewer-source
npm install
npm run dev
npm run build
```

`predev` 和 `prebuild` 会自动从 `models/`、`references/` 复制所需二进制资产到 `viewer-source/public/`。生产文件输出到 `viewer-source/dist/`。`src/main.js` 包含模型加载、分材质 PBR 调整、取景、灯光、骨骼显示、动画、全部按钮和移动端适配逻辑。

`?capture=1` 会从页面启动时关闭连续渲染，并在模型加载、视角变化或按钮操作后显式渲染，便于自动截图与测试。
