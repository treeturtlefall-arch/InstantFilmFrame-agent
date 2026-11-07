"""
InstantFilmFrame - 設定データクラス・幾何学仕様・トーンプロファイル・フォントおよびインク定義
"""
from dataclasses import dataclass
import datetime
import os
import random
from typing import Dict, Tuple, Any, Optional

# ディレクトリ基準パス
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(PACKAGE_ROOT, "fonts")

# Level 1: 構図選択肢 (Frame Formats)
FRAME_FORMATS = [
    "Portrait (Vertical)",
    "Square (Polaroid)",
    "Landscape (Wide)",
]

# Level 2: アスペクト適合方式 (Fit Modes)
FIT_MODES = [
    "Crop to Window",
    "Auto Aspect",
    "Keep Aspect",
]

# 実在フィルム規格の物理実測値に基づく幾何学プロポーション
# 基準寸法: s_ref = min(win_w, win_h)
FRAME_SPECS: Dict[str, Dict[str, Any]] = {
    # 1. instax mini (チェキ) 縦長
    # 写真窓: 46mm × 62mm (比率約 0.7419 ≈ 3:4) / 外枠: 54mm × 86mm (クレカ比率 1:1.593)
    "Portrait (Vertical)": {
        "aspect_ratio": 46.0 / 62.0,  # 0.741935...
        "margin_top": 0.130,          # 上余白 (実測 6.0mm / 46.0mm)
        "margin_bottom": 0.391,       # 下余白・顎 (実測 18.0mm / 46.0mm)
        "margin_sides": 0.087,        # 左右余白 (実測 4.0mm / 46.0mm)
        "corner_radius": 0.035,       # 外枠角丸
        "inner_radius": 0.008,        # 内窓ダイカット角丸
    },
    # 2. Polaroid 600 / SX-70 正方形
    # 写真窓: 79mm × 79mm (1:1) / 外枠: 88.5mm × 107.5mm (1:1.215)
    "Square (Polaroid)": {
        "aspect_ratio": 1.0,          # 1:1 正方形
        "margin_top": 0.063,          # 上余白 (実測 5.0mm / 79.0mm)
        "margin_bottom": 0.297,       # 下余白・顎 (実測 23.5mm / 79.0mm)
        "margin_sides": 0.060,        # 左右余白 (実測 4.75mm / 79.0mm)
        "corner_radius": 0.020,
        "inner_radius": 0.005,
    },
    # 3. instax WIDE 横長
    # 写真窓: 99mm × 62mm (比率約 1.5968 ≈ 16:10) / 外枠: 108mm × 86mm (1.256:1)
    "Landscape (Wide)": {
        "aspect_ratio": 99.0 / 62.0,  # 1.596774...
        "margin_top": 0.081,          # 上余白 (実測 5.0mm / 62.0mm)
        "margin_bottom": 0.306,       # 下余白・顎 (実測 19.0mm / 62.0mm)
        "margin_sides": 0.073,        # 左右余白 (実測 4.5mm / 62.0mm)
        "corner_radius": 0.020,
        "inner_radius": 0.005,
    },
}

# クロップ位置アンカー定義 (9方向アンカー)
CROP_POSITIONS = [
    "Center",
    "Top",
    "Bottom",
    "Left",
    "Right",
    "Top-Left",
    "Top-Right",
    "Bottom-Left",
    "Bottom-Right",
]

