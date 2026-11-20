"""把 work/asr/**.json（Qwen3-ASR 文字＋逐字時間）切成字幕段。

輸出 work/cues_en.json：{"sound/vo/site3/01_trigger_sc1": [[start, end, "English text"], ...], ...}
切法：優先在句尾標點斷；一段超過 MAX_DUR 秒或 MAX_CHARS 字元就在逗號或字間斷；
兩段之間停頓超過 GAP 秒也斷。字幕顯示到下一段開始或本段結束後 HOLD 秒。
"""
import io
import json
import re
import sys
from pathlib import Path

MAX_DUR, MAX_CHARS, GAP, HOLD = 4.5, 70, 1.2, 0.6
# 只有語助詞／慘叫的語音不上字幕
GRUNT = re.compile(r"(?i)^(?:(?:a+h+|o+h+|u+g+h+|a+r+g+h+|h+m+|h+u+h+|u+h+|g+a+h+|n+o+|h+e+y+|ow+|aa+h*)[.!?,]*\s*)+$")


def strip(t):
    return re.sub(r"[^\w']", "", t).lower()


def attach_punct(text, words):
    """aligner 的字沒有標點，用原文的空白斷詞依序對回去，取回帶標點的字。"""
    toks = text.split()
    out, j = [], 0
    for w, s, e in words:
        key = strip(w)
        k = j
        while k < len(toks) and strip(toks[k]) != key and k < j + 3:
            k += 1
        if k < len(toks) and strip(toks[k]) == key:
            out.append([toks[k], s, e])
            j = k + 1
        else:
            out.append([w, s, e])
    return out


def segment(words, duration):
    cues, cur = [], []

    def flush():
        if cur:
            cues.append([cur[0][1], cur[-1][2], " ".join(w for w, _, _ in cur)])
            cur.clear()

    for i, (w, s, e) in enumerate(words):
        if cur and s - cur[-1][2] > GAP:
            flush()
        cur.append([w, s, e])
        text = " ".join(x for x, _, _ in cur)
        dur = e - cur[0][1]
        if re.search(r"[.!?]['\"]?$", w) and dur >= 0.8 and not re.fullmatch(r"(?i)(dr|mr|mrs|ms|sgt|lt|st|cpl|pvt|jr|vs)\.", w):
            flush()
        elif (dur > MAX_DUR or len(text) > MAX_CHARS) and re.search(r"[,;:]$", w):
            flush()
        elif dur > MAX_DUR + 1 or len(text) > MAX_CHARS + 25:
            # 硬斷：別把冠詞、介系詞留在行尾
            if re.fullmatch(r"(?i)(a|an|the|to|of|in|on|at|for|and|or|but|with|that|my|your|our)", w) and len(cur) > 1:
                last = cur.pop()
                flush()
                cur.append(last)
            else:
                flush()
    flush()
    # 顯示時間：延到下一段開始前，最多多留 HOLD 秒
    for i, c in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else duration
        c[1] = round(min(max(c[1] + HOLD, c[0] + 1.0), nxt if nxt > c[0] else c[1] + HOLD), 2)
        c[0] = round(c[0], 2)
    return cues


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "work/asr")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "work/cues_en.json")
    result, empty = {}, []
    for f in sorted(src.rglob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        key = f.relative_to(src).with_suffix("").as_posix()
        if not d["text"].strip() or not d["words"] or GRUNT.match(d["text"].strip()):
            empty.append(key)
            continue
        result[key] = segment(attach_punct(d["text"], d["words"]), d["duration"])
    with io.open(out, "w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=0)
    n = sum(len(v) for v in result.values())
    print(f"{len(result)} 段語音 → {n} 條字幕；無語音內容 {len(empty)} 段")
    if empty:
        Path(str(out).replace(".json", "_empty.txt")).write_text("\n".join(empty), encoding="utf-8")


if __name__ == "__main__":
    main()
