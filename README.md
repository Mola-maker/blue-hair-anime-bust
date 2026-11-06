# 蓝发动漫少女 · 服装配色精修骨骼胸像

基于用户提供的动漫参考图制作的可编辑三维胸像工程。保留蓝发、粉色挑染、眼唇与发丝精修，在最新一轮仅参考新图的**冷白蓝服装、深蓝斜肩带与配色**；未增加全身、耳机或吉他。

## 交付内容

- 可编辑 Blender 高精度工程，内部另藏独立轻量骨骼版本。
- 高精度、轻量 GLB，均含 PBR 材质、18 根骨骼、完整蒙皮和 `Idle_Head_Hair` 动画。
- Three.js 静态交互查看器：视角切换、自动旋转、线框、骨骼、动作测试、模型下载。
- 面部精修、服装精修、GLB 后处理、工程合并与验证脚本。
- 两张用户参考图、渲染预览、验证报告和资产 SHA-256 清单。

## 模型规格

| 版本 | 三角面 | 骨骼 | 动画 | 动画通道 | 蒙皮 |
|---|---:|---:|---:|---:|---|
| 高精度 GLB | 1,956,361 | 18 | 1 | 54 | 全部 19 个 primitive |
| 轻量 GLB | 365,303 | 18 | 1 | 54 | 全部 19 个 primitive |

肩带顶点仅从 `Cloth_Cotton` 白衣顶点继承权重，避免邻近头发或皮肤造成拉扯。眼唇细节固定 `head` 权重，发丝从头发顶点继承权重。GLB 白衣 `baseColorFactor` 为 `[0.94, 0.975, 1.0, 1.0]`。

## 目录

```text
models/                 Blender 与 GLB 成品（完整 ZIP）
references/             用户提供的两张参考图（完整 ZIP）
previews/               整体、服装、眼部、唇肤渲染（完整 ZIP）
scripts/
  refine_clothing.py        冷白蓝材质、贴面肩带、蒙皮与导出
  finalize_glb.py           写入可移植的 GLB 白衣颜色因子
  assemble_clothing_verify.py 合并轻量工程并验证权重和动画
  validate_glb.py           检查 GLB 骨骼、动画、蒙皮和材质
  clothing_diagnostic.py    胸肩诊断相机
  face_details/             上一轮面部精修与诊断源码
web/                    完整静态 Three.js 查看器
viewer-source/          可读、可构建的 Vite + Three.js 查看器源码
asset-manifest.json      二进制资产大小与 SHA-256
docs/                   复现、资产与验证说明
```

## 打开与运行

### Blender

推荐使用 Blender 5.2.1 LTS。直接打开：

```text
models/蓝发动漫少女·服装配色精修.blend
```

高精度主体位于主场景；轻量版本位于默认隐藏的 `Preview_Lightweight_Hidden` 集合。骨骼对象为 `Rig_Bust_Hair`，动画为 `Idle_Head_Hair`。

### 网页查看器

```bash
cd web
python3 -m http.server 8080
```

访问 `http://localhost:8080`。查看器是纯前端静态页面，不需要 npm、后端或账号；模型文件直接从本地静态目录读取。

## 源码与二进制资产范围

公开 GitHub 仓库收录文本源码、脚本和文档。完整 ZIP 额外收录 `.blend`、`.glb`、参考图、预览图及网页模型。高精度 Blender 工程超过 GitHub 单文件 100 MiB 限制，且当前仓库写入通道只适合文本文件，因此**不能把 ZIP 中的模型视为已经推送到远程仓库**。`asset-manifest.json` 用于核对完整 ZIP 中资产的大小和 SHA-256。

网页提供两种形态：`web/` 是无需构建、已实测的静态部署包；`viewer-source/` 是可读、可修改的 Vite + Three.js 源码工程。静态包由 Three.js r180、GLTFLoader、OrbitControls 与查看器逻辑打包而成；可读源码独立实现同样的模型加载、材质、骨骼、动画与全部按钮交互，并已完成生产构建和浏览器实测。远程文本仓库收录可读源码，压缩部署包随完整 ZIP 提供。

## 复现与验证

见 [`docs/PIPELINE.md`](docs/PIPELINE.md) 与 [`docs/VALIDATION.md`](docs/VALIDATION.md)。参考图与模型权利说明见 [`CREDITS.md`](CREDITS.md)。