# 独立フィルム現像トーンプロファイル
FILM_TONES: Dict[str, Dict[str, Any]] = {
    "Auto (Match Format)": {},
    "Modern Clear (instax)": {
        "black_lift": (0.16, 0.12, 0.20),     # マゼンタ寄りのクリアな黒浮き
        "highlight_tint": (1.00, 0.94, 0.97), # 明るい人肌ハイキー
        "saturation": 1.15,
        "contrast": 1.10,
        "vignette": 0.42,
        "grain": 1.8,
        "softness": 0.45,
        "chroma_aberration": 1.8,
        "roller_unevenness": 0.04,
    },
    "Warm Amber (70s Vintage)": {
        "black_lift": (0.22, 0.17, 0.26),     # クラシックな濃厚青紫黒浮き
        "highlight_tint": (1.00, 0.88, 0.72), # 濃厚な夕暮れクリームハイライト
        "saturation": 0.82,
        "contrast": 1.22,
        "vignette": 0.68,                     # 深い周辺減光
        "grain": 3.0,
        "softness": 0.75,
        "chroma_aberration": 3.0,
        "roller_unevenness": 0.08,
    },
    "Cool Cyan (90s Snap)": {
        "black_lift": (0.15, 0.22, 0.25),     # 90年代ポラ特有の青緑黒浮き
        "highlight_tint": (0.94, 0.98, 0.88),
        "saturation": 0.88,
        "contrast": 1.16,
        "vignette": 0.55,
        "grain": 2.4,
        "softness": 0.60,
        "chroma_aberration": 2.4,
        "roller_unevenness": 0.06,
    },
    "Pastel Muted (Soft Dream)": {
        "black_lift": (0.18, 0.16, 0.20),     # ふんわり白浮きミルクフェード
        "highlight_tint": (1.00, 0.98, 0.96), # やわらかな自然光ハイライト
        "saturation": 0.90,                   # パステル調のやさしい彩度
        "contrast": 0.96,                     # 軟調・階調重視
        "vignette": 0.28,                     # 明るい画面を保つ控えめな減光
        "grain": 1.4,
        "softness": 0.65,                     # ふんわりソフトな光学質感
        "chroma_aberration": 1.2,
        "roller_unevenness": 0.03,
    },
    "Vivid Pop (Summer Punch)": {
        "black_lift": (0.10, 0.08, 0.12),     # 引き締まった黒
        "highlight_tint": (1.00, 0.96, 0.88), # ゴールデンサンシャイン
        "saturation": 1.35,                   # 原色が弾ける高彩度
        "contrast": 1.26,                     # トイカメラ風の高コントラスト
        "vignette": 0.60,
        "grain": 2.2,
        "softness": 0.35,
        "chroma_aberration": 2.8,             # トイレンズ風の微小色収差
        "roller_unevenness": 0.05,
    },
    "Classic B&W (Monochrome)": {
        "black_lift": (0.08, 0.08, 0.09),     # 均一な銀塩黒浮き
        "highlight_tint": (0.98, 0.98, 0.95), # 温黒調の温かみのある印画紙白
        "saturation": 0.0,                    # 完全脱色（スライダー連動で階調調整）
        "contrast": 1.24,                     # 深い黒と階調
        "vignette": 0.58,                     # クラシックレンズ周辺減光
        "grain": 2.8,                         # 豊かな銀塩粒子
        "softness": 0.50,
        "chroma_aberration": 0.0,             # モノクロのため色ズレなし
        "roller_unevenness": 0.05,
    },
    "Cinematic Teal (Moody Film)": {
        "black_lift": (0.08, 0.16, 0.22),     # 深い青緑・ティール黒浮き
        "highlight_tint": (0.92, 0.96, 1.00), # 青白いシネマティックハイライト
        "saturation": 0.82,                   # 落ち着いた映画調彩度
        "contrast": 1.35,                     # 重厚な陰影コントラスト
        "vignette": 0.75,                     # トンネル減光（夜景・フラッシュ直焚き）
        "grain": 2.6,
        "softness": 0.60,
        "chroma_aberration": 2.6,
        "roller_unevenness": 0.07,
    },
    "Bypass (No Filter)": {
        "black_lift": (0.0, 0.0, 0.0),
        "highlight_tint": (1.0, 1.0, 1.0),
        "saturation": 1.0,
        "contrast": 1.0,
        "vignette": 0.0,
        "grain": 0.0,
        "softness": 0.0,
        "chroma_aberration": 0.0,
        "roller_unevenness": 0.0,
    },
}

# 構図連動デフォルトトーン（Smart Default）
DEFAULT_FORMAT_TONES: Dict[str, str] = {
    "Portrait (Vertical)": "Modern Clear (instax)",
    "Square (Polaroid)": "Warm Amber (70s Vintage)",
    "Landscape (Wide)": "Cool Cyan (90s Snap)",
}

