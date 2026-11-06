# 静态 Three.js 查看器

完整 ZIP 可直接运行：

```bash
cd web
python3 -m http.server 8080
```

远程文本仓库只包含 `index.html` 与说明；压缩运行包、`model.glb`、`model-hires.glb`、`reference.jpg` 随完整 ZIP 提供。

`assets/index-zzr03k2J.js` 是包含 Three.js r180、GLTFLoader、OrbitControls 和查看器逻辑的静态部署包，不是早期未压缩的原始 `scene.js`。它无需构建，包含页面实际运行的全部代码。

如需阅读、修改或重新构建，请使用根目录 `viewer-source/` 中的可读源码工程。
