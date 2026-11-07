"""InstantFilmFrame 能力カタログモジュール。"""
from __future__ import annotations

from typing import Any, Dict
from .engine import load as load_engine
from .presets import list_all_presets, load_favorites, resolve_preset


def build_capabilities() -> Dict[str, Any]:
    instant_config, _ = load_engine()
    fav_slug, aliases, _ = load_favorites()

    try:
        resolved = resolve_preset("favorite")
        current_fav = {
            "name": resolved.name,
            "slug": resolved.slug,
            "config": resolved.config_dict,
        }
    except Exception as e:
        current_fav = {"favorite": fav_slug, "error": str(e)}

    preset_items = []
    for disp_name, s, cfg, src, _ in list_all_presets():
        preset_items.append({
            "name": disp_name,
            "slug": s,
            "source": src,
            "format": cfg.get("frame_format"),
            "fit_mode": cfg.get("fit_mode"),
            "tone": cfg.get("film_tone"),
            "emulation": cfg.get("emulation_strength"),
            "paper": cfg.get("paper_tone"),
            "handwriting": cfg.get("handwriting_style"),
            "ink": cfg.get("ink_color"),
            "description": cfg.get("description", ""),
        })

    return {
        "ok": True,
        "summary": "実在するインスタント写真（ポラロイド・チェキ等）の物理フレーム質感、0〜100の光学・化学現像エミュレーション、および余白への手書き文字・日時記入を合成する",
        "axes": {
            "frame_format": {
                "label": "構図規格（実寸比率エミュレート）",
                "choices": list(instant_config.FRAME_FORMATS),
                "details": {
                    "Portrait (Vertical)": "FUJIFILM instax mini (チェキ) 縦長実寸。窓46×62mm (約3:4) / 外枠54×86mm",
                    "Square (Polaroid)": "Polaroid 600 / SX-70 正方形実寸。窓79×79mm (1:1) / 外枠88.5×107.5mm",
                    "Landscape (Wide)": "FUJIFILM instax WIDE 横長実寸。窓99×62mm (約16:10) / 外枠108×86mm",
                },
            },
            "fit_mode": {
                "label": "アスペクト適合方式",
                "choices": list(instant_config.FIT_MODES),
                "details": {
                    "Crop to Window": "実在規格の窓いっぱいに切り抜き (9方向アンカー / パン対応)",
                    "Auto Aspect": "入力画像の縦横比から Portrait / Square / Landscape を自動判別",
                    "Keep Aspect": "元画像比率を100%維持し、インスタント写真の黄金比率外枠を付与",
                },
            },
            "film_tone": {
                "label": "フィルム現像トーン（独立トーンプロファイル）",
                "choices": ["Auto (Match Format)"] + list(instant_config.FILM_TONES.keys()),
            },
            "emulation_strength": {
                "label": "現像エミュレーション強度（0=完全非破壊, 1〜100=化学現像付与）",
                "range": [0, 100],
                "default": 65,
            },
            "paper_tone": {
                "label": "印画紙カラー・マテリアル",
                "choices": ["Auto (Match Format)"] + list(instant_config.PAPER_TONES.keys()),
            },
            "paper_texture": {
                "label": "印画紙テクスチャ・粗さ強度",
                "range": [0, 100],
                "default": 30,
            },
            "handwriting_style": {
                "label": "手書きフォントスタイル",
                "choices": list(instant_config.HANDWRITING_FONTS.keys()),
            },
            "ink_color": {
                "label": "インクカラー＆物理プロファイル",
                "choices": list(instant_config.INK_COLORS.keys()),
            },
            "layout_mode": {
                "label": "余白テキストレイアウト",
                "choices": [
                    "Center Caption + Right Date",
                    "Left Caption + Right Date",
                    "Center Caption Only",
                    "Right Date Only",
                    "Center Date Only",
                ],
            },
            "date_modes": {
                "photo": "写真のEXIF撮影日時（DateTimeOriginal）を自動反映",
                "today": "実行時の現在日付（'YY MM DD）を自動反映",
                "random": "1975〜2005年のランダムな過去日付を生成",
                "none": "日付を印字しない（キャプションのみ）",
                "custom": "指定した任意の日付文字列をそのまま印字",
            },
        },
        "presets": {
            "count": len(preset_items),
            "items": preset_items,
            "current_favorite": current_fav,
            "aliases": aliases,
        },
    }


def human_summary(caps: Dict[str, Any]) -> str:
    axes = caps["axes"]
    lines = [
        caps["summary"] + "。",
        "",
        "🌟 変えられる要素（軸）:",
        f"- 構図規格: {' / '.join(axes['frame_format']['choices'])}",
        f"- 適合方式: {' / '.join(axes['fit_mode']['choices'])}",
        f"- 現像トーン: Modern Clear (instax), Warm Amber (70s), Cool Cyan (90s), Pastel Muted, Vivid Pop, Classic B&W, Cinematic Teal, Bypass 等",
        f"- 現像強度: 0〜100 スライダー（0=色無変換・枠のみ, 65=推奨バランス）",
        f"- 印画紙カラー: Pure White, Warm Ivory, Aged Vintage, Matte Black",
        f"- 手書き文字: 日記ペン、かわいい丸文字、極細ペン、万年筆、筆文字、太字マーカー 等",
        f"- インク物理: 油性黒マジック、ゲル青ボールペン、濃紺万年筆、赤ペン、銀ラメペン、白ポスカ",
        f"- 日付指定: photo（EXIF撮影日）、today（今日の日付）、random（過去ランダム）、任意日付、または非表示",
        f"- 代表プリセット（{caps['presets']['count']}種）: instax-mini, polaroid-600, polaroid-sx70, instax-wide, pastel-dream, vivid-summer, classic-monochrome, cinematic-night 等",
        "",
        f"現在の既定プリセット（お気に入り）: {caps['presets']['current_favorite'].get('name', 'Instax Mini (Vertical Snap)')}",
    ]
    return "\n".join(lines)