# 構図連動デフォルト用紙
DEFAULT_FORMAT_PAPERS: Dict[str, str] = {
    "Portrait (Vertical)": "Pure White",
    "Square (Polaroid)": "Warm Ivory",
    "Landscape (Wide)": "Pure White",
}

# 紙面カラー・質感定義
PAPER_TONES: Dict[str, Dict[str, Any]] = {
    "Pure White": {
        "rgb": (248, 248, 246),
        "grain": 1.5,
        "dark": False,
    },
    "Warm Ivory": {
        "rgb": (245, 239, 226),
        "grain": 2.0,
        "dark": False,
    },
    "Aged Vintage": {
        "rgb": (236, 225, 202),
        "grain": 3.0,
        "dark": False,
    },
    "Matte Black": {
        "rgb": (28, 28, 30),
        "grain": 2.2,
        "dark": True,
    },
}

PAPER_CHOICES = ["Auto (Match Format)"] + list(PAPER_TONES.keys())

# インク色定義 (RGB)
INK_COLORS: Dict[str, Tuple[int, int, int]] = {
    # 1. Permanent Marker (Oil-based)
    "Marker Black (Permanent)": (24, 25, 28),
    "Marker Red (Permanent)": (208, 32, 40),
    "Marker Blue (Permanent)": (26, 68, 172),
    # 2. Deco & Pop (Opaque Acrylic Paint)
    "Posca Pink (Opaque Paint)": (246, 65, 142),
    "Posca Yellow (Opaque Paint)": (226, 162, 8),      # High saturation yellow
    "Posca Sky Blue (Opaque Paint)": (54, 184, 240),
    "Posca Lime (Opaque Paint)": (52, 160, 56),        # High contrast lime green
    "Posca Violet (Opaque Paint)": (162, 86, 212),
    "Posca Orange (Opaque Paint)": (232, 88, 16),       # High saturation orange
    "Posca White (Opaque Paint)": (252, 252, 254),
    # 3. Metallic Flakes (Specular Glitter)
    "Glitter Gold (Metallic)": (226, 186, 88),
    "Metallic Silver (Metallic)": (218, 222, 230),
    # 4. Classic & Stamp (Ballpoint & Rubber Stamp)
    "Ballpoint Blue (Ballpoint)": (32, 64, 150),
    "Stamp Navy (Ink Stamp)": (36, 60, 105),
}

# 手書きスタイル枠（第1階層カテゴリ）
HANDWRITING_STYLES = [
    "Diary Pen (Casual Notes)",
    "Heisei Pop (Round Cheki)",
    "Traveler Marker (Chisel Tip)",
    "Archivist Note (Fountain Pen)",
    "Cinema Monologue (Subtitles & Script)",
    "All Fonts (Direct Access)",
]

# 手書きスタイル枠ごとの収録フォント選択肢（第2階層バリエーション）
STYLE_FONT_GROUPS: Dict[str, list] = {
    "Diary Pen (Casual Notes)": [
        "Auto",
        "Tekitou Poem (Casual Notes)",
        "Tekitou Poem Bold (Sign Pen)",
        "Zen Kurenaido (Ballpoint)",
        "Yomogi (Delicate Script)",
        "851 Tegaki Zatsu (Quick Scribble)",
        "Mushin (Relaxed Script)",
    ],
    "Heisei Pop (Round Cheki)": [
        "Auto",
        "Seto Font (Round Pop)",
        "Hachi Maru Pop (Retro Pop)",
        "FZ Korota (Cafe Light)",
    ],
    "Traveler Marker (Chisel Tip)": [
        "Auto",
        "Tekitou Poem Bold (Sign Pen)",
        "Yusei Magic (Permanent Marker)",
        "851 MakaPop (Thick Marker)",
        "RocknRoll One (Geometric Pop)",
    ],
    "Archivist Note (Fountain Pen)": [
        "Auto",
        "Yuji Syuku (Fountain Pen)",
        "Klee One (Neat Pen)",
        "Nani Font (Brush Pen)",
        "851 Chikara (Emotional Brush)",
    ],
    "Cinema Monologue (Subtitles & Script)": [
        "Auto",
        "Cinecaption (Cinema Subtitle)",
        "Caveat Brush (Casual Brush)",
        "Pinyon Script (Calligraphy)",
        "Slackside One (Relaxed Felt)",
    ],
}

