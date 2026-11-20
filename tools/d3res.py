"""DOOM 3 BFG Edition .resources 容器工具（列出／解出）。

格式（見 neo/framework/File_Resource.cpp）：
  header : uint32 BE magic 0xD000000D, uint32 BE tableOffset, uint32 BE tableLength
  table  : uint32 BE numFiles，接著每筆
           int32 LE 檔名長度 + 檔名, uint32 BE offset, uint32 BE length

用法：
  python d3res.py list    <file.resources> [篩選字串]
  python d3res.py extract <file.resources> <輸出目錄> [篩選字串]
"""
import struct
import sys
from pathlib import Path

MAGIC = 0xD000000D


def read_table(path):
    with open(path, "rb") as f:
        magic, table_off, table_len = struct.unpack(">III", f.read(12))
        if magic != MAGIC:
            raise ValueError(f"{path}: 不是 .resources 檔（magic={magic:#x}）")
        f.seek(table_off)
        buf = f.read(table_len)
    (num,) = struct.unpack_from(">I", buf, 0)
    pos = 4
    entries = []
    for _ in range(num):
        (nlen,) = struct.unpack_from("<i", buf, pos)
        pos += 4
        name = buf[pos:pos + nlen].decode("latin-1")
        pos += nlen
        off, length = struct.unpack_from(">II", buf, pos)
        pos += 8
        entries.append((name, off, length))
    return entries


def main(argv):
    if len(argv) < 3 or argv[1] not in ("list", "extract"):
        print(__doc__)
        return 1
    cmd, res = argv[1], Path(argv[2])
    entries = read_table(res)
    if cmd == "list":
        flt = argv[3].lower() if len(argv) > 3 else ""
        for name, off, length in entries:
            if flt in name.lower():
                print(f"{length:>10}  {name}")
        return 0
    out = Path(argv[3])
    flt = argv[4].lower() if len(argv) > 4 else ""
    n = 0
    with open(res, "rb") as f:
        for name, off, length in entries:
            if flt not in name.lower():
                continue
            dst = (out / name).resolve()
            if out.resolve() not in dst.parents:
                raise ValueError(f"可疑路徑：{name}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            f.seek(off)
            dst.write_bytes(f.read(length))
            n += 1
    print(f"解出 {n} 個檔案到 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
