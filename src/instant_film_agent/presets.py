"""プリセットおよびお気に入りの名前解決モジュール。"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .errors import EXIT_USAGE, AgentError

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
REPO_PRESETS_DIR = PACKAGE_DIR.parents[1] / "presets"
REPO_FAVORITES = PACKAGE_DIR.parents[1] / "favorites.json"

FAVORITE_WORDS = ("favorite", "お気に入り", "いつもの", "default")

# ビルトインプリセット（代表的なインスタントフィルム表現）
BUILTIN_PRESETS: Dict[str, Dict[str, Any]] = {
    "Instax Mini (Vertical Snap)": {
        "frame_format": "Portrait (Vertical)",
        "fit_mode": "Crop to Window",
        "film_tone": "Modern Clear (instax)",
        "emulation_strength": 65,
        "paper_tone": "Pure White",
        "paper_texture": 30,
        "handwriting_style": "Diary Pen (Casual Notes)",
        "ink_color": "Marker Black (Permanent)",
        "layout_mode": "Center Caption + Right Date",
        "description": "縦長チェキ実寸比率。現代チェキ風ハイキー人肌トーンと日常日記ペン。",
    },
    "Polaroid 600 (Square Classic)": {
        "frame_format": "Square (Polaroid)",
        "fit_mode": "Crop to Window",
        "film_tone": "Cool Cyan (90s Snap)",
        "emulation_strength": 70,
        "paper_tone": "Pure White",
        "paper_texture": 35,
        "handwriting_style": "Quick Memo (Rough)",
        "ink_color": "Marker Black (Permanent)",
        "layout_mode": "Center Caption + Right Date",
        "description": "ポラロイド600正方形比率。90年代特有の爽やかな青緑黒浮きと太字メモ。",
    },
    "Polaroid SX-70 (70s Warm Vintage)": {
        "frame_format": "Square (Polaroid)",
        "fit_mode": "Crop to Window",
        "film_tone": "Warm Amber (70s Vintage)",
        "emulation_strength": 80,
        "paper_tone": "Warm Ivory",
        "paper_texture": 40,
        "handwriting_style": "Fountain Pen (Elegant)",
        "ink_color": "Fountain Pen Navy (Dark)",
        "layout_mode": "Center Caption + Right Date",
        "description": "70年代SX-70正方形比率。琥珀色ハイライト・濃厚な暖色黒浮き・温白色用紙。",
    },
    "Instax WIDE (Landscape Panorama)": {
        "frame_format": "Landscape (Wide)",
        "fit_mode": "Crop to Window",
        "film_tone": "Cool Cyan (90s Snap)",
        "emulation_strength": 65,
        "paper_tone": "Pure White",
        "paper_texture": 30,
        "handwriting_style": "Fine Liner (Neat)",
        "ink_color": "Gel Ink Blue (Ballpoint)",
        "layout_mode": "Center Caption + Right Date",
        "description": "横長ワイド実寸比率（16:10）。パノラマ・集合写真向けワイドフレームと青インク。",
    },
    "Pastel Dream (Soft Kawaii)": {
        "frame_format": "Portrait (Vertical)",
        "fit_mode": "Crop to Window",
        "film_tone": "Pastel Muted (Soft Dream)",
        "emulation_strength": 60,
        "paper_tone": "Pure White",
        "paper_texture": 20,
        "handwriting_style": "Cute Round Pop (Kawaii)",
        "ink_color": "Silver Gel (Glitter)",
        "layout_mode": "Center Caption + Right Date",
        "description": "軟調・低彩度・ふんわり白浮き。現代アイドルチェキや丸文字・ラメペン。",
    },
    "Vivid Summer (Lomo Pop)": {
        "frame_format": "Square (Polaroid)",
        "fit_mode": "Crop to Window",
        "film_tone": "Vivid Pop (Summer Punch)",
        "emulation_strength": 75,
        "paper_tone": "Pure White",
        "paper_texture": 30,
        "handwriting_style": "Marker (Bold)",
        "ink_color": "Sign Pen Red (Correction)",
        "layout_mode": "Center Caption + Right Date",
        "description": "原色が弾ける高彩度・高コントラスト。夏のフェスやストリート感、赤サインペン。",
    },
    "Classic Monochrome (Silver Halide B&W)": {
        "frame_format": "Square (Polaroid)",
        "fit_mode": "Crop to Window",
        "film_tone": "Classic B&W (Monochrome)",
        "emulation_strength": 75,
        "paper_tone": "Warm Ivory",
        "paper_texture": 35,
        "handwriting_style": "Retro Brush (Vintage)",
        "ink_color": "Marker Black (Permanent)",
        "layout_mode": "Center Caption + Right Date",
        "description": "純銀塩モノクロ現像。温黒調階調と筆文字スタイル。",
    },
    "Cinematic Night (Moody Teal)": {
        "frame_format": "Landscape (Wide)",
        "fit_mode": "Crop to Window",
        "film_tone": "Cinematic Teal (Moody Film)",
        "emulation_strength": 80,
        "paper_tone": "Matte Black",
        "paper_texture": 30,
        "handwriting_style": "Fine Liner (Neat)",
        "ink_color": "White Paint (Correction Pen)",
        "layout_mode": "Center Caption + Right Date",
        "description": "ティール黒浮き・強周辺減光の夜景映画調。黒台紙フレームに白ポスカペン。",
    },
    "Aged Nostalgia (Antique Memory)": {
        "frame_format": "Square (Polaroid)",
        "fit_mode": "Crop to Window",
        "film_tone": "Warm Amber (70s Vintage)",
        "emulation_strength": 85,
        "paper_tone": "Aged Vintage",
        "paper_texture": 60,
        "handwriting_style": "Fountain Pen (Elegant)",
        "ink_color": "Fountain Pen Navy (Dark)",
        "layout_mode": "Center Caption + Right Date",
        "description": "経年劣化したヴィンテージ印画紙。色褪せトーンとアンティーク万年筆。",
    },
    "Auto Smart (Adaptive Instant)": {
        "frame_format": "Portrait (Vertical)",
        "fit_mode": "Auto Aspect",
        "film_tone": "Auto (Match Format)",
        "emulation_strength": 65,
        "paper_tone": "Auto (Match Format)",
        "paper_texture": 30,
        "handwriting_style": "Diary Pen (Casual Notes)",
        "ink_color": "Marker Black (Permanent)",
        "layout_mode": "Center Caption + Right Date",
        "description": "入力画像の比率に合わせてチェキ縦/ポラ正方形/ワイド横を自動判別し、連動トーンを適用。",
    },
    "Keep Aspect Clean (No Crop Frame)": {
        "frame_format": "Portrait (Vertical)",
        "fit_mode": "Keep Aspect",
        "film_tone": "Auto (Match Format)",
        "emulation_strength": 65,
        "paper_tone": "Auto (Match Format)",
        "paper_texture": 30,
        "handwriting_style": "Diary Pen (Casual Notes)",
        "ink_color": "Marker Black (Permanent)",
        "layout_mode": "Center Caption + Right Date",
        "description": "元画像の比率を100%維持（トリミングなし）し、最適な外枠カードを付与。",
    },
}


def slugify(text: str) -> str:
    """プリセット名を比較用のスラグ形式（小文字・ハイフン区切り）に変換する。"""
    s = text.strip().lower()
    s = re.sub(r"[\s_()]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def user_config_dir() -> Path:
    override = os.environ.get("INSTANT_FILM_AGENT_CONFIG_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "instant-film-agent"


def user_presets_dir() -> Path:
    return user_config_dir() / "presets"


def user_favorites_file() -> Path:
    return user_config_dir() / "favorites.json"


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise AgentError("invalid_json", EXIT_USAGE, f"JSON を読めません: {path}: {e}")
    if not isinstance(data, dict):
        raise AgentError("invalid_json", EXIT_USAGE, f"JSON の最上位はオブジェクトである必要があります: {path}")
    return data


@dataclass
class ResolvedPreset:
    name: str                       # 元のプリセット名（表示用）
    slug: str                       # スラグ化名（キー）
    config_dict: Dict[str, Any]     # InstantFrameConfig互換の辞書
    source: str                     # "builtin", "repo", "user", "file"
    file_path: Optional[Path] = None


def get_builtin_presets() -> Dict[str, Dict[str, Any]]:
    return dict(BUILTIN_PRESETS)


def list_all_presets() -> List[Tuple[str, str, Dict[str, Any], str, Optional[Path]]]:
    """
    全プリセット（組み込み + リポジトリ同梱 + ユーザー）の一覧を返す。
    返り値: (表示名, スラグ名, 設定辞書, 出典, ファイルパス)
    重複時は ユーザー > リポジトリ > 組み込み の順で上書き。
    """
    result_map: Dict[str, Tuple[str, str, Dict[str, Any], str, Optional[Path]]] = {}

    # 1. 組み込みプリセット
    for name, params in get_builtin_presets().items():
        s = slugify(name)
        result_map[s] = (name, s, params, "builtin", None)

    # 2. リポジトリ同梱 presets/
    if REPO_PRESETS_DIR.is_dir():
        for p in sorted(REPO_PRESETS_DIR.glob("*.json")):
            try:
                data = _read_json(p)
                s = slugify(p.stem)
                disp_name = data.get("name", p.stem)
                result_map[s] = (disp_name, s, data, "repo", p)
            except Exception:
                continue

    # 3. ユーザー独自 presets/
    up = user_presets_dir()
    if up.is_dir():
        for p in sorted(up.glob("*.json")):
            try:
                data = _read_json(p)
                s = slugify(p.stem)
                disp_name = data.get("name", p.stem)
                result_map[s] = (disp_name, s, data, "user", p)
            except Exception:
                continue

    return sorted(result_map.values(), key=lambda t: t[1])


def load_favorites() -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    """
    お気に入り設定をロードする。
    優先順位: ユーザー設定ファイル (~/.config/.../favorites.json) > リポジトリ同梱 favorites.json > 既定値
    戻り値: (favorite_preset_slug, aliases_dict, extra_options)
    """
    # 探索順: ユーザー設定 > パッケージ同梱 (data/favorites.json) > リポジトリ同梱。
    # pip インストール後はリポジトリ直下の favorites.json が存在しないため、
    # パッケージ内に同梱したコピーを必ず探索に入れる (無いと alias が全滅する)。
    fav_file = user_favorites_file()
    if not fav_file.is_file():
        for candidate in (DATA_DIR / "favorites.json", REPO_FAVORITES):
            if candidate.is_file():
                fav_file = candidate
                break

    default_fav = "instax-mini"
    aliases: Dict[str, str] = {}
    extra: Dict[str, Any] = {}

    if fav_file.is_file():
        try:
            data = _read_json(fav_file)
            default_fav = data.get("favorite", default_fav)
            raw_aliases = data.get("aliases", {})
            if isinstance(raw_aliases, dict):
                aliases = {str(k).strip().lower(): str(v).strip() for k, v in raw_aliases.items()}
            for k, v in data.items():
                if k not in ("favorite", "aliases"):
                    extra[k] = v
        except Exception:
            pass

    return default_fav, aliases, extra


def resolve_preset(preset_query: Optional[str]) -> ResolvedPreset:
    """
    ユーザーが指定した文字列（名前、スラグ、エイリアス、ファイルパス、'favorite' 等）からプリセットを解決する。
    指定が無いか 'favorite' の場合はお気に入りを解決する。
    """
    default_fav, aliases, _ = load_favorites()

    # 未指定または 'favorite' 系ワード
    if not preset_query or preset_query.strip().lower() in FAVORITE_WORDS:
        target = default_fav
    else:
        target = preset_query.strip()

    # 1. 直接の JSON ファイルパス指定
    p = Path(target)
    if p.is_file() and p.suffix.lower() == ".json":
        data = _read_json(p)
        disp_name = data.get("name", p.stem)
        return ResolvedPreset(
            name=disp_name,
            slug=slugify(p.stem),
            config_dict=data,
            source="file",
            file_path=p.resolve(),
        )

    # 2. エイリアス解決
    target_clean = target.lower()
    if target_clean in aliases:
        target = aliases[target_clean]

    # 3. 全プリセットから検索（完全一致、スラグ一致）
    all_presets = {s: (disp, cfg, src, path) for disp, s, cfg, src, path in list_all_presets()}

    target_slug = slugify(target)
    if target_slug in all_presets:
        disp, cfg, src, path = all_presets[target_slug]
        return ResolvedPreset(
            name=disp,
            slug=target_slug,
            config_dict=cfg,
            source=src,
            file_path=path,
        )

    # 4. 部分一致検索
    candidates = [s for s in all_presets if target_slug in s]
    if len(candidates) == 1:
        s = candidates[0]
        disp, cfg, src, path = all_presets[s]
        return ResolvedPreset(
            name=disp,
            slug=s,
            config_dict=cfg,
            source=src,
            file_path=path,
        )

    # 見つからない場合のエラー
    avail = sorted(all_presets.keys())
    raise AgentError(
        "preset_not_found",
        EXIT_USAGE,
        f"プリセット '{preset_query}' が見つかりません。",
        candidates=avail,
    )


def set_user_favorite(preset_name: str) -> None:
    """ユーザーのお気に入りプリセットを保存する。"""
    resolved = resolve_preset(preset_name)
    fav_file = user_favorites_file()
    fav_file.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if fav_file.is_file():
        try:
            data = _read_json(fav_file)
        except Exception:
            data = {}

    data["favorite"] = resolved.slug
    fav_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def create_preset(name: str, config: Dict[str, Any], overwrite: bool = False) -> Path:
    """新規プリセットをユーザー設定ディレクトリに作成する。"""
    slug = slugify(name)
    if not slug:
        raise AgentError("invalid_preset_name", EXIT_USAGE, f"無効なプリセット名です: '{name}'")

    up = user_presets_dir()
    up.mkdir(parents=True, exist_ok=True)
    target = up / f"{slug}.json"

    if target.is_file() and not overwrite:
        raise AgentError("preset_exists", EXIT_USAGE, f"プリセットファイルが既に存在します: {target}")

    save_data = dict(config)
    save_data["name"] = name
    target.write_text(json.dumps(save_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
