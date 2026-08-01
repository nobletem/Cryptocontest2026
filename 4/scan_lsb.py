import json
import re
import struct
from pathlib import Path

import numpy as np
from safetensors import safe_open


MODEL_PATH = Path("TinyLlama-1.1B-Chat-v1.0/model.safetensors")
OUT_PATH = Path("Scanned Result.txt")
PREVIEW_BYTES = 256
SAMPLE_BYTES = 4096
KEYWORDS = [b"flag", b"crypto", b"secret", b"square", b"key"]


def read_header(path: Path):
    with path.open("rb") as f:
        header_len = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(header_len))
    return header_len, header


def to_nibble_hi_lo_bytes(tensor) -> bytes:
    arr = tensor.detach().cpu().contiguous().numpy()
    raw = arr.view({2: np.uint16, 4: np.uint32, 8: np.uint64}[arr.dtype.itemsize]).reshape(-1)
    nibbles = (raw & 0xF).astype(np.uint8, copy=False)
    paired = nibbles[: (len(nibbles) // 2) * 2].reshape(-1, 2)
    return ((paired[:, 0] << 4) | paired[:, 1]).astype(np.uint8, copy=False).tobytes()


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    good = sum(1 for b in data if b in (9, 10, 13) or 32 <= b <= 126)
    return good / len(data)


def clean_preview(data: bytes) -> str:
    text = data[:PREVIEW_BYTES].decode("utf-8", "replace")
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    return text


def printable_runs(data: bytes, min_len: int = 24) -> list[str]:
    runs = re.findall(rb"[\x09\x0a\x0d\x20-\x7e]{" + str(min_len).encode() + rb",}", data)
    return [
        r[:160].decode("utf-8", "replace").replace("\r", "\\r").replace("\n", "\\n")
        for r in runs[:3]
    ]


def main():
    header_len, header = read_header(MODEL_PATH)
    entries = {k: v for k, v in header.items() if k != "__metadata__"}

    lines = []
    lines.append(f"model: {MODEL_PATH}")
    lines.append("method: raw tensor value -> uint integer view -> low 4 bits -> combine two nibbles as high-low byte")
    lines.append(f"header_bytes: {header_len}")
    lines.append(f"tensor_count: {len(entries)}")
    lines.append("")

    with safe_open(str(MODEL_PATH), framework="pt", device="cpu") as f:
        for idx, name in enumerate(f.keys(), start=1):
            tensor = f.get_tensor(name)
            data = to_nibble_hi_lo_bytes(tensor)
            sample = data[:SAMPLE_BYTES]
            lower = sample.lower()
            hits = [k.decode() for k in KEYWORDS if k in lower]
            nul = data.find(b"\x00")
            printable_until_nul = data[:nul] if nul != -1 else sample

            lines.append(f"[{idx:03d}] {name}")
            lines.append(f"  dtype: {tensor.dtype}")
            lines.append(f"  shape: {tuple(tensor.shape)}")
            lines.append(f"  safetensors_data_offsets: {entries[name]['data_offsets']}")
            lines.append(f"  recovered_bytes_from_low4: {len(data)}")
            lines.append(f"  printable_ratio_first_{SAMPLE_BYTES}: {printable_ratio(sample):.3f}")
            lines.append(f"  keyword_hits_first_{SAMPLE_BYTES}: {hits}")
            lines.append(f"  preview_first_{PREVIEW_BYTES}: {clean_preview(data)}")

            runs = printable_runs(sample)
            if runs:
                lines.append("  printable_runs:")
                for run in runs:
                    lines.append(f"    - {run}")

            if name == "model.embed_tokens.weight":
                end = nul if nul != -1 else min(len(data), 1000)
                lines.append("  extracted_until_null:")
                lines.append(printable_until_nul[:end].decode("utf-8", "replace").replace("\r", "\\r").replace("\n", "\\n"))

            lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
