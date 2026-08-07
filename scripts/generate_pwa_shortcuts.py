#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.10"
# dependencies = ["fonttools"]
# ///
"""
生成 PWA shortcut 图标（96×96 PNG）。

从 @mdi/font 的 ttf 提取侧边栏 7 个图标对应的字形 path，渲染成
「透明底 + 黑色图标 #000」的 SVG，
再用 sharp（frontend/node_modules）转成 96×96 PNG，落到
frontend/public/shortcuts/，供 vite.config.ts manifest.shortcuts 引用。

配色与图标名与侧边栏 AppLayout.vue 的 prepend-icon 对齐，改图标改这里。

用法（项目根）：uv run scripts/generate_pwa_shortcuts.py
"""
import re
import subprocess
import tempfile
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

# ---- 配置 ----
ROOT = Path(__file__).resolve().parent.parent
MDI_DIR = ROOT / "frontend" / "node_modules" / "@mdi" / "font"
CSS = MDI_DIR / "css" / "materialdesignicons.css"
TTF = MDI_DIR / "fonts" / "materialdesignicons-webfont.ttf"
FRONTEND = ROOT / "frontend"
OUT_DIR = FRONTEND / "public" / "shortcuts"

# shortcut 顺序、文件名、MDI 图标名（与 AppLayout.vue prepend-icon 对齐）
SHORTCUTS = [
    ("today", "silverware-fork-knife"),       # 今日推荐
    ("prices", "currency-cny"),               # 价格记录
    ("recipes", "book-open-variant"),         # 菜谱管理
    ("products", "package-variant"),          # 商品管理
    ("ingredients", "leaf"),                  # 原料管理
    ("merchants", "store"),                   # 商家管理
    ("profile", "account"),                   # 个人中心
]

BG_COLOR = "none"     # 透明底
FG_COLOR = "#000000"   # 黑色图标
SIZE = 512             # SVG viewBox 边长 = 字体 unitsPerEm，path 坐标直接用字体单位


def load_codepoints() -> dict:
    """解析 mdi css，建 {图标名(无 mdi- 前缀): codepoint} 映射。"""
    text = CSS.read_text(encoding="utf-8")
    pat = re.compile(r'\.mdi-([a-z0-9-]+)::before\s*\{\s*content:\s*"\\([0-9A-Fa-f]+)"', re.M)
    return {name: int(cp, 16) for name, cp in pat.findall(text)}


def glyph_to_svg(font, glyph_set, gname: str) -> str:
    """提字形 path，统一缩放 + 几何居中，生成 SIZE×SIZE 透明底黑图标 SVG。

    所有图标按最大边缩放到画布 65%，保证透明底下一致的视觉大小；
    按各自 bounding box 几何中心居中（字体坐标 y-up → SVG y-down 翻 y）。
    """
    pen = SVGPathPen(glyph_set)
    glyph_set[gname].draw(pen)
    d = pen.getCommands()

    g = font["glyf"][gname]
    x_min, y_min, x_max, y_max = g.xMin, g.yMin, g.xMax, g.yMax

    glyph_w = x_max - x_min
    glyph_h = y_max - y_min
    target = SIZE * 0.65
    scale = target / max(glyph_w, glyph_h)

    # 几何中心（字体坐标）
    cx = (x_max + x_min) / 2
    cy = (y_max + y_min) / 2

    # translate 把缩放后的几何中心落到 SVG 中心 (SIZE/2, SIZE/2)
    # scale(s, -s)：x' = s*x + tx,  y' = -s*y + ty
    # 令 x'=SIZE/2 → tx = SIZE/2 - s*cx
    # 令 y'=SIZE/2 → ty = SIZE/2 + s*cy
    tx = SIZE / 2 - scale * cx
    ty = SIZE / 2 + scale * cy

    bg_rect = f'  <rect width="{SIZE}" height="{SIZE}" fill="{BG_COLOR}"/>\n' if BG_COLOR != "none" else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SIZE} {SIZE}" width="{SIZE}" height="{SIZE}">\n'
        f'{bg_rect}'
        f'  <path transform="translate({tx:.2f},{ty:.2f}) scale({scale:.2f},{-scale:.2f})" '
        f'd="{d}" fill="{FG_COLOR}"/>\n'
        f'</svg>\n'
    )


# sharp 读 SVG 批量转 96×96 PNG（ESM top-level await）
NODE_CONV = r"""
import sharp from 'sharp'
import { readdir, readFile, writeFile } from 'fs/promises'
import { join } from 'path'
const [tmpDir, outDir] = [process.argv[1], process.argv[2]]
for (const f of await readdir(tmpDir)) {
  if (!f.endsWith('.svg')) continue
  const buf = await readFile(join(tmpDir, f))
  const png = await sharp(buf, { density: 600 }).resize(96, 96).png().toBuffer()
  await writeFile(join(outDir, f.replace(/\.svg$/, '.png')), png)
  console.log('  ', f, '->', f.replace(/\.svg$/, '.png'))
}
"""


def main() -> None:
    if not TTF.exists():
        raise SystemExit(f"找不到 MDI 字体：{TTF}（确认 @mdi/font 已安装）")

    codepoints = load_codepoints()
    font = TTFont(TTF)
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pwa_sc_") as tmp:
        tmp_dir = Path(tmp)
        missing = []
        for key, icon in SHORTCUTS:
            cp = codepoints.get(icon)
            if cp is None or cp not in cmap:
                missing.append(icon)
                continue
            gname = cmap[cp]
            svg = glyph_to_svg(font, glyph_set, gname)
            (tmp_dir / f"{key}.svg").write_text(svg, encoding="utf-8")
        if missing:
            raise SystemExit(f"css/cmap 缺图标：{missing}")

        print(f"已生成 {len(SHORTCUTS)} 个 SVG，调 sharp 转 PNG → {OUT_DIR}")
        subprocess.run(
            ["node", "--input-type=module", "-e", NODE_CONV, str(tmp_dir), str(OUT_DIR)],
            cwd=str(FRONTEND),
            check=True,
        )

    print(f"\n完成。{OUT_DIR.relative_to(ROOT)} 下 7 个 96×96 PNG 可用。")


if __name__ == "__main__":
    main()
