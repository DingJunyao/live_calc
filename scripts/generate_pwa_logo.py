#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 PWA logo SVG（路径化 / 转曲）。

用思源黑体 SC Bold 把「生计」二字字形提取为 SVG <path>，
横排居中于 1024×1024 橄榄绿背景画布。转曲后 SVG 不依赖字体，
字体文件仅本脚本运行时使用，不入仓库（scripts/.fonts/ 已 gitignore）。

使用：
  1. 下载思源黑体 SC Bold OTF：
     https://github.com/adobe-fonts/source-han-sans/releases
     选 SourceHanSansSC.zip，解压取 SourceHanSansSC-Bold.otf
  2. 放到 scripts/.fonts/SourceHanSansSC-Bold.otf
  3. 在项目根用 .venv 运行：python scripts/generate_pwa_logo.py
  4. 产出 frontend/public/logo.svg（放 public/：assets-generator 产物与源同目录，图标需在 public/ 才能被 manifest 根路径引用）
"""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

# ---- 配置 ----
FONT_PATH = Path(__file__).parent / ".fonts" / "SourceHanSansSC-Bold.otf"
TEXT = "生计"
OUT_SVG = Path(__file__).parent.parent / "frontend" / "public" / "logo.svg"

VIEWBOX = 1024            # 画布尺寸
BG_COLOR = "#558B2F"      # 橄榄绿 primary（对齐 vuetify.ts lightTheme）
FG_COLOR = "#FDFCF8"      # 温暖米白
FONT_SIZE = 560           # 字号；两字横排约占画布宽 55%，四周留白兼容 maskable 安全区


def main() -> None:
    if not FONT_PATH.exists():
        raise SystemExit(
            f"字体不存在：{FONT_PATH}\n"
            "请从 https://github.com/adobe-fonts/source-han-sans/releases "
            "下载思源黑体 SC Bold OTF 放到该路径（目录已 gitignore）。"
        )

    font = TTFont(FONT_PATH)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    units_per_em = font["head"].unitsPerEm
    scale = FONT_SIZE / units_per_em

    # 取每个字的 glyph 名 + 水平 advance，计算总宽与起始 x（水平居中）
    glyphs = []
    for ch in TEXT:
        if ord(ch) not in cmap:
            raise SystemExit(f"字体缺少字符：{ch}")
        gname = cmap[ord(ch)]
        adv = font["hmtx"][gname][0]
        glyphs.append((gname, adv))

    total_width = sum(adv for _, adv in glyphs) * scale
    x_cursor = (VIEWBOX - total_width) / 2
    baseline = VIEWBOX * 0.78  # 字底基线 y（目视居中略偏下）

    paths = []
    for gname, adv in glyphs:
        pen = SVGPathPen(glyph_set)
        glyph_set[gname].draw(pen)
        d = pen.getCommands()
        # 字体坐标 y 向上 → SVG y 向下：translate 到字位 + scale(s,-s) 翻转
        paths.append(
            f'    <path transform="translate({x_cursor:.2f},{baseline:.2f}) '
            f'scale({scale:.6f},-{scale:.6f})" d="{d}"/>'
        )
        x_cursor += adv * scale

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VIEWBOX} {VIEWBOX}" width="{VIEWBOX}" height="{VIEWBOX}">\n'
        f'  <rect width="{VIEWBOX}" height="{VIEWBOX}" fill="{BG_COLOR}"/>\n'
        f'  <g fill="{FG_COLOR}">\n'
        f'{chr(10).join(paths)}\n'
        f'  </g>\n'
        f'</svg>\n'
    )

    OUT_SVG.parent.mkdir(parents=True, exist_ok=True)
    OUT_SVG.write_text(svg, encoding="utf-8")
    print(f"已生成 {OUT_SVG}（路径化，{len(TEXT)} 字，无字体引用）")


if __name__ == "__main__":
    main()