# 全フォント一覧 (全20書体)
ALL_AVAILABLE_FONTS = [
    # Traveler
    "Yusei Magic (Permanent Marker)",
    "851 MakaPop (Thick Marker)",
    "RocknRoll One (Geometric Pop)",
    # Diary
    "Tekitou Poem (Casual Notes)",
    "Tekitou Poem Bold (Sign Pen)",
    "Zen Kurenaido (Ballpoint)",
    "Yomogi (Delicate Script)",
    "851 Tegaki Zatsu (Quick Scribble)",
    "Mushin (Relaxed Script)",
    # Heisei Pop
    "Seto Font (Round Pop)",
    "Hachi Maru Pop (Retro Pop)",
    "FZ Korota (Cafe Light)",
    # Archivist
    "Yuji Syuku (Fountain Pen)",
    "Klee One (Neat Pen)",
    "Nani Font (Brush Pen)",
    "851 Chikara (Emotional Brush)",
    # Cinema / English
    "Cinecaption (Cinema Subtitle)",
    "Caveat Brush (Casual Brush)",
    "Pinyon Script (Calligraphy)",
    "Slackside One (Relaxed Felt)",
]
STYLE_FONT_GROUPS["All Fonts (Direct Access)"] = ["Auto"] + ALL_AVAILABLE_FONTS

# スタイル枠 Auto 時の推奨デフォルトフォント
STYLE_DEFAULT_FONTS: Dict[str, str] = {
    "Diary Pen (Casual Notes)": "Tekitou Poem (Casual Notes)",
    "Heisei Pop (Round Cheki)": "Seto Font (Round Pop)",
    "Traveler Marker (Chisel Tip)": "Tekitou Poem Bold (Sign Pen)",
    "Archivist Note (Fountain Pen)": "Yuji Syuku (Fountain Pen)",
    "Cinema Monologue (Subtitles & Script)": "Cinecaption (Cinema Subtitle)",
    "All Fonts (Direct Access)": "Tekitou Poem (Casual Notes)",
}

# 全フォント候補（ComfyUIウィジェット用フラット一覧）
FONT_CHOICES = ["Auto"] + ALL_AVAILABLE_FONTS

# 手書きフォント名 ⇄ ファイル名マッピング (全20書体)
HANDWRITING_FONTS: Dict[str, str] = {
    # 1. Traveler Marker
    "Yusei Magic (Permanent Marker)": "YuseiMagic-Regular.ttf",
    "851 MakaPop (Thick Marker)": "851MkPOP_101.ttf",
    "RocknRoll One (Geometric Pop)": "RocknRollOne-Regular.ttf",
    # 2. Diary Pen
    "Tekitou Poem (Casual Notes)": "TekitouPoem.ttf",
    "Tekitou Poem Bold (Sign Pen)": "TekitouPoem_Bold.ttf",
    "Zen Kurenaido (Ballpoint)": "ZenKurenaido-Regular.ttf",
    "851 Tegaki Zatsu (Quick Scribble)": "851tegaki_zatsu_normal_0883.ttf",
    "Mushin (Relaxed Script)": "mushin.otf",
    # 3. Heisei Pop
    "Seto Font (Round Pop)": "SetoFont.ttf",
    "Hachi Maru Pop (Retro Pop)": "HachiMaruPop-Regular.ttf",
    "FZ Korota (Cafe Light)": "FZ-Korota-light.ttf",
    # 4. Archivist Note
    "Yuji Syuku (Fountain Pen)": "YujiSyuku-Regular.ttf",
    "Klee One (Neat Pen)": "KleeOne-Regular.ttf",
    "Nani Font (Brush Pen)": "NaniFont-Regular.ttf",
    "851 Chikara (Emotional Brush)": "851CHIKARA-DZUYOKU_kanaA_004.ttf",
    # 5. Cinema Monologue / English
    "Cinecaption (Cinema Subtitle)": "cinecaption.ttf",
    "Pinyon Script (Calligraphy)": "PinyonScript-Regular.ttf",
    "Yomogi (Delicate Script)": "Yomogi-Regular.ttf",
    "Caveat Brush (Casual Brush)": "CaveatBrush-Regular.ttf",
    "Slackside One (Relaxed Felt)": "SlacksideOne-Regular.ttf",
}

