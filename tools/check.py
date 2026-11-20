"""檢查譯文：漏翻、多出的 key、變數／換行不一致、簡體字、未翻（中英相同）。

  python tools/check.py [english.lang 路徑]   # 預設 extracted/english.lang
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build import ROOT, parse_lang  # noqa: E402

TOKEN = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[sdifxXc]|\^\d|<DNT_VAL>|(?<![A-Za-z])_[a-z][a-z0-9_]+")
# 常見簡體字（對應繁體不同形）；出現就是寫錯
SIMPLIFIED = set("这们说时为会对发问题经过还进来个给让应该开关无从门间动现实体录频视讯设备网络软数据库储计确认删载线连统钟级层报错误")


def tokens(s):
    return sorted(TOKEN.findall(s))


def main():
    eng_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "extracted" / "english.lang"
    eng = parse_lang(eng_path.read_text(encoding="utf-8-sig"))
    problems = 0
    seen = {}
    for f in sorted((ROOT / "translations").glob("*.lang")):
        text = f.read_text(encoding="utf-8-sig")
        n_lines = sum(1 for line in text.splitlines() if line.lstrip().startswith('"'))
        tr = parse_lang(text)
        if n_lines != len(tr):
            print(f"[重複 key] {f.name}: {n_lines} 行只解析出 {len(tr)} 條")
            problems += 1
        for k, v in tr.items():
            where = f"{f.name} {k}"
            if k in seen:
                print(f"[重複] {where}（也在 {seen[k]}）")
                problems += 1
            seen[k] = f.name
            if k not in eng:
                print(f"[多出] {where}")
                problems += 1
                continue
            e = eng[k]
            if tokens(e) != tokens(v):
                print(f"[變數] {where}: 原 {tokens(e)} 譯 {tokens(v)}")
                problems += 1
            if e.count("\n") != v.count("\n"):
                print(f"[換行] {where}: 原 {e.count(chr(10))} 譯 {v.count(chr(10))}")
                problems += 1
            bad = SIMPLIFIED & set(v)
            if bad:
                print(f"[簡體] {where}: {''.join(sorted(bad))}")
                problems += 1
    todo = [k for k, v in eng.items() if k not in seen and re.search(r"[A-Za-z]{2,}", v)
            and not re.match(r"#str_dlg_(360|ps3)_|#font_", k)]
    print(f"\n已翻 {len(seen)} 條，未翻 {len(todo)} 條，問題 {problems} 個")
    if todo[:20]:
        print("未翻範例：", " ".join(todo[:20]))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
