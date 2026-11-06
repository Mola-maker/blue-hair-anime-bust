import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../..');
const publicDir = resolve(here, '../public');
mkdirSync(publicDir, { recursive: true });

const assets = [
  ['models/蓝发动漫少女·服装配色精修轻量版.glb', 'model.glb'],
  ['models/蓝发动漫少女·服装配色精修版.glb', 'model-hires.glb'],
  ['references/服装配色参考.jpeg', 'reference.jpg'],
];

for (const [source, target] of assets) {
  const input = resolve(root, source);
  if (!existsSync(input)) {
    throw new Error(`缺少运行资产：${source}\n请使用完整 ZIP，或按 docs/ASSETS.md 补齐文件。`);
  }
  copyFileSync(input, resolve(publicDir, target));
  console.log(`copied ${source} -> public/${target}`);
}