# フォントごとの視覚サイズ自動正規化係数 (Visual Size Normalization)
FONT_NORM_FACTORS: Dict[str, float] = {
    # 1. Traveler Marker
    "Yusei Magic (Permanent Marker)": 0.98,
    "851 MakaPop (Thick Marker)": 0.95,
    "RocknRoll One (Geometric Pop)": 0.95,
    # 2. Diary Pen
    "Tekitou Poem (Casual Notes)": 1.05,
    "Tekitou Poem Bold (Sign Pen)": 1.05,
    "Zen Kurenaido (Ballpoint)": 1.05,
    "851 Tegaki Zatsu (Quick Scribble)": 1.08,
    "Mushin (Relaxed Script)": 1.04,
    # 3. Heisei Pop
    "Seto Font (Round Pop)": 1.00,
    "Hachi Maru Pop (Retro Pop)": 0.98,
    "FZ Korota (Cafe Light)": 1.12,
    # 4. Archivist Note
    "Yuji Syuku (Fountain Pen)": 1.05,
    "Klee One (Neat Pen)": 1.06,
    "Nani Font (Brush Pen)": 1.00,
    "851 Chikara (Emotional Brush)": 1.02,
    # 5. Cinema Monologue / English
    "Cinecaption (Cinema Subtitle)": 1.04,
    "Pinyon Script (Calligraphy)": 1.25,
    "Yomogi (Delicate Script)": 1.10,
    "Caveat Brush (Casual Brush)": 1.15,
    "Slackside One (Relaxed Felt)": 1.18,
}

# 全水準漢字を網羅するフォールバックフォント（約16,100字収録）
FALLBACK_FONT_FILE = "TekitouPoem.ttf"

# ファイル名 ⇄ 視覚正規化係数マッピング
FONT_FILE_NORM_FACTORS: Dict[str, float] = {}
for _disp_name, _file_name in HANDWRITING_FONTS.items():
    if _disp_name in FONT_NORM_FACTORS:
        FONT_FILE_NORM_FACTORS[_file_name] = FONT_NORM_FACTORS[_disp_name]
FONT_FILE_NORM_FACTORS[FALLBACK_FONT_FILE] = FONT_NORM_FACTORS.get("Tekitou Poem (Casual Notes)", 1.05)


def get_font_norm_factor(font_key_or_file: str) -> float:
    """フォント表示名またはファイル名から視覚正規化係数を取得する"""
    if not font_key_or_file:
        return 1.0
    if font_key_or_file in FONT_NORM_FACTORS:
        return FONT_NORM_FACTORS[font_key_or_file]
    if font_key_or_file in FONT_FILE_NORM_FACTORS:
        return FONT_FILE_NORM_FACTORS[font_key_or_file]
    # ファイル名ベース（パス付き等）
    base = os.path.basename(font_key_or_file)
    return FONT_FILE_NORM_FACTORS.get(base, 1.0)


