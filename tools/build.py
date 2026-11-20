"""組出繁中化檔案並（選擇性）安裝到遊戲。

  python tools/build.py                       # 只建到 build/
  python tools/build.py --install "<遊戲目錄>"  # 建好後複製到 <遊戲目錄>/base
  python tools/build.py --uninstall "<遊戲目錄>"

做的事：
  1. 合併 translations/*.lang（格式同遊戲 .lang，一行一筆 "key" "value"）
  2. 用譯文用到的字產生字型 newfonts/chinese/48.dat + 48.tga
  3. 輸出 base/strings/english_zcht.lang（UTF-8 BOM）
     遊戲會把所有 strings/english*.lang 依檔名排序載入、後載覆蓋先載，
     所以這個檔排在 english.lang 後面，蓋掉英文；再用 "#font_*" 把所有字型導向中文字型。
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "base"
FONT_NAME = "chinese"
LANG_NAME = "english_zcht.lang"
DEFAULT_FONT = Path("C:/Windows/Fonts/NotoSansTC-VF.ttf")


def unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            i += 1
            c = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(s[i], s[i])
        out.append(c)
        i += 1
    return "".join(out)


def escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def parse_lang(text):
    """跟引擎 idLangDict::Load 同樣的規則：一行一筆，key 不含跳脫，value 到最後一個引號為止。"""
    entries = {}
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith('"'):
            continue
        k_end = s.index('"', 1)
        key = s[1:k_end]
        rest = s[k_end + 1:]
        v_start = rest.index('"') + 1
        v_end = rest.rindex('"')
        entries[key] = unescape(rest[v_start:v_end])
    return entries


def load_translations():
    merged = {}
    for f in sorted((ROOT / "translations").glob("*.lang")):
        for k, v in parse_lang(f.read_text(encoding="utf-8-sig")).items():
            if v.strip():
                merged[k] = v
    return merged


def build(font_path):
    tr = load_translations()
    tr["#font_*"] = FONT_NAME
    # english.lang 把舊 GUI 字型導向 Arial_Narrow 等；那些字型可能在語言檔載入前就被登記
    # （RBDOOM 會），快取裡沒有中文 → 顯示成 *。直接指到中文字型。
    for k in ("#font_", "#font_an", "#font_arial", "#font_bank", "#font_micro"):
        tr[k] = FONT_NAME
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (BUILD / "strings").mkdir(parents=True)

    charset = ROOT / "build" / "charset.txt"
    charset.write_text("".join(sorted({c for v in tr.values() for c in v})), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_font.py"), "--font", str(font_path),
                    "--chars", str(charset), "--out", str(BUILD / "newfonts" / FONT_NAME)], check=True)

    lines = ["// DOOM 3 BFG 繁體中文化 — 由 tools/build.py 產生，請改 translations/", "{"]
    lines += [f'\t"{k}"\t"{escape(v)}"' for k, v in sorted(tr.items())]
    lines.append("}")
    (BUILD / "strings" / LANG_NAME).write_bytes(b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8"))
    print(f"{len(tr) - 1} 條譯文 → {BUILD / 'strings' / LANG_NAME}")


def installed_files():
    return [p.relative_to(BUILD) for p in BUILD.rglob("*") if p.is_file()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", type=Path, default=DEFAULT_FONT)
    ap.add_argument("--install", type=Path, metavar="GAME_DIR")
    ap.add_argument("--uninstall", type=Path, metavar="GAME_DIR")
    ap.add_argument("--keep-intro", action="store_true", help="安裝時不跳過開頭動畫")
    a = ap.parse_args()

    if a.uninstall:
        base = a.uninstall / "base"
        for rel in [Path("strings") / LANG_NAME, Path("newfonts") / FONT_NAME]:
            p = base / rel
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
        gen = base / "generated" / "images" / "newfonts" / FONT_NAME
        if gen.exists():
            shutil.rmtree(gen)  # 引擎從 tga 轉出的快取
        set_autoexec(base, False)
        print("已移除繁中化檔案")
        return

    build(a.font)
    if a.install:
        base = a.install / "base"
        if not base.is_dir():
            raise SystemExit(f"找不到 {base}，--install 要指向遊戲根目錄")
        gen = base / "generated" / "images" / "newfonts" / FONT_NAME
        if gen.exists():
            shutil.rmtree(gen)  # 字型重建後舊快取要清掉
        for rel in installed_files():
            dst = base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BUILD / rel, dst)
        if not a.keep_intro:
            set_autoexec(base, True)
        print(f"已安裝到 {base}")


SKIP_INTRO_LINE = 'set com_skipIntroVideos "1" // doom3bfg-cht: skip intro video'


def set_autoexec(base, enable):
    """在 base/autoexec.cfg 加上／移除跳過開頭動畫的設定，不動使用者自己寫的其他行。
    引擎在讀完 autoexec.cfg 之後才檢查 com_skipIntroVideos（Common.cpp）。"""
    cfg = base / "autoexec.cfg"
    lines = cfg.read_text(encoding="utf-8").splitlines() if cfg.exists() else []
    lines = [ln for ln in lines if "com_skipIntroVideos" not in ln]
    if enable:
        lines.append(SKIP_INTRO_LINE)
    if lines:
        cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif cfg.exists():
        cfg.unlink()


if __name__ == "__main__":
    main()
