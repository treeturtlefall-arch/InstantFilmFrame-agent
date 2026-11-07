#!/usr/bin/env python3
"""本家 InstantFilmFrame と同梱エンジンの差分を表示する同期チェックツール。

使い方: python scripts/sync_upstream.py <本家 InstantFilmFrame のパス>
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ENGINE_FILES = ["instant_frame.py", "instant_config.py"]


def sha256(path: Path) -> str:
    # engine_file_sha256 と同じ改行正規化 (CRLF/LF を同一視する)。
    if not path.is_file():
        return ""
    data = path.read_bytes()
    if path.suffix.lower() in {".py", ".txt", ".md", ".json"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    upstream = Path(sys.argv[1]).expanduser()
    engine = Path(__file__).resolve().parents[1] / "src" / "instant_film_agent" / "engine"
    if not upstream.is_dir():
        print(f"本家パスが見つかりません: {upstream}")
        return 2

    changed = 0
    for name in ENGINE_FILES:
        src, dst = upstream / name, engine / name
        if not src.is_file():
            print(f"[missing] 本家に {name} がありません")
            changed += 1
            continue
        same = dst.is_file() and sha256(src) == sha256(dst)
        print(f"[{'same' if same else 'DIFF'}] {name}")
        changed += 0 if same else 1

    src_fonts, dst_fonts = upstream / "fonts", engine / "fonts"
    s = {p.name for p in src_fonts.glob("*")} if src_fonts.is_dir() else set()
    d = {p.name for p in dst_fonts.glob("*")} if dst_fonts.is_dir() else set()
    fonts_same = (s == d)
    print(f"[{'same' if fonts_same else 'DIFF'}] fonts/ (本家 {len(s)} 件 / 同梱 {len(d)} 件)")
    changed += 0 if fonts_same else 1

    print("差分あり。取り込みは UPSTREAM.md の手順で行ってください。" if changed else "同梱エンジンは本家と完全に一致しています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