# 書体別キネマティクス定義 (Handwriting Kinematics Profiles)
# 人間の書字運動特性: 手首ピボット弧 (arc), 1文字回転 (rot), 上下ジッター (dy), 字間スラック (dx), 字粒筆勢 (scale), 行全体傾き (tilt)
FONT_KINEMATICS: Dict[str, Dict[str, float]] = {
    # 1. Connected Script (筆記体): リガチャー切断を防止するため字間揺らぎゼロ、回転・上下ジッターを大幅抑制
    "Pinyon Script (Calligraphy)": {
        "arc_mul": 0.65, "rot_mul": 0.15, "dy_mul": 0.15, "dx_mul": 0.00, "scale_mul": 0.20, "tilt_mul": 0.75,
    },
    "Caveat Brush (Casual Brush)": {
        "arc_mul": 0.70, "rot_mul": 0.20, "dy_mul": 0.20, "dx_mul": 0.00, "scale_mul": 0.25, "tilt_mul": 0.80,
    },
    # 2. Neat / Subtitle (端正・字幕): 几帳面な大人の筆致、抑制された上品な揺らぎ
    "Cinecaption (Cinema Subtitle)": {
        "arc_mul": 0.55, "rot_mul": 0.50, "dy_mul": 0.50, "dx_mul": 0.45, "scale_mul": 0.35, "tilt_mul": 0.55,
    },
    "Klee One (Neat Pen)": {
        "arc_mul": 0.60, "rot_mul": 0.55, "dy_mul": 0.50, "dx_mul": 0.50, "scale_mul": 0.40, "tilt_mul": 0.60,
    },
    "Yuji Syuku (Fountain Pen)": {
        "arc_mul": 0.65, "rot_mul": 0.60, "dy_mul": 0.55, "dx_mul": 0.50, "scale_mul": 0.45, "tilt_mul": 0.65,
    },
    # 3. Heisei Pop (丸文字・チェキ): コロコロと弾む字粒感と愛らしいリズム
    "Seto Font (Round Pop)": {
        "arc_mul": 0.85, "rot_mul": 1.15, "dy_mul": 1.10, "dx_mul": 0.85, "scale_mul": 1.15, "tilt_mul": 0.90,
    },
    "Hachi Maru Pop (Retro Pop)": {
        "arc_mul": 0.85, "rot_mul": 1.15, "dy_mul": 1.10, "dx_mul": 0.85, "scale_mul": 1.15, "tilt_mul": 0.90,
    },
    "FZ Korota (Cafe Light)": {
        "arc_mul": 0.80, "rot_mul": 1.10, "dy_mul": 1.05, "dx_mul": 0.80, "scale_mul": 1.10, "tilt_mul": 0.85,
    },
    # 4. Quick Scribble (走り書き・筆勢): 勢いのあるラフな筆致
    "851 Tegaki Zatsu (Quick Scribble)": {
        "arc_mul": 1.15, "rot_mul": 1.25, "dy_mul": 1.20, "dx_mul": 1.15, "scale_mul": 1.25, "tilt_mul": 1.20,
    },
    "851 MakaPop (Thick Marker)": {
        "arc_mul": 1.10, "rot_mul": 1.20, "dy_mul": 1.15, "dx_mul": 1.10, "scale_mul": 1.20, "tilt_mul": 1.15,
    },
    "851 Chikara (Emotional Brush)": {
        "arc_mul": 1.20, "rot_mul": 1.30, "dy_mul": 1.25, "dx_mul": 1.20, "scale_mul": 1.30, "tilt_mul": 1.25,
    },
    "Slackside One (Relaxed Felt)": {
        "arc_mul": 1.15, "rot_mul": 1.20, "dy_mul": 1.15, "dx_mul": 1.10, "scale_mul": 1.15, "tilt_mul": 1.15,
    },
}

# ファイル名 ⇄ キネマティクス辞書
FONT_FILE_KINEMATICS: Dict[str, Dict[str, float]] = {}
for _disp_name, _file_name in HANDWRITING_FONTS.items():
    if _disp_name in FONT_KINEMATICS:
        FONT_FILE_KINEMATICS[_file_name] = FONT_KINEMATICS[_disp_name]

# スタンプ（剛体）キネマティクス: 手首アークゼロ、回転・上下ジッター極小、字間ゼロ
STAMP_KINEMATICS: Dict[str, float] = {
    "arc_mul": 0.00,
    "rot_mul": 0.06,
    "dy_mul": 0.10,
    "dx_mul": 0.04,
    "scale_mul": 0.00,
    "tilt_mul": 0.85,
}

DEFAULT_KINEMATICS: Dict[str, float] = {
    "arc_mul": 1.00,
    "rot_mul": 1.00,
    "dy_mul": 1.00,
    "dx_mul": 1.00,
    "scale_mul": 1.00,
    "tilt_mul": 1.00,
}


