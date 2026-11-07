"""InstantFilmFrame 描画エンジン（ピン留め同梱）ローダ。

同梱ファイルは本家同様にトップレベル import（`from instant_config import ...`）
前提のため、このフォルダを sys.path に入れてから import する。
同梱ファイル自体は改変しない（UPSTREAM.md 参照）。
"""
from __future__ import annotations

import functools
import hashlib
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
FONTS_DIR = ENGINE_DIR / "fonts"


def ensure_path() -> Path:
    """エンジンのフォルダを sys.path へ（重複挿入はしない）。"""
    p = str(ENGINE_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)
    return ENGINE_DIR


@functools.lru_cache(maxsize=1)
def load():
    """(instant_config, instant_frame) を返す。"""
    ensure_path()
    import instant_config
    import instant_frame

    return instant_config, instant_frame


def engine_file_sha256(path: Path) -> str:
    """エンジン同梱ファイルの SHA-256 を計算する。
    テキストファイル (.py) の場合は CRLF/LF の差分を排除して正規化する。
    """
    if not path.is_file():
        return "missing"
    data = path.read_bytes()
    if path.suffix == ".py":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()
