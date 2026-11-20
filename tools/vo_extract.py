"""把 BFG 的 .idwav（generated/sound/**）轉回標準 .wav。

idwav 格式（見 neo/sound/XAudio2/XA2_SoundSample.cpp LoadGeneratedSample）：
  u32 BE magic, i64 BE timestamp, u8 loaded, i32 BE playBegin, i32 BE playLength
  WAVEFORMAT（little-endian，PCM 16 bytes；ADPCM 再加 u16 extraSize + extraSize bytes）
  i32 BE amplitude 數量 + 該數量 bytes
  i32 BE totalBufferSize, i32 BE 區塊數，每塊：i32 BE numSamples, i32 BE bufferSize, 資料
輸出：fmt chunk 原樣搬，data 為所有區塊串接；MS ADPCM 可直接給 ffmpeg 解。

用法：
  python vo_extract.py <xxx.resources> <輸出資料夾> [路徑篩選，預設 generated/sound/vo/]
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from d3res import read_table  # noqa: E402

FORMAT_PCM, FORMAT_ADPCM = 1, 2


def idwav_to_wav(data):
    pos = 4 + 8 + 1
    play_begin, play_length = struct.unpack_from(">ii", data, pos)
    pos += 8
    tag, ch, rate, avg, block, bits = struct.unpack_from("<HHIIHH", data, pos)
    fmt = data[pos:pos + 16]
    pos += 16
    if tag != FORMAT_PCM:
        (extra,) = struct.unpack_from("<H", data, pos)
        fmt = data[pos - 16:pos + 2 + extra]
        pos += 2 + extra
    (namp,) = struct.unpack_from(">i", data, pos)
    pos += 4 + namp
    total, nbuf = struct.unpack_from(">ii", data, pos)
    pos += 8
    chunks = []
    for _ in range(nbuf):
        _ns, size = struct.unpack_from(">ii", data, pos)
        pos += 8
        chunks.append(data[pos:pos + size])
        pos += size
    pcm = b"".join(chunks)
    riff = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if len(fmt) % 2:
        riff += b"\0"
    if tag != FORMAT_PCM:  # 壓縮格式要有 fact chunk（總樣本數）
        riff += b"fact" + struct.pack("<II", 4, play_length)
    riff += b"data" + struct.pack("<I", len(pcm)) + pcm
    return b"RIFF" + struct.pack("<I", len(riff)) + riff, dict(tag=tag, rate=rate, ch=ch, samples=play_length)


def main(argv):
    res, out = Path(argv[1]), Path(argv[2])
    flt = argv[3] if len(argv) > 3 else "generated/sound/vo/"
    n = 0
    with open(res, "rb") as f:
        for name, off, length in read_table(res):
            if not name.startswith(flt) or not name.endswith(".idwav"):
                continue
            f.seek(off)
            wav, info = idwav_to_wav(f.read(length))
            rel = Path(name[len("generated/"):]).with_suffix(".wav")  # sound/vo/...
            dst = (out / rel).resolve()
            if out.resolve() not in dst.parents:
                raise ValueError(f"可疑路徑：{name}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(wav)
            n += 1
    print(f"轉出 {n} 個 wav 到 {out}")


if __name__ == "__main__":
    main(sys.argv)