def get_handwriting_kinematics(font_key_or_file: str, pen_type: str = "marker") -> Dict[str, float]:
    """フォント名/ファイル名およびペンの種類に応じた書字キネマティクスを取得する"""
    if pen_type == "stamp":
        return STAMP_KINEMATICS.copy()

    if not font_key_or_file:
        return DEFAULT_KINEMATICS.copy()

    if font_key_or_file in FONT_KINEMATICS:
        return FONT_KINEMATICS[font_key_or_file].copy()

    if font_key_or_file in FONT_FILE_KINEMATICS:
        return FONT_FILE_KINEMATICS[font_key_or_file].copy()

    base = os.path.basename(font_key_or_file)
    if base in FONT_FILE_KINEMATICS:
        return FONT_FILE_KINEMATICS[base].copy()

    return DEFAULT_KINEMATICS.copy()


# インク種別ごとの物理質感プロファイル (Ink Physics Profiles)
INK_PHYSICS: Dict[str, Dict[str, Any]] = {
    # 1. Permanent Marker (Oil-based)
    "Marker Black (Permanent)": {
        "pen_type": "marker",
        "bleed_radius": 0.65,         # Capillary ink bleed into paper fibers
        "unevenness": 0.12,          # Ink pooling and concentration variations
        "opacity": 0.96,             # Dense permanent dye
        "glitter": 0.0,
    },
    "Marker Red (Permanent)": {
        "pen_type": "marker",
        "bleed_radius": 0.65,
        "unevenness": 0.14,
        "opacity": 0.95,
        "glitter": 0.0,
    },
    "Marker Blue (Permanent)": {
        "pen_type": "marker",
        "bleed_radius": 0.60,
        "unevenness": 0.14,
        "opacity": 0.95,
        "glitter": 0.0,
    },
    # 2. Deco & Pop (Opaque Acrylic Paint)
    "Posca Pink (Opaque Paint)": {
        "pen_type": "posca",
        "bleed_radius": 0.25,
        "unevenness": 0.06,
        "opacity": 0.99,
        "glitter": 0.0,
    },
    "Posca Yellow (Opaque Paint)": {
        "pen_type": "posca",
        "bleed_radius": 0.25,
        "unevenness": 0.06,
        "opacity": 0.99,
        "glitter": 0.0,
    },
    "Posca Sky Blue (Opaque Paint)": {
        "pen_type": "posca",
        "bleed_radius": 0.25,
        "unevenness": 0.06,
        "opacity": 0.99,
        "glitter": 0.0,
    },
    "Posca Lime (Opaque Paint)": {
        "pen_type": "posca",
        "bleed_radius": 0.25,
        "unevenness": 0.06,
        "opacity": 0.99,
        "glitter": 0.0,
    },
    "Posca Violet (Opaque Paint)": {
        "pen_type": "posca",
        "bleed_radius": 0.25,
        "unevenness": 0.06,
        "opacity": 0.99,
        "glitter": 0.0,
    },
    "Posca Orange (Opaque Paint)": {
        "pen_type": "posca",
        "bleed_radius": 0.25,
        "unevenness": 0.06,
        "opacity": 0.99,
        "glitter": 0.0,
    },
    "Posca White (Opaque Paint)": {
        "pen_type": "posca",
        "bleed_radius": 0.20,
        "unevenness": 0.04,
        "opacity": 1.00,
        "glitter": 0.0,
    },
    # 3. Metallic Flakes (Specular Glitter)
    "Glitter Gold (Metallic)": {
        "pen_type": "metallic",
        "bleed_radius": 0.10,
        "unevenness": 0.22,
        "opacity": 0.95,
        "glitter": 0.45,
    },
    "Metallic Silver (Metallic)": {
        "pen_type": "metallic",
        "bleed_radius": 0.10,
        "unevenness": 0.25,
        "opacity": 0.92,
        "glitter": 0.40,
    },
    # 4. Classic & Stamp (Ballpoint & Rubber Stamp)
    "Ballpoint Blue (Ballpoint)": {
        "pen_type": "ballpoint",
        "bleed_radius": 0.20,
        "unevenness": 0.22,          # Pen pressure scratch & high frequency texture
        "opacity": 0.88,
        "glitter": 0.0,
    },
    "Stamp Navy (Ink Stamp)": {
        "pen_type": "stamp",
        "bleed_radius": 0.50,
        "unevenness": 0.30,          # Rubber stamp & fountain pen shading
        "opacity": 0.89,
        "glitter": 0.0,
    },
}


