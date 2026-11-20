"""產生 DOOM 3 BFG 的 idFont（newfonts/<name>/48.dat + 48.tga）。

格式（見 neo/renderer/Font.cpp idFont::LoadFont）：
  uint32 BE  magic = 42 | 'i'<<24 | 'd'<<16 | 'f'<<8
  int16  BE  pointSize (=48)
  int16  BE  ascender
  int16  BE  descender
  int16  BE  numGlyphs（上限 32767）
  glyphInfo_t[numGlyphs]，每筆 10 bytes、little-endian：
      u8 width, u8 height, s8 top, s8 left, u8 xSkip, (pad), u16 s, u16 t
  uint32 LE  charIndex[numGlyphs]（Unicode 碼位，遞增排序）
貼圖：同名 .tga，白色 RGB＋alpha 為字形覆蓋率。

用法：
  python make_font.py --font NotoSansTC-VF.ttf --weight Bold \
      --chars charset.txt --out build/base/newfonts/chinese
"""
import argparse
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MAGIC = 42 | (ord("i") << 24) | (ord("d") << 16) | (ord("f") << 8)
PAD = 2


def load_font(path, size, weight):
    font = ImageFont.truetype(str(path), size)
    if weight:
        try:
            font.set_variation_by_name(weight)
        except (OSError, ValueError):
            pass  # 非可變字型就照原樣
    return font


def collect_chars(chars_file):
    chars = {chr(c) for c in range(32, 127)}
    if chars_file:
        text = Path(chars_file).read_text(encoding="utf-8-sig")
        chars |= {c for c in text if ord(c) >= 32}
    return sorted(chars, key=ord)


def render(font, chars, atlas_w):
    ascent, descent = font.getmetrics()
    glyphs = []
    for ch in chars:
        l, t, r, b = font.getbbox(ch, anchor="ls")
        adv = round(font.getlength(ch))
        if r <= l or b <= t:  # 空白類
            l, t, r, b = 0, 0, 0, 0
        glyphs.append(dict(ch=ch, l=l, t=t, w=r - l, h=b - t, adv=adv))

    # 逐列排進貼圖
    x = y = PAD
    row_h = 0
    for g in glyphs:
        if x + g["w"] + PAD > atlas_w:
            x = PAD
            y += row_h + PAD
            row_h = 0
        g["s"], g["t_px"] = x, y
        x += g["w"] + PAD
        row_h = max(row_h, g["h"])
    atlas_h = 1
    while atlas_h < y + row_h + PAD:
        atlas_h *= 2

    alpha = Image.new("L", (atlas_w, atlas_h), 0)
    for g in glyphs:
        if g["w"] == 0:
            continue
        mask = Image.new("L", (g["w"], g["h"]), 0)
        ImageDraw.Draw(mask).text((-g["l"], -g["t"]), g["ch"], font=font, fill=255, anchor="ls")
        alpha.paste(mask, (g["s"], g["t_px"]))
    img = Image.merge("RGBA", (Image.new("L", alpha.size, 255),) * 3 + (alpha,))
    return glyphs, img, ascent, descent


def write_dat(path, glyphs, ascent, descent):
    out = bytearray(struct.pack(">IhhhH", MAGIC, 48, ascent, -descent, len(glyphs)))
    for g in glyphs:
        for k, lim in (("w", 255), ("h", 255), ("adv", 255)):
            if not 0 <= g[k] <= lim:
                raise ValueError(f"{g['ch']!r} 的 {k}={g[k]} 超出 byte 範圍")
        out += struct.pack("<BBbbBxHH", g["w"], g["h"], -g["t"], g["l"], g["adv"], g["s"], g["t_px"])
    out += struct.pack(f"<{len(glyphs)}I", *(ord(g["ch"]) for g in glyphs))
    path.write_bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--weight", default="Bold")
    ap.add_argument("--size", type=int, default=48, help="渲染像素大小（48pt 格的字身）")
    ap.add_argument("--chars", help="要收錄的字（UTF-8 文字檔，通常是譯文本身）")
    ap.add_argument("--atlas-width", type=int, default=4096)
    ap.add_argument("--out", required=True, help="輸出資料夾，例如 build/base/newfonts/chinese")
    a = ap.parse_args()

    font = load_font(a.font, a.size, a.weight)
    chars = collect_chars(a.chars)
    if len(chars) > 32767:
        raise SystemExit("字數超過 idFont 上限 32767")
    glyphs, img, ascent, descent = render(font, chars, a.atlas_width)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write_dat(out / "48.dat", glyphs, ascent, descent)
    img.save(out / "48.tga")  # PIL 存未壓縮 32-bit TGA
    print(f"{len(glyphs)} 字，貼圖 {img.size[0]}x{img.size[1]}，ascent={ascent} descent={descent}")


if __name__ == "__main__":
    main()
