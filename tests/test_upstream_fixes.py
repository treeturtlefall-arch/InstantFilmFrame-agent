"""上流バグ修正の回帰テスト (2026-11-08 実地検証で見つけた5件)。

1. doctor の engine_integrity が .txt の CRLF/LF 差で落ちる
2. pip インストール後に favorites.json (alias) が読めない
3. ドキュメント記載名 polaroid-sx70 / sx70 が解決できない
4. favorites.json の "date": "photo" が既定日付に反映されない
5. (パッケージング) data/favorites.json が同梱されていること自体をここで担保する
"""
import hashlib
import json
from pathlib import Path

import pytest

from instant_film_agent import presets
from instant_film_agent.engine import ENGINE_DIR, engine_file_sha256
from instant_film_agent.presets import load_favorites, resolve_preset
from instant_film_agent.runner import apply


@pytest.fixture(autouse=True)
def isolated_user_config(tmp_path, monkeypatch):
    """実ユーザーの ~/.config/instant-film-agent をテストに持ち込まない。"""
    monkeypatch.setenv("INSTANT_FILM_AGENT_CONFIG_DIR", str(tmp_path / "config"))
    return tmp_path


def test_engine_hash_normalizes_crlf_for_txt(tmp_path):
    lf = tmp_path / "note_lf.txt"
    crlf = tmp_path / "note_crlf.txt"
    lf.write_bytes(b"line1\nline2\n")
    crlf.write_bytes(b"line1\r\nline2\r\n")
    expected = hashlib.sha256(b"line1\nline2\n").hexdigest()
    assert engine_file_sha256(lf) == expected
    assert engine_file_sha256(crlf) == expected


def test_engine_manifest_matches_normalized_hashes():
    manifest = json.loads(
        (Path(ENGINE_DIR).parent / "data" / "engine_hashes.json").read_text(encoding="utf-8")
    )
    assert manifest, "engine_hashes.json が空です"
    for rel_path, expected in manifest.items():
        assert engine_file_sha256(ENGINE_DIR / rel_path) == expected, rel_path


def test_packaged_favorites_serve_aliases_without_repo_file(isolated_user_config, monkeypatch):
    """パッケージ同梱の data/favorites.json から alias が読めることを確認する。"""
    monkeypatch.setattr(presets, "REPO_FAVORITES", isolated_user_config / "no_such_favorites.json")
    _, aliases, extra = load_favorites()
    assert aliases, "パッケージ同梱の favorites.json から alias が読めていません"
    assert extra.get("date") == "photo"

    assert resolve_preset("cheki").slug == "instax-mini-vertical-snap"
    assert resolve_preset("チェキ").slug == "instax-mini-vertical-snap"
    assert resolve_preset("polaroid").slug == "polaroid-600-square-classic"
    assert resolve_preset("ポラロイド").slug == "polaroid-600-square-classic"


def test_sx70_documented_names_resolve():
    for query in ("sx70", "sx-70", "polaroid-sx70", "polaroid-sx-70"):
        assert resolve_preset(query).slug == "polaroid-sx-70-70s-warm-vintage", query


def test_vintage_alias_is_not_silently_sx70():
    assert resolve_preset("vintage").slug == "aged-nostalgia-antique-memory"


def test_default_apply_uses_favorites_date_photo(exif_test_image: Path, tmp_path: Path):
    if not exif_test_image.is_file():
        pytest.skip("EXIF テスト画像がありません")
    out = tmp_path / "default_date.jpg"
    res = apply(exif_test_image, output_path=out)
    assert res["ok"] is True
    assert res["date_source"].startswith("photo_")
    assert res["date_resolved"] == "'03 10 02"


def test_explicit_preset_keeps_preset_default_date(exif_test_image: Path, tmp_path: Path):
    """favorites の date は「お気に入り呼び出し」だけの既定。明示プリセットは従来どおり。"""
    if not exif_test_image.is_file():
        pytest.skip("EXIF テスト画像がありません")
    out = tmp_path / "explicit_preset_date.jpg"
    res = apply(exif_test_image, output_path=out, preset="polaroid-600")
    assert res["ok"] is True
    assert res["date_source"] == "preset_default"
