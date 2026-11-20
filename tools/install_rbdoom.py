"""建立有對話字幕的 RBDOOM-3-BFG 遊戲資料夾（不動 Steam 原版）。

  python tools/install_rbdoom.py <Steam 遊戲目錄> <RBDOOM 原始碼目錄> <目標資料夾>

1. 把 Steam 版 base/ 底下的檔案「硬連結」到 <目標>/base/（同一顆磁碟不佔空間；
   不同磁碟會改成複製）
2. 複製 RBDOOM 編好的 RBDoom3BFG.exe 與 RBDOOM 自帶的 base 資料（materials、renderprogs2 …）
3. 呼叫 build.py --install 裝上繁中語言檔、字型、字幕
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_RB = {"_tb"}  # RBDOOM base 裡給地圖編輯器用的，不需要


def link_or_copy(src, dst):
    if dst.exists():
        return "skip"
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
        return "link"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def main():
    steam, rb, target = (Path(p) for p in sys.argv[1:4])
    if not (steam / "base" / "_common.resources").exists():
        raise SystemExit(f"{steam} 不是 DOOM 3 BFG 遊戲目錄")
    exe = rb / "build" / "Release" / "RBDoom3BFG.exe"
    if not exe.exists():
        raise SystemExit(f"找不到 {exe}，先編譯 RBDOOM")
    target.mkdir(parents=True, exist_ok=True)

    stats = {"link": 0, "copy": 0, "skip": 0}
    for src in (steam / "base").rglob("*"):
        if src.is_file():
            stats[link_or_copy(src, target / "base" / src.relative_to(steam / "base"))] += 1
    print(f"Steam 遊戲資料：硬連結 {stats['link']}、複製 {stats['copy']}、已存在 {stats['skip']}")

    shutil.copy2(exe, target / exe.name)
    n = 0
    for src in (rb / "base").rglob("*"):
        rel = src.relative_to(rb / "base")
        if not src.is_file() or rel.parts[0] in SKIP_RB or src.suffix == ".bat":
            continue
        dst = target / "base" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_nlink > 1:
            dst.unlink()  # 別透過硬連結改到 Steam 原檔
        shutil.copy2(src, dst)
        n += 1
    print(f"RBDOOM：exe ＋ {n} 個 base 檔案")

    subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "--install", str(target)], check=True)
    print(f"完成：執行 {target / exe.name}")


if __name__ == "__main__":
    main()
