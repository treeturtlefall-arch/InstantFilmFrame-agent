#!/usr/bin/env python3
"""本家 InstantFilmFrame と同梱エンジンの差分を表示・マニフェスト更新を行う同期ツール。

使い方:
  python scripts/sync_upstream.py [本家 InstantFilmFrame のパス]
  python scripts/sync_upstream.py --update-manifest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# パッケージ内の engine_file_sha256 を利用
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from instant_film_agent.engine import ENGINE_DIR, FONTS_DIR, engine_file_sha256

MANIFEST_PATH = ROOT_DIR / "src" / "instant_film_agent" / "data" / "engine_hashes.json"
ENGINE_FILES = ["instant_frame.py", "instant_config.py"]


def update_manifest() -> int:
    """同梱エンジンおよびフォントの SHA-256 ハッシュマニフェストを再生成する。"""
    manifest = {}
    for name in ENGINE_FILES:
        fp = ENGINE_DIR / name
        if fp.is_file():
            manifest[name] = engine_file_sha256(fp)

    for fp in sorted(FONTS_DIR.glob("*")):
        if fp.is_file():
            rel = f"fonts/{fp.name}"
            manifest[rel] = engine_file_sha256(fp)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    MANIFEST_PATH.write_text(content, encoding="utf-8", newline="\n")
    print(f"マニフェストを更新しました: {MANIFEST_PATH} ({len(manifest)} 件)")
    return 0


def check_upstream(upstream_path: Path) -> int:
    changed = 0
    for name in ENGINE_FILES:
        src, dst = upstream_path / name, ENGINE_DIR / name
        if not src.is_file():
            print(f"[missing] 本家に {name} がありません")
            changed += 1
            continue
        same = dst.is_file() and engine_file_sha256(src) == engine_file_sha256(dst)
        print(f"[{'same' if same else 'DIFF'}] {name}")
        changed += 0 if same else 1

    src_fonts, dst_fonts = upstream_path / "fonts", FONTS_DIR
    s_names = {p.name for p in src_fonts.glob("*") if p.is_file()} if src_fonts.is_dir() else set()
    d_names = {p.name for p in dst_fonts.glob("*") if p.is_file()} if dst_fonts.is_dir() else set()

    font_diffs = 0
    all_font_names = sorted(s_names | d_names)
    for fn in all_font_names:
        sf, df = src_fonts / fn, dst_fonts / fn
        if not sf.is_file() or not df.is_file():
            font_diffs += 1
        elif engine_file_sha256(sf) != engine_file_sha256(df):
            font_diffs += 1

    fonts_same = (font_diffs == 0 and s_names == d_names)
    print(f"[{'same' if fonts_same else 'DIFF'}] fonts/ (本家 {len(s_names)} 件 / 同梱 {len(d_names)} 件 / 差分 {font_diffs} 件)")
    changed += 0 if fonts_same else 1

    print("差分あり。取り込みは UPSTREAM.md の手順で行ってください。" if changed else "同梱エンジンは本家と完全に一致しています。")
    return 0 if changed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="本家 InstantFilmFrame との同期・差分検証ツール")
    parser.add_argument("upstream", nargs="?", help="本家 InstantFilmFrame のディレクトリパス")
    parser.add_argument("--update-manifest", action="store_true", help="同梱エンジンの SHA-256 マニフェストを再生成する")

    args = parser.parse_args(argv)

    if args.update_manifest:
        return update_manifest()

    if not args.upstream:
        parser.print_help()
        return 2

    upstream_path = Path(args.upstream).expanduser().resolve()
    if not upstream_path.is_dir():
        print(f"本家パスが見つかりません: {upstream_path}", file=sys.stderr)
        return 2

    return check_upstream(upstream_path)


if __name__ == "__main__":
    raise SystemExit(main())
