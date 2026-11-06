# 可维护的 Three.js 查看器源码

这是 `web/` 中静态预览的可读源码版本，使用 Vite + Three.js 0.180.0。模型和参考图不重复提交到此目录，而是由脚本从仓库相应目录复制到 Vite 的 `public/`。

## 本地运行

在完整 ZIP 根目录中确认模型与参考图存在，然后：

```bash
cd viewer-source
npm install
npm run dev
```

构建静态站点：

```bash
npm run build
```

构建结果在 `viewer-source/dist/`。`predev` 与 `prebuild` 会自动执行资产复制。

## 源码结构

- `src/main.js`：模型加载、材质精调、取景、骨骼显示、线框、动画和下载交互。
- `index.html`：中文界面、响应式布局和控制栏。
- `scripts/copy-assets.mjs`：从仓库模型、参考图目录复制运行资产。
- `vite.config.js`：相对路径构建配置。

## 验证接口

页面加载完成后暴露：

- `window.__SCENE_READY__`
- `window.__MODEL_STATS__`
- `window.__RENDER_STATS__`

添加 `?capture=1` 可从启动时关闭连续渲染，加载、交互或尺寸改变后显式重绘，适合自动化截图。正常访问不添加此参数。

远程 GitHub 仓库只保存文本源码。运行所需 GLB 和参考图请从完整 ZIP 获取。
