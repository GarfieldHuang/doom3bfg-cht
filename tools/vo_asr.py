"""用 Qwen3-ASR + ForcedAligner 把語音轉成英文稿與逐字時間。

在 ComfyUI venv 執行（見 README）：
  PYTHONPATH=D:\\comfyui\\pylibs_stub;D:\\comfyui\\pylibs_qwenasr ^
  D:\\comfyui\\.venv\\Scripts\\python.exe tools/vo_asr.py work/vo work/asr

每個 wav 產生一個同路徑 .json：{"text": ..., "words": [[word, start, end], ...], "duration": 秒}
已存在的 json 會跳過，可中斷後續跑。
"""
import io
import json
import sys
import wave
from pathlib import Path

import torch
from qwen_asr import Qwen3ASRModel

BATCH = 16


def duration(p):
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    files = sorted(src.rglob("*.wav"))
    todo = [f for f in files if not (dst / f.relative_to(src)).with_suffix(".json").exists()]
    if len(sys.argv) > 3 and sys.argv[3] == "reverse":  # 第二個行程從尾端往前做
        todo.reverse()
    print(f"共 {len(files)} 個，待處理 {len(todo)} 個", flush=True)
    if not todo:
        return
    model = Qwen3ASRModel.from_pretrained(
        "Qwen/Qwen3-ASR-1.7B",
        forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",
        forced_aligner_kwargs=dict(dtype=torch.bfloat16, device_map="cuda:0"),
        dtype=torch.bfloat16, device_map="cuda:0", max_inference_batch_size=BATCH,
    )
    for i in range(0, len(todo), BATCH):
        batch = [f for f in todo[i:i + BATCH]
                 if not (dst / f.relative_to(src)).with_suffix(".json").exists()]  # 另一個行程可能已做完
        if not batch:
            continue
        try:
            results = model.transcribe([str(f) for f in batch], language="English", return_time_stamps=True)
        except Exception as e:  # 單批失敗就逐一重試，避免一個壞檔卡住整批
            print(f"批次失敗，逐檔重試：{e}", flush=True)
            results = []
            for f in batch:
                try:
                    results += model.transcribe(str(f), language="English", return_time_stamps=True)
                except Exception as e2:
                    print(f"  失敗 {f}: {e2}", flush=True)
                    results.append(None)
        for f, r in zip(batch, results):
            out = (dst / f.relative_to(src)).with_suffix(".json")
            out.parent.mkdir(parents=True, exist_ok=True)
            data = {"text": "", "words": [], "duration": duration(f), "error": r is None}
            if r is not None:
                data["text"] = r.text
                if r.time_stamps is not None:
                    data["words"] = [[w.text, w.start_time, w.end_time] for w in r.time_stamps]
            with io.open(out, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False)
        print(f"{min(i + BATCH, len(todo))}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
