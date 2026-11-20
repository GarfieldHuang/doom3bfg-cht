"""把翻好的字幕（work/sub_zh_*.txt）轉成 translations/subtitles.lang。

輸入格式（每段語音一個標頭，底下每行一條字幕）：
  ### sound/vo/<路徑>
  <開始秒>|<結束秒>|<中文>
輸出 key：#sub_sound/vo/<路徑>，value：各條字幕以 \\n 串接（引擎 snd_subtitles.cpp 解析）。
會對照 work/sub_en_*.txt 檢查標頭、條數、時間是否一致。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build import ROOT, escape  # noqa: E402


def read(path):
    clips, cur = {}, None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        if line.startswith("### "):
            cur = line[4:].strip()
            clips[cur] = []
        else:
            s, e, t = line.split("|", 2)
            clips[cur].append((s, e, t.strip()))
    return clips


def main():
    work = ROOT / "work"
    problems, out = 0, {}
    for zh_path in sorted(work.glob("sub_zh_*.txt")):
        en = read(work / zh_path.name.replace("sub_zh_", "sub_en_"))
        zh = read(zh_path)
        if list(en) != list(zh):
            print(f"[標頭] {zh_path.name}: 段落清單和原文不同")
            problems += 1
        for k, cues in zh.items():
            ref = en.get(k, [])
            if [(s, e) for s, e, _ in cues] != [(s, e) for s, e, _ in ref]:
                print(f"[時間] {zh_path.name} {k}")
                problems += 1
            for s, e, t in cues:
                if re.search(r"[A-Za-z]{4,}", t) and not re.search(r"[一-鿿]", t):
                    print(f"[未翻] {k} {s}: {t}")
            out[k] = "\n".join(f"{float(s):g}|{float(e):g}|{t}" for s, e, t in cues)
    lines = ["// 對話字幕：由 tools/subs_to_lang.py 從 work/sub_zh_*.txt 產生", "{"]
    lines += [f'\t"#sub_{k}"\t"{escape(v)}"' for k, v in sorted(out.items())]
    lines.append("}")
    (ROOT / "translations" / "subtitles.lang").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(out)} 段語音字幕 → translations/subtitles.lang，問題 {problems} 個")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