def resolve_ink_key(key: str) -> str:
    """インクカラー名を検証し、未指定または不正値の場合はデフォルトを返す"""
    if not key:
        return "Marker Black (Permanent)"
    if key in INK_COLORS:
        return key
    return "Marker Black (Permanent)"


def get_ink_color_rgb(key: str) -> Tuple[int, int, int]:
    canonical = resolve_ink_key(key)
    return INK_COLORS.get(canonical, (24, 25, 28))


def get_ink_physics(key: str) -> Dict[str, Any]:
    canonical = resolve_ink_key(key)
    return INK_PHYSICS.get(canonical, INK_PHYSICS["Marker Black (Permanent)"])

LAYOUT_MODES = [
    "Center Caption + Right Date",
    "Left Stacked (Caption & Date)",
    "Caption Only (Centered)",
    "Date Only (Bottom Right)",
]


@dataclass
class InstantFrameConfig:
    # Level 1: 構図選択
    frame_format: str = "Portrait (Vertical)"
    # Level 2: アスペクト適合
    fit_mode: str = "Crop to Window"
    crop_position: str = "Center"
    pan_x: float = 0.0
    pan_y: float = 0.0
    # Level 3: 現像エミュレーション
    film_tone: str = "Auto (Match Format)"
    emulation_strength: int = 65  # 0 to 100
    # Level 4: 印画紙マテリアル
    paper_tone: str = "Auto (Match Format)"
    paper_texture: int = 30       # 0 to 100
    # Level 5: 手書きタイポグラフィ
    caption_text: str = ""
    date_string: str = "today"
    handwriting_style: str = "Diary Pen (Casual Notes)"
    font_choice: str = "Auto"
    ink_color: str = "Marker Black (Permanent)"
    layout_mode: str = "Center Caption + Right Date"
    font_scale: float = 1.0
    handwriting_wobble: int = 50  # 0 to 100
    # System: シード
    seed: int = 0
    # スマート被写体フレーミング (SAMマスク / AIエージェント共通)
    subject_mask: Optional[Any] = None  # np.ndarray [H, W] float32
    subject_bbox: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1) in 0.0~1.0
    focus_point: Optional[Tuple[float, float]] = None  # (cx, cy) in 0.0~1.0


def resolve_date_string(date_string: str, seed: int = 0) -> str:
    """
    日付文字列を解決する。
    - 'today'（未指定時含む）: 今日の日付 ('%y %m %d)
    - 'random': 1975〜2005年のランダムな過去日付
    - 自由記述（例: '98 08 15, 2024.12.24 等）: そのまま印字
    """
    raw = str(date_string).strip()
    if not raw:
        return ""
    key = raw.lower()
    if key == "today":
        now = datetime.datetime.now()
        return now.strftime("'%y %m %d")
    if key == "random":
        rng = random.Random(seed)
        year = rng.randint(1975, 2005)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        return f"'{year % 100:02d} {month:02d} {day:02d}"
    return raw


def resolve_handwriting_font(
    style_name: Optional[str] = None,
    font_choice: Optional[str] = None,
) -> Tuple[str, float]:
    """
    スタイル枠 (style_name) とフォント選択 (font_choice) から、
    使用するフォントファイル名と視覚正規化係数を解決する。
    """
    eff_style = style_name or "Diary Pen (Casual Notes)"
    eff_choice = (font_choice or "").strip()

    # 1. font_choice が Auto または未指定の場合
    if not eff_choice or eff_choice == "Auto":
        font_key = STYLE_DEFAULT_FONTS.get(eff_style, "Tekitou Poem (Casual Notes)")
    else:
        font_key = eff_choice

    # 2. フォントファイル名の特定
    font_file = HANDWRITING_FONTS.get(font_key, FALLBACK_FONT_FILE)

    # 3. 正規化係数の取得
    norm_factor = get_font_norm_factor(font_key)
    if norm_factor == 1.0 and font_file:
        norm_factor = get_font_norm_factor(font_file)
    return font_file, norm_factor
