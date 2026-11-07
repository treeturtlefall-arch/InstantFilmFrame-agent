"""
InstantFilmFrame - コア描画・現像エミュレーションエンジン (NumPy + Pillow)
ComfyUI 非依存で単体動作可能。
"""
import os
import math
import random
import functools
import struct
from typing import Tuple, Dict, Any, Optional, Set
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from .instant_config import (
        InstantFrameConfig,
        FRAME_SPECS,
        PAPER_TONES,
        INK_COLORS,
        HANDWRITING_FONTS,
        FONT_NORM_FACTORS,
        INK_PHYSICS,
        FILM_TONES,
        DEFAULT_FORMAT_TONES,
        DEFAULT_FORMAT_PAPERS,
        FONTS_DIR,
        FALLBACK_FONT_FILE,
        get_font_norm_factor,
        get_handwriting_kinematics,
        resolve_date_string,
        resolve_handwriting_font,
        resolve_ink_key,
        get_ink_color_rgb,
        get_ink_physics,
    )
except (ImportError, ValueError):
    from instant_config import (
        InstantFrameConfig,
        FRAME_SPECS,
        PAPER_TONES,
        INK_COLORS,
        HANDWRITING_FONTS,
        FONT_NORM_FACTORS,
        INK_PHYSICS,
        FILM_TONES,
        DEFAULT_FORMAT_TONES,
        DEFAULT_FORMAT_PAPERS,
        FONTS_DIR,
        FALLBACK_FONT_FILE,
        get_font_norm_factor,
        get_handwriting_kinematics,
        resolve_date_string,
        resolve_handwriting_font,
        resolve_ink_key,
        get_ink_color_rgb,
        get_ink_physics,
    )


def _align_dimension(val: int, multiple: int = 8) -> int:
    """指定倍数 (default: 8) に切り上げて丸める（余白の安全マージンを確保）"""
    if multiple <= 1:
        return val
    return ((val + multiple - 1) // multiple) * multiple


# 9方向アンカーマッピング (rel_x, rel_y)
CROP_ANCHOR_OFFSETS: Dict[str, Tuple[float, float]] = {
    "Center": (0.5, 0.5),
    "Top": (0.5, 0.0),
    "Bottom": (0.5, 1.0),
    "Left": (0.0, 0.5),
    "Right": (1.0, 0.5),
    "Top-Left": (0.0, 0.0),
    "Top-Right": (1.0, 0.0),
    "Bottom-Left": (0.0, 1.0),
    "Bottom-Right": (1.0, 1.0),
}


def _extract_subject_region(
    img_np: np.ndarray,
    subject_mask: Optional[np.ndarray] = None,
    subject_bbox: Optional[Tuple[float, float, float, float]] = None,
    focus_point: Optional[Tuple[float, float]] = None,
) -> Optional[Dict[str, float]]:
    """
    マスク、またはBBox/注視点から被写体の正規化領域 (cx, cy, x0, y0, x1, y1) を抽出する。
    - 優先度1: subject_bbox または focus_point (AIエージェントCLI用)
    - 優先度2: subject_mask (SAM / 検出器マスク接続時)
    """
    h, w, _ = img_np.shape

    # 優先度1: AIエージェント直接指定
    if subject_bbox is not None:
        x0, y0, x1, y1 = [float(v) for v in subject_bbox]
        x0 = max(0.0, min(1.0, x0))
        y0 = max(0.0, min(1.0, y0))
        x1 = max(x0, min(1.0, x1))
        y1 = max(y0, min(1.0, y1))
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        return {"cx": cx, "cy": cy, "x0": x0, "y0": y0, "x1": x1, "y1": y1}

    if focus_point is not None:
        cx, cy = [float(v) for v in focus_point]
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        return {
            "cx": cx,
            "cy": cy,
            "x0": max(0.0, cx - 0.12),
            "y0": max(0.0, cy - 0.12),
            "x1": min(1.0, cx + 0.12),
            "y1": min(1.0, cy + 0.12),
        }

    # 優先度2: subject_mask (SAM等)
    if subject_mask is not None:
        mask_np = np.asarray(subject_mask, dtype=np.float32)
        if mask_np.ndim == 3:
            mask_np = mask_np[0] if mask_np.shape[0] == 1 else mask_np[:, :, 0]
        mh, mw = mask_np.shape
        if (mh, mw) != (h, w):
            pil_m = Image.fromarray(np.clip(mask_np * 255.0, 0, 255).astype(np.uint8), mode="L")
            resized_m = pil_m.resize((w, h), Image.Resampling.BILINEAR)
            mask_np = np.array(resized_m, dtype=np.float32) / 255.0

        active_indices = np.where(mask_np > 0.08)
        if len(active_indices[0]) > 0:
            weights = mask_np[active_indices]
            sum_w = float(np.sum(weights))
            if sum_w > 1e-4:
                yy, xx = active_indices
                cy = float(np.sum(yy * weights) / sum_w) / max(1.0, float(h))
                cx = float(np.sum(xx * weights) / sum_w) / max(1.0, float(w))
                y0 = float(np.min(yy)) / max(1.0, float(h))
                y1 = float(np.max(yy)) / max(1.0, float(h))
                x0 = float(np.min(xx)) / max(1.0, float(w))
                x1 = float(np.max(xx)) / max(1.0, float(w))
                return {
                    "cx": float(np.clip(cx, 0.0, 1.0)),
                    "cy": float(np.clip(cy, 0.0, 1.0)),
                    "x0": float(np.clip(x0, 0.0, 1.0)),
                    "y0": float(np.clip(y0, 0.0, 1.0)),
                    "x1": float(np.clip(x1, 0.0, 1.0)),
                    "y1": float(np.clip(y1, 0.0, 1.0)),
                }

    return None


def _crop_and_fit_window(
    img_np: np.ndarray,
    target_aspect: Optional[float],
    crop_position: str = "Center",
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    subject_mask: Optional[np.ndarray] = None,
    subject_bbox: Optional[Tuple[float, float, float, float]] = None,
    focus_point: Optional[Tuple[float, float]] = None,
) -> np.ndarray:
    """
    指定アスペクト比 (w / h)、アンカー位置、パンオフセットに基づいて入力画像を切り抜く。
    - target_aspect が None または <= 0 の場合は、元画像のアスペクト比を維持。
    - crop_position: 9方向 ("Center", "Top", "Top-Right", etc.)
    - pan_x, pan_y: アンカー位置からの微調整 (-1.0 〜 1.0)
    - subject_mask / subject_bbox / focus_point: スマート被写体フレーミング用
    """
    h, w, c = img_np.shape
    current_aspect = w / h

    # 目標アスペクト比（None または <= 0 の場合は元画像比率を維持）
    eff_aspect = target_aspect if (target_aspect is not None and target_aspect > 0) else current_aspect

    # 基本切り抜きサイズ（短辺100%基準）
    if current_aspect > eff_aspect:
        base_h = h
        base_w = max(2, int(round(h * eff_aspect)))
    else:
        base_w = w
        base_h = max(2, int(round(w / eff_aspect)))

    crop_w = base_w
    crop_h = base_h

    # 偶数化（Mod-2 アライメント）＆画像境界クリップ
    crop_w = crop_w - (crop_w % 2)
    crop_h = crop_h - (crop_h % 2)
    crop_w = max(2, min(w, crop_w))
    crop_h = max(2, min(h, crop_h))

    # 可動域（スラック）
    slack_x = w - crop_w
    slack_y = h - crop_h

    # 被写体領域の解析
    subject_info = _extract_subject_region(
        img_np,
        subject_mask=subject_mask,
        subject_bbox=subject_bbox,
        focus_point=focus_point,
    )

    if subject_info is not None:
        # カメラマン構図ロジック: 三分割・上寄り配置 (黄金比 42%) とヘッドルーム保護
        cx = subject_info["cx"]
        cy = subject_info["cy"]
        y0 = subject_info["y0"]
        y1 = subject_info["y1"]
        x0 = subject_info["x0"]
        x1 = subject_info["x1"]

        # 理想の開始位置（重心を横50%、縦42%に配置）
        ideal_start_x = cx * w - 0.50 * crop_w
        ideal_start_y = cy * h - 0.42 * crop_h

        # ヘッドルーム（頭上余白: 窓高の約 6%）保護: 被写体上端が切れるのを防止
        headroom = crop_h * 0.06
        sub_top_px = y0 * h
        if ideal_start_y > sub_top_px - headroom:
            ideal_start_y = sub_top_px - headroom

        # 被写体下端保護 (被写体全体の高さが窓に収まる場合)
        sub_bottom_px = y1 * h
        sub_h_px = (y1 - y0) * h
        if sub_h_px <= crop_h and (ideal_start_y + crop_h) < sub_bottom_px:
            ideal_start_y = sub_bottom_px - crop_h

        # 横方向の被写体はみ出し保護 (被写体全体の幅が窓に収まる場合)
        sub_left_px = x0 * w
        sub_right_px = x1 * w
        sub_w_px = (x1 - x0) * w
        if sub_w_px <= crop_w:
            if ideal_start_x > sub_left_px:
                ideal_start_x = sub_left_px
            elif (ideal_start_x + crop_w) < sub_right_px:
                ideal_start_x = sub_right_px - crop_w

        base_x = float(np.clip(ideal_start_x, 0, max(0, slack_x)))
        base_y = float(np.clip(ideal_start_y, 0, max(0, slack_y)))
    else:
        # 9方向アンカー位置 (0.0〜1.0)
        rel_x, rel_y = CROP_ANCHOR_OFFSETS.get(crop_position, (0.5, 0.5))
        base_x = rel_x * slack_x
        base_y = rel_y * slack_y

    # パン微調整 (-1.0〜1.0)
    shift_x = pan_x * (slack_x / 2.0)
    shift_y = pan_y * (slack_y / 2.0)

    start_x = int(round(np.clip(base_x + shift_x, 0, max(0, slack_x))))
    start_y = int(round(np.clip(base_y + shift_y, 0, max(0, slack_y))))

    return img_np[start_y : start_y + crop_h, start_x : start_x + crop_w, :]


def _apply_instant_emulation(
    img_np: np.ndarray,
    strength: float,
    tone_profile: Dict[str, Any],
    seed: int = 0,
) -> np.ndarray:
    """
    インスタント写真の化学現像 ＆ 光学エミュレーション (5段階パイプライン)
    strength: 0.0 (完全非破壊バイパス) 〜 1.0 (最大化学現像エミュレート)
    """
    if strength <= 0.0:
        return img_np.copy()

    h, w, _ = img_np.shape
    rng = np.random.RandomState(seed & 0xFFFFFFFF)

    # Step 2.1: プラスチックレンズ光学緩和 (Optical Softness)
    softness = float(tone_profile.get("softness", 0.75))
    if softness > 0.05:
        pil_tmp = Image.fromarray((img_np * 255.0).astype(np.uint8))
        blur_radius = max(0.6, 1.6 * softness)
        blurred_pil = pil_tmp.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        blurred_np = np.array(blurred_pil, dtype=np.float32) / 255.0
        soft_blend = min(0.65, 0.65 * softness)
        res = img_np * (1.0 - soft_blend) + blurred_np * soft_blend
    else:
        res = img_np.copy()

    # Step 2.2: 水平・周辺微小色収差 (Chromatic Aberration)
    ca_amount = float(tone_profile.get("chroma_aberration", 2.8))
    shift_px = int(round(ca_amount))
    if shift_px > 0:
        r_shifted = np.pad(res[:, :-shift_px, 0], ((0, 0), (shift_px, 0)), mode="edge")
        b_shifted = np.pad(res[:, shift_px:, 2], ((0, 0), (0, shift_px)), mode="edge")
        res[:, :, 0] = r_shifted
        res[:, :, 2] = b_shifted

    # Step 2.3: 化学現像トーンカーブ ＆ スプリットトーニング (インプレース高速化)
    black_lift = np.array(tone_profile.get("black_lift", (0.24, 0.18, 0.28)), dtype=np.float32)
    highlight_tint = np.array(tone_profile.get("highlight_tint", (1.00, 0.88, 0.72)), dtype=np.float32)
    contrast = float(tone_profile.get("contrast", 1.22))
    saturation = float(tone_profile.get("saturation", 0.78))
    vignette_amount = float(tone_profile.get("vignette", 0.68))
    grain_amount = float(tone_profile.get("grain", 3.2)) * 0.01
    roller_unevenness = float(tone_profile.get("roller_unevenness", 0.08))

    res *= contrast
    res += 0.45 * (1.0 - contrast)
    np.clip(res, 0.0, 1.0, out=res)

    res *= (1.0 - black_lift)
    res += black_lift
    res *= highlight_tint
    np.clip(res, 0.0, 1.0, out=res)

    luma = 0.299 * res[:, :, 0] + 0.587 * res[:, :, 1] + 0.114 * res[:, :, 2]
    res -= luma[:, :, None]
    res *= saturation
    res += luma[:, :, None]
    np.clip(res, 0.0, 1.0, out=res)

    # Step 2.4: ローラー薬液展開ムラ & レンズ周辺減光 (2Dマスク事前統合)
    y_coords = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    x_coords = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    r_sq = (x_coords ** 2 + y_coords ** 2) * 0.5
    vignette_mask = 1.0 - np.clip(r_sq * vignette_amount, 0.0, 0.88)
    if roller_unevenness > 0:
        roller_grad = 1.0 + roller_unevenness * np.sin(np.linspace(0, np.pi * 1.5, h, dtype=np.float32))[:, None]
        vignette_mask *= roller_grad
    res *= vignette_mask[:, :, None]
    np.clip(res, 0.0, 1.0, out=res)

    # Step 2.5: 輝度連動の色素雲グレイン（白黒は純銀塩輝度ノイズ、カラーは有機的グレイン）
    if grain_amount > 0:
        cur_luma = 0.299 * res[:, :, 0] + 0.587 * res[:, :, 1] + 0.114 * res[:, :, 2]
        luma_clamped = np.clip(cur_luma, 0.0, 1.0)
        grain_weight = (1.0 - luma_clamped ** 1.3) * (0.35 + 0.65 * np.sqrt(luma_clamped))
        grain_weight = np.clip(grain_weight, 0.0, 1.0)[:, :, None]

        if saturation <= 0.01:
            # モノクロ時は純粋な銀塩輝度グレイン（カラーノイズの混入を完全防止）
            raw_noise = rng.normal(0.0, grain_amount * 1.4, (h, w, 1)).astype(np.float32)
        else:
            # カラー時は有機的フィルム粒子（主たる輝度グレイン75% + 微小色素雲クロマグレイン25%）
            l_noise = rng.normal(0.0, grain_amount * 1.2, (h, w, 1)).astype(np.float32)
            c_noise = rng.normal(0.0, grain_amount * 0.4, (h, w, 3)).astype(np.float32)
            raw_noise = l_noise + c_noise

        res += raw_noise * grain_weight
        np.clip(res, 0.0, 1.0, out=res)

    out = img_np * (1.0 - strength) + res * strength
    return np.clip(out, 0.0, 1.0)


def _norm_std(arr: np.ndarray) -> np.ndarray:
    """配列を平均0・標準偏差1.0に正規化するヘルパー"""
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    if std < 1e-6:
        return arr - mean
    return (arr - mean) / std


def _generate_smooth_field(
    h: int,
    w: int,
    rng: np.random.RandomState,
    grid_div: int,
) -> np.ndarray:
    """大域的な滑らかフィールド生成（ブロッチ感のない超低周波グラデーション用）"""
    gh = max(2, int(round(h / grid_div)))
    gw = max(2, int(round(w / grid_div)))
    grid = rng.normal(0.0, 1.0, (gh, gw)).astype(np.float32)
    grid_u8 = np.clip((grid / 5.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
    pil_g = Image.fromarray(grid_u8, mode="L").resize((w, h), Image.Resampling.BICUBIC)
    return _norm_std(np.array(pil_g, dtype=np.float32))


def _generate_coated_micro_emboss(
    h: int,
    w: int,
    rng: np.random.RandomState,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    ポラロイド/チェキの「ポリマーコート紙・シルク/リネン微細エンボス」を生成する。
    緻密なマット／シルク調エンボス凹凸を法線勾配（Bump Mapping）で計算（高速化版）。
    """
    hs1, ws1 = max(16, int(h * 0.72)), max(16, int(w * 0.72))
    n1 = rng.normal(0.0, 1.0, (hs1, ws1)).astype(np.float32)
    p1 = Image.fromarray(np.clip((n1 / 5.5 + 0.5) * 255.0, 0, 255).astype(np.uint8), mode="L")
    a1 = np.array(p1.resize((w, h), Image.Resampling.BILINEAR), dtype=np.float32)

    hs2, ws2 = max(12, int(h * 0.42)), max(12, int(w * 0.42))
    n2 = rng.normal(0.0, 1.0, (hs2, ws2)).astype(np.float32)
    p2 = Image.fromarray(np.clip((n2 / 5.5 + 0.5) * 255.0, 0, 255).astype(np.uint8), mode="L")
    a2 = np.array(p2.resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32)

    hx, wx = max(16, int(h * 0.80)), max(16, int(w * 0.25))
    nx = rng.normal(0.0, 1.0, (hx, wx)).astype(np.float32)
    px = Image.fromarray(np.clip((nx / 5.5 + 0.5) * 255.0, 0, 255).astype(np.uint8), mode="L")
    ax = np.array(px.resize((w, h), Image.Resampling.BILINEAR), dtype=np.float32)

    hy, wy = max(16, int(h * 0.25)), max(16, int(w * 0.80))
    ny = rng.normal(0.0, 1.0, (hy, wy)).astype(np.float32)
    py = Image.fromarray(np.clip((ny / 5.5 + 0.5) * 255.0, 0, 255).astype(np.uint8), mode="L")
    ay = np.array(py.resize((w, h), Image.Resampling.BILINEAR), dtype=np.float32)

    hm, wm = max(8, int(h / 7.0)), max(8, int(w / 7.0))
    nm = rng.normal(0.0, 1.0, (hm, wm)).astype(np.float32)
    pm = Image.fromarray(np.clip((nm / 5.5 + 0.5) * 255.0, 0, 255).astype(np.uint8), mode="L")
    am = np.array(pm.resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32)

    combined = a1 * 0.45
    combined += a2 * 0.25
    combined += (ax + ay) * 0.15
    combined += am * 0.15
    emboss_height = _norm_std(combined)

    light_angle = math.radians(-132.0 + rng.uniform(-12.0, 12.0))
    lx, ly = math.cos(light_angle), math.sin(light_angle)

    # 高速中央差分（フルサイズ np.gradient 2枚の中間メモリ確保を排除）
    diff_x = np.empty_like(emboss_height)
    diff_x[:, 1:-1] = (emboss_height[:, 2:] - emboss_height[:, :-2]) * 0.5
    diff_x[:, 0] = emboss_height[:, 1] - emboss_height[:, 0]
    diff_x[:, -1] = emboss_height[:, -1] - emboss_height[:, -2]

    diff_y = np.empty_like(emboss_height)
    diff_y[1:-1, :] = (emboss_height[2:, :] - emboss_height[:-2, :]) * 0.5
    diff_y[0, :] = emboss_height[1, :] - emboss_height[0, :]
    diff_y[-1, :] = emboss_height[-1, :] - emboss_height[-2, :]

    emboss_relief = _norm_std(diff_x * lx + diff_y * ly)
    return emboss_relief, emboss_height


def _generate_scanned_instant_paper(
    canvas_h: int,
    canvas_w: int,
    win_box: Tuple[int, int, int, int],
    paper_tone: Dict[str, Any],
    texture_strength: float,  # 0.0 〜 1.0 (スライダー連動)
    seed: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    印画紙キャンバス (canvas_h, canvas_w, 3) と 微細エンボス高さマップ を生成。
    マテリアル質感（滑らかな工業カード感）と エイジング劣化（黄ばみ・カビ・繊維）を二重分離した設計。
    texture_strength (0.0〜1.0):
      - 0.0: 完全デジタルフラット枠（テクスチャ無効）
      - 0.30: 【デフォルト】滑らかで清潔なポリマー印画紙（ダイカット断面・サテン光沢・アゴ立体感、黄ばみ/カビ/繊維ゼロ）
      - 0.50: 本物感・清潔な白枠と立体感・微光沢が調和した標準印画紙カード
      - 0.75: 自然な保管経年感（わずかな日焼け・微小チリ）
      - 1.00: 【極限ヴィンテージ】数十年の強い酸化日焼け・薬液浸透染み・フォクシング斑点・反り
    """
    rng = np.random.RandomState((seed * 747796405 + 2891336453) & 0xFFFFFFFF)
    py_rng = random.Random((seed + 98765) & 0xFFFFFFFF)

    win_x0, win_y0, win_x1, win_y1 = win_box
    win_w = win_x1 - win_x0
    win_h = win_y1 - win_y0
    m_side = win_x0
    m_top = win_y0
    m_bottom = canvas_h - win_y1

    raw_base_rgb = np.array(paper_tone["rgb"], dtype=np.float32) / 255.0
    is_dark = bool(paper_tone.get("dark", False))
    tone_grain_mul = float(paper_tone.get("grain", 2.0)) / 2.0

    eff_s = float(np.clip(texture_strength, 0.0, 1.0))
    if eff_s <= 0.001:
        flat = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)
        flat[:, :] = raw_base_rgb
        return flat, np.zeros((canvas_h, canvas_w), dtype=np.float32)

    # =========================================================================
    # カーブの二重分離設計（改善版）:
    # 1. struct_curve: 物理カードのマテリアル感（立体感・ダイカット・サテン光沢・アゴ構造）
    # 2. aging_curve: 経年劣化（黄ばみ・カビ斑点・薬液染み・波打ち・繊維くず）
    #    0〜100 でリニアかつ美しく紙質とエイジングが立ち上がる滑らかな連続関数
    # =========================================================================
    struct_curve = eff_s ** 0.70

    if eff_s <= 0.08:
        aging_curve = 0.0
    else:
        aging_curve = ((eff_s - 0.08) / 0.92) ** 1.35

    # 白枠の暗化（グレー化）防止をしつつ、自然な温かみとエイジングを付与
    if not is_dark:
        base_rgb = raw_base_rgb - (0.006 * struct_curve + 0.045 * aging_curve)
    else:
        base_rgb = raw_base_rgb + (0.015 * eff_s)

    y_px = np.arange(canvas_h, dtype=np.float32)[:, None]
    x_px = np.arange(canvas_w, dtype=np.float32)[None, :]
    yy = y_px / max(1.0, float(canvas_h - 1))
    xx = x_px / max(1.0, float(canvas_w - 1))

    # 1. 工業的立体構造 (3D Geometry: 薬液ポッド・外枠プレス)
    chin_y = np.clip((y_px - win_y1) / max(1.0, float(m_bottom)), 0.0, 1.0)
    in_chin = (y_px >= win_y1).astype(np.float32)

    pod_dome_y = np.sin(chin_y * math.pi) ** 1.15
    pod_slope_light = np.cos(chin_y * math.pi) * (np.sin(chin_y * math.pi) ** 0.45) * in_chin

    trap_top_crease = -np.exp(-((chin_y - 0.042) / 0.022) ** 2) * in_chin
    trap_top_ridge = 0.60 * np.exp(-((chin_y - 0.080) / 0.030) ** 2) * in_chin

    seam_jitter_l = rng.uniform(-1.5, 1.5)
    seam_jitter_r = rng.uniform(-1.5, 1.5)
    seam_w = max(2.0, m_side * 0.10)
    crease_l = -np.exp(-((x_px - (win_x0 + seam_jitter_l)) / seam_w) ** 2) + 0.55 * np.exp(
        -((x_px - (win_x0 + seam_jitter_l + seam_w * 0.85)) / seam_w) ** 2
    )
    crease_r = -np.exp(-((x_px - (win_x1 + seam_jitter_r)) / seam_w) ** 2) - 0.55 * np.exp(
        -((x_px - (win_x1 + seam_jitter_r + seam_w * 0.85)) / seam_w) ** 2
    )

    pod_center_norm = (x_px - win_x0) / max(1.0, float(win_w))
    pod_dome_x = np.clip(np.sin(np.clip(pod_center_norm, 0.0, 1.0) * math.pi), 0.0, 1.0) ** 0.6
    pod_bias = 1.0 + rng.uniform(-0.15, 0.15) * (pod_center_norm - 0.5)

    # 薬液ポッドの立体感（視認性向上）
    chin_3d_shading = in_chin * (
        0.024 * pod_slope_light * pod_dome_x * pod_bias
        + 0.015 * (pod_dome_y * pod_dome_x - 0.35)
        + 0.022 * (trap_top_crease + trap_top_ridge) * pod_dome_x
        + 0.016 * (crease_l + crease_r) * (pod_dome_y ** 0.6)
    )

    dist_left = x_px
    dist_right = (canvas_w - 1) - x_px
    dist_top = y_px
    dist_bot = (canvas_h - 1) - y_px
    dist_outer = np.minimum(np.minimum(dist_left, dist_right), np.minimum(dist_top, dist_bot))

    d_max = int(dist_outer.max()) + 1
    d_outer_1d = np.arange(d_max, dtype=np.float32)
    outer_idx = dist_outer.astype(np.int32)

    outer_bevel_lut = -0.040 * np.exp(-d_outer_1d / max(1.8, m_side * 0.06))
    seal_pos = max(4.0, m_side * 0.20)
    seal_w = max(1.2, m_side * 0.035)
    heat_seal_lut = -0.014 * np.exp(-((d_outer_1d - seal_pos) / seal_w) ** 2) + 0.010 * np.exp(
        -((d_outer_1d - (seal_pos + seal_w * 1.1)) / seal_w) ** 2
    )

    outer_bevel = outer_bevel_lut[outer_idx]
    heat_seal_line = heat_seal_lut[outer_idx]

    dx_win = np.maximum(0.0, np.maximum(win_x0 - x_px, x_px - (win_x1 - 1)))
    dy_win = np.maximum(0.0, np.maximum(win_y0 - y_px, y_px - (win_y1 - 1)))
    bevel_w = max(2.2, m_side * 0.10)
    d_win_max = int(max(canvas_w, canvas_h))
    d_win_grid = np.arange(d_win_max + 1, dtype=np.float32)
    win_bevel_lut = (-0.020 * np.exp(-d_win_grid / bevel_w) + 0.014 * np.exp(
        -((d_win_grid - bevel_w * 1.25) / (bevel_w * 0.75)) ** 2
    )).astype(np.float32)
    dist_from_win_idx = np.sqrt(dx_win * dx_win + dy_win * dy_win).astype(np.int32)
    win_bevel_shade = win_bevel_lut[dist_from_win_idx]

    # 2. 紙の反り（うねり・波打ち）: 劣化要素なので aging_curve 連動 (加法定理による1D分離高速化)
    angle1 = rng.uniform(0, math.pi * 2)
    angle2 = angle1 + rng.uniform(1.0, 2.1)
    phase1 = rng.uniform(0, math.pi * 2)
    phase2 = rng.uniform(0, math.pi * 2)
    freq1 = rng.uniform(1.0, 1.6) * math.pi
    freq2 = rng.uniform(1.6, 2.4) * math.pi

    u1 = xx * (freq1 * math.cos(angle1))
    v1 = yy * (freq1 * math.sin(angle1)) + phase1
    wave1 = np.sin(u1) * np.cos(v1) + np.cos(u1) * np.sin(v1)

    u2 = xx * (freq2 * math.cos(angle2))
    v2 = yy * (freq2 * math.sin(angle2)) + phase2
    wave2 = np.cos(u2) * np.cos(v2) - np.sin(u2) * np.sin(v2)

    macro_curl = _norm_std((wave1 * 0.70 + wave2 * 0.30).astype(np.float32))

    # 3. 滑らかなポリマーコート微細シボ ＆ サテン反射
    emboss_relief, emboss_height = _generate_coated_micro_emboss(canvas_h, canvas_w, rng)
    smooth_density = _generate_smooth_field(canvas_h, canvas_w, rng, grid_div=4)

    sheen_field = _norm_std(0.50 * macro_curl + 0.50 * (chin_3d_shading * 50.0))
    sheen_highlight = np.clip(sheen_field - 0.05, 0.0, 2.0) ** 1.6

    # 4. 合成
    canvas_np = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)
    canvas_np[:, :] = base_rgb

    # 工業構造の立体感
    amp = 0.20 + 0.80 * struct_curve
    grain_amp = amp * (0.80 + 0.20 * tone_grain_mul)

    if not is_dark:
        total_struct = chin_3d_shading + outer_bevel + heat_seal_line + win_bevel_shade
        curl_scale = 0.005 * struct_curve + 0.030 * aging_curve

        luma_mod = total_struct * (1.00 * amp)
        if curl_scale > 0.0:
            luma_mod += macro_curl * curl_scale
        if struct_curve > 0.0:
            luma_mod += smooth_density * (0.008 * struct_curve)
        luma_mod += emboss_relief * (0.022 * grain_amp)
        canvas_np += luma_mod[:, :, None]

        # サテン光沢ハイライト（清潔で高級感のある反射）
        sheen_rgb = np.array([1.0, 0.99, 0.97], dtype=np.float32)
        sheen_mod = max(0.3, 1.0 - 0.3 * aging_curve)
        canvas_np += sheen_highlight[:, :, None] * sheen_rgb * (0.020 * amp * sheen_mod)

        # 外周エッジ＆四隅の酸化・日焼け・黄ばみ (aging_curve 連動)
        if aging_curve > 0.001:
            edge_prox_lut = np.exp(-d_outer_1d / max(14.0, m_side * 0.85))
            edge_prox = edge_prox_lut[outer_idx]
            corner_prox = (np.exp(-dist_left / (canvas_w * 0.28)) + np.exp(-dist_right / (canvas_w * 0.28))) * (
                np.exp(-dist_top / (canvas_h * 0.28)) + np.exp(-dist_bot / (canvas_h * 0.28))
            )
            aging_asym = np.clip(0.60 + 0.55 * _generate_smooth_field(canvas_h, canvas_w, rng, grid_div=3), 0.15, 1.8)
            oxidation_mask = np.clip((edge_prox * 0.60 + corner_prox * 0.55) * aging_asym, 0.0, 2.0)

            aging_tint = np.array([-0.040, -0.095, -0.210], dtype=np.float32)
            is_pure_white = (paper_tone["rgb"] == PAPER_TONES["Pure White"]["rgb"])
            aging_scale = (0.50 if is_pure_white else 0.90 * tone_grain_mul) * (1.20 * aging_curve)
            canvas_np += oxidation_mask[:, :, None] * aging_tint * aging_scale

            # 薬液ポッドの経年化学浸透染み
            pod_stain_tint = np.array([-0.025, -0.060, -0.125], dtype=np.float32)
            pod_bleed_asym = 0.7 + 0.3 * np.sin(x_px / 40.0 + seed)
            canvas_np += (in_chin * (pod_dome_y ** 1.3) * pod_dome_x * pod_bleed_asym)[:, :, None] * pod_stain_tint * (
                1.20 * aging_curve * tone_grain_mul
            )

        # フォクシング・経年斑点 (aging_curve が 0.15 を超えたヴィンテージ領域)
        if aging_curve > 0.15:
            foxing_noise = np.clip(_generate_smooth_field(canvas_h, canvas_w, rng, grid_div=6) - 0.25, 0.0, 2.0)
            foxing_tint = np.array([-0.020, -0.040, -0.080], dtype=np.float32)
            canvas_np += foxing_noise[:, :, None] * foxing_tint * (aging_curve * 1.10 * tone_grain_mul)

    else:
        # Matte Black (黒枠)
        total_struct = chin_3d_shading + outer_bevel * 0.6 + heat_seal_line + win_bevel_shade
        luma_mod = total_struct * (1.00 * amp)
        luma_mod += macro_curl * (0.008 * struct_curve + 0.020 * aging_curve)
        luma_mod += emboss_relief * (0.022 * grain_amp)
        luma_mod += sheen_highlight * (0.025 * amp)
        canvas_np += luma_mod[:, :, None]
        if aging_curve > 0.001:
            edge_wear_lut = np.exp(-d_outer_1d / max(4.0, m_side * 0.25))
            edge_wear = edge_wear_lut[outer_idx]
            corner_wear = (np.exp(-dist_left / 20.0) + np.exp(-dist_right / 20.0)) * (np.exp(-dist_top / 20.0) + np.exp(-dist_bot / 20.0))
            canvas_np += (edge_wear * 0.6 + corner_wear * 0.8)[:, :, None] * (0.100 * aging_curve)

    # 5. 微細繊維・チリ（本数を適切に管理し、自然な紙質を表現）
    canvas_np = np.clip(canvas_np, 0.0, 1.0)
    
    # 繊維はエイジング劣化時（aging_curve > 0.02）から自然に発生
    if aging_curve > 0.02:
        detail_layer = Image.new("L", (canvas_w, canvas_h), 0)
        draw_det = ImageDraw.Draw(detail_layer)

        num_fibers = int(round((canvas_w * canvas_h) / 36000.0 * (struct_curve * 0.4 + aging_curve * 0.6) * tone_grain_mul))
        for _ in range(num_fibers):
            fx = py_rng.uniform(0, canvas_w - 1)
            fy = py_rng.uniform(0, canvas_h - 1)
            if win_x0 <= fx <= win_x1 and win_y0 <= fy <= win_y1:
                continue
            f_len = py_rng.uniform(2.5, 5.5)
            f_ang = py_rng.uniform(0, math.pi * 2)
            xm = fx + math.cos(f_ang) * (f_len * 0.5) + py_rng.uniform(-0.5, 0.5)
            ym = fy + math.sin(f_ang) * (f_len * 0.5) + py_rng.uniform(-0.5, 0.5)
            fx2 = fx + math.cos(f_ang) * f_len
            fy2 = fy + math.sin(f_ang) * f_len

            alpha = int(py_rng.uniform(10, 24) * min(1.2, aging_curve * 1.5))
            draw_det.line([(fx, fy), (xm, ym), (fx2, fy2)], fill=alpha, width=1)

        # チリ（スキャナーの微小ダスト）
        num_specks = int(round((canvas_w * canvas_h) / 30000.0 * (0.05 * struct_curve + aging_curve)))
        for _ in range(num_specks):
            sx = py_rng.randint(0, canvas_w - 1)
            sy = py_rng.randint(0, canvas_h - 1)
            if win_x0 <= sx <= win_x1 and win_y0 <= sy <= win_y1:
                continue
            alpha = int(py_rng.uniform(8, 20) * min(1.2, 0.2 * struct_curve + aging_curve))
            draw_det.point((sx, sy), fill=alpha)

        detail_layer = detail_layer.filter(ImageFilter.GaussianBlur(radius=0.35))
        det_a = np.array(detail_layer, dtype=np.float32)[:, :, None] * (1.0 / 255.0)
        dust_rgb = np.array([125 / 255.0, 105 / 255.0, 80 / 255.0] if not is_dark else [200 / 255.0, 195 / 255.0, 190 / 255.0], dtype=np.float32)
        canvas_np = canvas_np * (1.0 - det_a) + dust_rgb * det_a

    # 6. 内窓ダイカット断面
    rim_px = max(2, int(round(min(win_w, win_h) * 0.0045)))
    if not is_dark:
        for r in range(1, rim_px + 1):
            w_f = ((rim_px + 1 - r) / rim_px) * 0.035 * amp
            if win_y0 - r >= 0:
                canvas_np[win_y0 - r, win_x0:win_x1, :] -= w_f
            if win_x0 - r >= 0:
                canvas_np[win_y0:win_y1, win_x0 - r, :] -= w_f * 0.85
        for r in range(rim_px):
            w_f = ((rim_px - r) / rim_px) * 0.045 * amp
            if win_y1 + r < canvas_h:
                canvas_np[win_y1 + r, win_x0:win_x1, :] += w_f
            if win_x1 + r < canvas_w:
                canvas_np[win_y0:win_y1, win_x1 + r, :] += w_f * 0.85
    else:
        for r in range(rim_px):
            w_f = ((rim_px - r) / rim_px) * 0.065 * amp
            if win_y1 + r < canvas_h:
                canvas_np[win_y1 + r, win_x0:win_x1, :] += w_f
            if win_x1 + r < canvas_w:
                canvas_np[win_y0:win_y1, win_x1 + r, :] += w_f * 0.85

    return np.clip(canvas_np, 0.0, 1.0), emboss_height


def _composite_text_with_paper_grain(
    pil_canvas: Image.Image,
    text_layer: Image.Image,
    pos: Tuple[int, int],
    emboss_height: np.ndarray,
    texture_strength: float,
) -> None:
    """
    手書き文字レイヤーを紙面に合成する際、印画紙の微細シボに応じてインクの乗りを変調する。
    """
    tx, ty = pos
    tw, th = text_layer.size
    ch, cw = emboss_height.shape

    x0 = max(0, tx)
    y0 = max(0, ty)
    x1 = min(cw, tx + tw)
    y1 = min(ch, ty + th)
    if x1 <= x0 or y1 <= y0:
        return

    sub_text = text_layer.crop((x0 - tx, y0 - ty, x1 - tx, y1 - ty))
    t_arr = np.array(sub_text, dtype=np.float32) / 255.0
    sub_h = emboss_height[y0:y1, x0:x1]

    aging_fade = max(0.68, 1.0 - 0.25 * (texture_strength ** 1.5))
    grain_mod = np.clip(1.0 + sub_h * (0.16 * texture_strength), 0.70, 1.10) * aging_fade
    t_arr[:, :, 3] = np.clip(t_arr[:, :, 3] * grain_mod, 0.0, 1.0)

    mod_layer = Image.fromarray((t_arr * 255.0).astype(np.uint8), mode="RGBA")
    pil_canvas.alpha_composite(mod_layer, (x0, y0))


@functools.lru_cache(maxsize=32)
def _get_font_supported_chars(font_file: str) -> Set[int]:
    """
    TTF / OTF ファイルの cmap テーブルをパースし、
    フォントが収録している Unicode コードポイントの集合 (Set[int]) を返す。
    外部ライブラリ非依存（Python標準ライブラリ struct のみで高速動作）。
    """
    font_path = os.path.join(FONTS_DIR, font_file)
    if not os.path.exists(font_path):
        return set()

    chars: Set[int] = set()
    try:
        with open(font_path, "rb") as f:
            sfnt_version = f.read(4)
            num_tables, = struct.unpack(">H", f.read(2))
            f.seek(12)
            cmap_offset = None
            for _ in range(num_tables):
                tag = f.read(4)
                _, offset, _ = struct.unpack(">III", f.read(12))
                if tag == b"cmap":
                    cmap_offset = offset
                    break
            if not cmap_offset:
                return chars

            f.seek(cmap_offset)
            _, num_subtables = struct.unpack(">HH", f.read(4))
            subtables = []
            for _ in range(num_subtables):
                platform_id, encoding_id, offset = struct.unpack(">HHI", f.read(8))
                subtables.append((platform_id, encoding_id, cmap_offset + offset))

            for _, _, sub_offset in subtables:
                f.seek(sub_offset)
                format_num, = struct.unpack(">H", f.read(2))
                if format_num == 4:
                    _, _, seg_count_x2 = struct.unpack(">HHH", f.read(6))
                    seg_count = seg_count_x2 // 2
                    f.seek(sub_offset + 14)
                    end_codes = struct.unpack(f">{seg_count}H", f.read(seg_count * 2))
                    f.seek(sub_offset + 14 + seg_count * 2 + 2)
                    start_codes = struct.unpack(f">{seg_count}H", f.read(seg_count * 2))
                    id_deltas = struct.unpack(f">{seg_count}h", f.read(seg_count * 2))
                    id_range_offsets_pos = f.tell()
                    id_range_offsets = struct.unpack(f">{seg_count}H", f.read(seg_count * 2))
                    for i in range(seg_count):
                        s = start_codes[i]
                        e = end_codes[i]
                        if s == 0xFFFF:
                            break
                        if id_range_offsets[i] == 0:
                            for c in range(s, e + 1):
                                if (c + id_deltas[i]) & 0xFFFF != 0:
                                    chars.add(c)
                        else:
                            for c in range(s, e + 1):
                                off = id_range_offsets_pos + i * 2 + id_range_offsets[i] + (c - s) * 2
                                f.seek(off)
                                glyph_index, = struct.unpack(">H", f.read(2))
                                if glyph_index != 0 and (glyph_index + id_deltas[i]) & 0xFFFF != 0:
                                    chars.add(c)
                elif format_num == 12:
                    f.seek(sub_offset + 12)
                    num_groups, = struct.unpack(">I", f.read(4))
                    for _ in range(num_groups):
                        start_char, end_char, _ = struct.unpack(">III", f.read(12))
                        for c in range(start_char, end_char + 1):
                            chars.add(c)
    except Exception:
        pass
    return chars


@functools.lru_cache(maxsize=128)
def _get_font_by_file(font_file: str, font_size: int) -> ImageFont.FreeTypeFont:
    """フォントファイル名とサイズからフォントオブジェクトを取得"""
    font_path = os.path.join(FONTS_DIR, font_file)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass
    # フォールバック
    fallback_path = os.path.join(FONTS_DIR, FALLBACK_FONT_FILE)
    if os.path.exists(fallback_path):
        try:
            return ImageFont.truetype(fallback_path, font_size)
        except Exception:
            pass
    return ImageFont.load_default()


def _measure_char_width(char: str, font: ImageFont.FreeTypeFont) -> float:
    """1文字の横幅 (px) を計測"""
    try:
        return font.getlength(char)
    except Exception:
        bbox = font.getbbox(char)
        return float(bbox[2] - bbox[0]) if bbox else float(font.size * 0.5)


def _measure_text_width(
    text: str,
    primary_font_file: str,
    primary_size: int,
    fallback_font_file: str = FALLBACK_FONT_FILE,
    fallback_size: Optional[int] = None,
) -> float:
    """
    混植（フォールバック）を考慮してテキスト全体の横幅 (px) を計測する。
    """
    clean_text = text.strip()
    if not clean_text:
        return 0.0

    if fallback_size is None:
        fb_norm = get_font_norm_factor(fallback_font_file)
        primary_norm = get_font_norm_factor(primary_font_file)
        fb_size = max(8, int(round(primary_size * (fb_norm / max(0.5, primary_norm)))))
    else:
        fb_size = fallback_size

    primary_chars = _get_font_supported_chars(primary_font_file)
    fallback_chars = _get_font_supported_chars(fallback_font_file)
    p_font = _get_font_by_file(primary_font_file, primary_size)
    f_font = _get_font_by_file(fallback_font_file, fb_size)

    total_w = 0.0
    for char in clean_text:
        c_code = ord(char)
        if primary_chars and (c_code in primary_chars):
            total_w += _measure_char_width(char, p_font)
        elif (not fallback_chars) or (c_code in fallback_chars):
            total_w += _measure_char_width(char, f_font)
        else:
            # どちらのフォントにも無い文字（絵文字等）は未定義豆腐描画を防ぐため幅計測から除外
            continue
    return total_w


def _classify_char(ch: str) -> str:
    """文字種を判定: 'kanji', 'kana', 'punct', 'other'"""
    code = ord(ch)
    if (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF):
        return "kanji"
    if (0x3040 <= code <= 0x309F) or (0x30A0 <= code <= 0x30FF):
        return "kana"
    if ch in "!?:;\"'.,~!?！？♡♥☆★♪〜・…":
        return "punct"
    return "other"


def _auto_fit_font_and_text(
    text: str,
    primary_font_file: str,
    base_font_size: int,
    max_w: float,
    max_h: float,
    fallback_font_file: str = FALLBACK_FONT_FILE,
    min_size: int = 7,
    wobble_strength: float = 0.5,
    font_kinematics: Optional[Dict[str, float]] = None,
) -> Tuple[int, str]:
    """
    指定の矩形 (max_w, max_h) に収まるよう、
    フォントサイズを自動縮小 (Auto-fit) し、最小サイズでも溢れる場合は安全に末尾省略する。
    Returns:
        (cur_size, clean_text)
    """
    clean_text = text.strip()
    if not clean_text or max_w <= 0 or max_h <= 0:
        return base_font_size, clean_text

    cur_size = base_font_size
    w = max(0.0, min(1.0, float(wobble_strength)))
    kin = font_kinematics or {}
    dx_mul = kin.get("dx_mul", 1.0)
    tilt_mul = kin.get("tilt_mul", 1.0)

    # 余裕（回転・ジッター・パディング・字間）を見込んだ推定幅
    pad_extra = max(6, int(cur_size * (0.35 + 0.12 * dx_mul * w)))
    text_w = _measure_text_width(clean_text, primary_font_file, cur_size, fallback_font_file) + pad_extra

    # 幅オーバー時の縮小
    if text_w > max_w:
        w_without_pad = max(1.0, _measure_text_width(clean_text, primary_font_file, cur_size, fallback_font_file))
        scale_w = max(0.05, (max_w - pad_extra) / w_without_pad)
        cur_size = max(min_size, int(cur_size * scale_w))

    # 高さオーバー時の縮小（行傾斜による見込み縦膨張も考慮）
    line_h = cur_size * (1.30 + 0.10 * tilt_mul * w)
    if line_h > max_h:
        scale_h = max(0.05, max_h / max(1.0, line_h))
        cur_size = max(min_size, int(cur_size * scale_h))

    # 最小サイズでも max_w を超える超長文の場合は末尾省略（Ellipsis）
    pad_extra = max(4, int(cur_size * 0.25))
    available_text_w = max_w - pad_extra
    if _measure_text_width(clean_text, primary_font_file, cur_size, fallback_font_file) > available_text_w:
        ell = "…"
        ell_w = _measure_text_width(ell, primary_font_file, cur_size, fallback_font_file)
        trimmed = clean_text
        while len(trimmed) > 1 and (_measure_text_width(trimmed, primary_font_file, cur_size, fallback_font_file) + ell_w) > available_text_w:
            trimmed = trimmed[:-1]
        clean_text = trimmed + ell

    return cur_size, clean_text


def _render_handwritten_text_layer(
    text: str,
    primary_font_file: str,
    font_size: int,
    ink_rgb: Tuple[int, int, int],
    ink_profile: Dict[str, Any],
    fallback_font_file: str = FALLBACK_FONT_FILE,
    seed: int = 0,
    wobble_strength: float = 0.5,
    max_tilt_deg: Optional[float] = None,
    is_date: bool = False,
) -> Optional[Image.Image]:
    """
    混植（フォールバック）対応の余白手書き文字レイヤーレンダリング。
    主フォントにグリフが無い文字（漢字など）は自動的に全水準網羅のフォールバックフォントで描画。
    wobble_strength (0.0〜1.0) に応じて、手首実寸ピボット曲線・AR(1)慣性ドリフト・文字種別リズム・筆記速度インク変調・行傾斜を変調。
    """
    clean_text = text.strip()
    if not clean_text:
        return None

    w = max(0.0, min(1.0, float(wobble_strength)))
    rng = random.Random(seed & 0xFFFFFFFF)
    np_rng = np.random.RandomState(seed & 0xFFFFFFFF)

    pen_type = ink_profile.get("pen_type", "marker")
    base_opacity = int(round(255 * ink_profile.get("opacity", 0.95)))
    bleed_radius = float(ink_profile.get("bleed_radius", 0.5))
    unevenness = float(ink_profile.get("unevenness", 0.15))
    glitter = float(ink_profile.get("glitter", 0.0))

    # 書体・ペン種別キネマティクスプロファイルの解決
    kinematics = get_handwriting_kinematics(primary_font_file, pen_type=pen_type)
    arc_mul = kinematics.get("arc_mul", 1.0)
    rot_mul = kinematics.get("rot_mul", 1.0)
    dy_mul = kinematics.get("dy_mul", 1.0)
    dx_mul = kinematics.get("dx_mul", 1.0)
    scale_mul = kinematics.get("scale_mul", 1.0)
    tilt_mul = kinematics.get("tilt_mul", 1.0)

    # 日付モード (is_date=True): 数字列の安定した記録のため、アークとジッターを上品に引き締める
    if is_date:
        arc_mul *= 0.25
        rot_mul *= 0.55
        dy_mul *= 0.55
        dx_mul *= 0.50
        scale_mul *= 0.40
        tilt_mul = min(tilt_mul, 0.60)

    # 主フォントとフォールバックフォントの準備
    primary_chars = _get_font_supported_chars(primary_font_file)
    fallback_chars = _get_font_supported_chars(fallback_font_file)
    p_font = _get_font_by_file(primary_font_file, font_size)

    # フォールバックフォントの正規化係数に応じたサイズ調整
    fb_norm = get_font_norm_factor(fallback_font_file)
    primary_norm = get_font_norm_factor(primary_font_file)
    fb_size = max(8, int(round(font_size * (fb_norm / max(0.5, primary_norm)))))
    f_font = _get_font_by_file(fallback_font_file, fb_size)

    try:
        ascent, descent = p_font.getmetrics()
    except Exception:
        ascent = int(font_size * 0.8)
        descent = int(font_size * 0.2)

    extra_pad_y = max(10, int(round(font_size * 0.65 * w + 10)))
    line_h_ref = ascent + descent + max(14, int(font_size * 0.4)) + extra_pad_y * 2
    base_y_offset = extra_pad_y + max(6, int(font_size * 0.2))

    # 1. 混植判定と送り幅の先行スキャン (物理距離計算用)
    parsed_chars = []
    total_advance = 0.0
    for char in clean_text:
        c_code = ord(char)
        if primary_chars and (c_code in primary_chars):
            cur_font = p_font
        elif (not fallback_chars) or (c_code in fallback_chars):
            cur_font = f_font
        else:
            # 未収録文字（絵文字等）は安全にスキップ
            continue

        try:
            adv = float(cur_font.getlength(char))
        except Exception:
            bb = cur_font.getbbox(char)
            adv = float(bb[2] - bb[0]) if bb else float(cur_font.size * 0.5)

        is_sp = char.isspace()
        bb = cur_font.getbbox(char) if not is_sp else None
        c_type = _classify_char(char)
        parsed_chars.append({
            "char": char,
            "font": cur_font,
            "advance": adv,
            "bbox": bb,
            "is_space": is_sp,
            "type": c_type,
            "cum_x": total_advance,
        })
        total_advance += adv

    if not parsed_chars or total_advance <= 0:
        return None

    # 2. 手首ピボット曲線パラメータ (実寸スパン & 短文減衰ゲート)
    # 人間の手首の自然可動域: 約8.5文字分の物理横幅
    wrist_span = max(float(font_size) * 8.5, 120.0)
    # 2〜3文字以下の短文では手首の回転弧が生じないよう滑らかに減衰 (0.0〜1.0)
    len_gate = max(0.0, min(1.0, (total_advance - font_size * 0.8) / max(1.0, font_size * 2.8)))

    arc_amp = rng.uniform(-0.14, 0.14)
    wave_amp = rng.uniform(-0.05, 0.05)
    wave_phase = rng.uniform(0.0, math.pi * 2)

    # 1次自己相関 (AR(1)) 運動慣性状態
    ar_dy = 0.0
    ar_rot = 0.0
    ar_scale = 0.0

    char_images = []
    total_w = 0
    max_h = 0

    for item in parsed_chars:
        char = item["char"]
        cur_font = item["font"]
        adv = item["advance"]
        bbox = item["bbox"]
        c_type = item["type"]
        is_sp = item["is_space"]

        # 空白文字: ペンが浮くため運動慣性を大幅緩和リセット
        if is_sp:
            ar_dy *= 0.25
            ar_rot *= 0.25
            ar_scale *= 0.25
            space_w = max(4, int(round(adv)))
            char_images.append((None, space_w, 0.0))
            total_w += space_w
            continue

        if bbox is None or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            space_w = max(4, int(cur_font.size * 0.32))
            char_images.append((None, space_w, 0.0))
            total_w += space_w
            continue

        # 実寸物理スパンに基づく無次元距離 u (-0.5〜0.5 付近)
        char_cx = item["cum_x"] + adv * 0.5
        u = (char_cx - total_advance * 0.5) / wrist_span

        # 手首アーク曲線 dy と 接線角の計算
        if w > 0.001 and len_gate > 0.0:
            curve_dy = (arc_amp * (u ** 2) + wave_amp * math.sin(math.pi * u * 1.5 + wave_phase)) * float(font_size) * w * arc_mul * len_gate
            d_dy_dx = (2.0 * arc_amp * u + wave_amp * (math.pi * 1.5) * math.cos(math.pi * u * 1.5 + wave_phase)) * (float(font_size) / wrist_span) * w * arc_mul * len_gate
            tangent_deg = math.degrees(math.atan(d_dy_dx))
        else:
            curve_dy = 0.0
            tangent_deg = 0.0

        # AR(1) 運動ドリフト更新 (前の文字からの慣性)
        ar_dy = 0.55 * ar_dy + 0.45 * rng.uniform(-1.0, 1.0)
        ar_rot = 0.45 * ar_rot + 0.55 * rng.uniform(-1.0, 1.0)
        ar_scale = 0.50 * ar_scale + 0.50 * rng.uniform(-1.0, 1.0)

        # 文字種別リズム調整
        if c_type == "kanji":
            rot_mod = 0.75
            dy_mod = 0.75
            scale_add = 0.015 * w
        elif c_type == "kana":
            rot_mod = 1.00
            dy_mod = 1.00
            scale_add = -0.015 * w
        elif c_type == "punct":
            rot_mod = 1.35
            dy_mod = 1.25
            scale_add = 0.030 * w
        else:
            rot_mod = 1.00
            dy_mod = 1.00
            scale_add = 0.0

        # 最終回転角・上下オフセット・字間・字粒スケール
        if w > 0.001:
            char_rot = tangent_deg + ar_rot * 2.2 * rot_mod * rot_mul * w
            char_dy = curve_dy + ar_dy * (0.035 * float(font_size)) * dy_mod * dy_mul * w
            char_dx = rng.uniform(-0.025, 0.030) * float(font_size) * dx_mul * w
            char_scale = max(0.85, min(1.15, 1.0 + (ar_scale * 0.035 * scale_mul + scale_add) * w))
        else:
            char_rot = 0.0
            char_dy = 0.0
            char_dx = 0.0
            char_scale = 1.0

        pad_x = max(8, int(cur_font.size * 0.40))
        gw = bbox[2] - bbox[0]
        cw = max(int(round(adv)), gw) + pad_x * 2
        ch = line_h_ref

        tmp_img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp_img)
        draw_x = pad_x - bbox[0]
        draw_y = base_y_offset
        tmp_draw.text((draw_x, draw_y), char, fill=(*ink_rgb, base_opacity), font=cur_font)

        # グリフのベースライン中央 (glyph_cx, glyph_base_y) をピボットとして回転
        glyph_cx = draw_x + (bbox[0] + bbox[2]) * 0.5
        glyph_base_y = base_y_offset + ascent

        if abs(char_rot) > 0.08:
            tmp_img = tmp_img.rotate(char_rot, resample=Image.Resampling.BICUBIC, expand=False, center=(glyph_cx, glyph_base_y))

        # ベースライン中心の微小字粒スケール
        if abs(char_scale - 1.0) > 0.012:
            new_w = max(2, int(round(cw * char_scale)))
            new_h = max(2, int(round(ch * char_scale)))
            resized = tmp_img.resize((new_w, new_h), resample=Image.Resampling.BICUBIC)
            off_x = int(round((new_w - cw) * (glyph_cx / max(1.0, float(cw)))))
            off_y = int(round((new_h - ch) * (glyph_base_y / max(1.0, float(ch)))))
            tmp_img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            tmp_img.paste(resized, (-off_x, -off_y))

        step_w = max(2, int(round(adv + char_dx)))
        total_w += step_w
        max_h = max(max_h, ch)
        char_images.append((tmp_img, step_w, char_dy))

    if not char_images or total_w <= 0:
        return None

    # フォントサイズとジッター/インク滲みに応じた十分な動的マージン
    margin_x = max(40, int(font_size * 1.5))
    margin_y = max(40, int(font_size * 1.0))
    line_w = total_w + margin_x * 2
    line_h = max_h + margin_y * 2
    line_canvas = Image.new("RGBA", (line_w, line_h), (0, 0, 0, 0))

    curr_x = margin_x
    for img_c, step_w, dy in char_images:
        if img_c is not None:
            paste_x = int(round(curr_x))
            paste_y = int(round(margin_y + dy))
            line_canvas.alpha_composite(img_c, (paste_x, paste_y))
        curr_x += step_w

    arr = np.array(line_canvas, dtype=np.float32) / 255.0
    alpha = arr[:, :, 3]

    if np.any(alpha > 0.05):
        h_arr, w_arr = alpha.shape
        # 筆記速度連動の濃度・筆圧ムラ
        eff_unevenness = unevenness * (0.80 + 0.45 * w)
        if eff_unevenness > 0:
            noise_map = np_rng.uniform(1.0 - eff_unevenness, 1.0 + eff_unevenness * 0.5, alpha.shape).astype(np.float32)
            if pen_type == "ballpoint":
                scratch_amp = 0.70 - 0.15 * w
                scratch = np_rng.uniform(scratch_amp, 1.05, alpha.shape).astype(np.float32)
                alpha = alpha * scratch
            for c in range(3):
                arr[:, :, c] = np.clip(arr[:, :, c] * noise_map, 0.0, 1.0)

        # 筆記速度による横方向の微細筆圧グラデーション (書き始めが濃く、書き終わりにかけてわずかに抜ける)
        if w > 0.05 and pen_type != "stamp":
            grad_x = np.linspace(1.02, 0.96, w_arr, dtype=np.float32)[None, :]
            alpha = np.clip(alpha * (1.0 - 0.05 * w + 0.05 * w * grad_x), 0.0, 1.0)

        # ゴム印 (stamp) の片当たり印圧ムラ (左右または上下の押しムラ)
        if pen_type == "stamp" and w > 0.02:
            stamp_slant_x = rng.uniform(-0.15, 0.15) * w
            stamp_slant_y = rng.uniform(-0.12, 0.12) * w
            gx = np.linspace(-1.0, 1.0, w_arr, dtype=np.float32)[None, :]
            gy = np.linspace(-1.0, 1.0, h_arr, dtype=np.float32)[:, None]
            stamp_mod = np.clip(1.0 + gx * stamp_slant_x + gy * stamp_slant_y, 0.72, 1.15)
            alpha = np.clip(alpha * stamp_mod, 0.0, 1.0)

        if glitter > 0 and pen_type == "metallic":
            glitter_noise = (np_rng.uniform(0.0, 1.0, alpha.shape) > 0.88).astype(np.float32)
            sparkle = glitter_noise * glitter * alpha
            for c in range(3):
                arr[:, :, c] = np.clip(arr[:, :, c] + sparkle, 0.0, 1.0)

        if bleed_radius > 0 and pen_type in ("marker", "stamp"):
            alpha_pil = Image.fromarray((alpha * 255.0).astype(np.uint8), mode="L")
            bleed_alpha = alpha_pil.filter(ImageFilter.GaussianBlur(radius=bleed_radius))
            alpha_out = np.maximum(alpha, np.array(bleed_alpha, dtype=np.float32) / 255.0 * 0.45)
            arr[:, :, 3] = np.clip(alpha_out, 0.0, 1.0)
        else:
            arr[:, :, 3] = np.clip(alpha, 0.0, 1.0)

        line_canvas = Image.fromarray((arr * 255.0).astype(np.uint8), mode="RGBA")

    # 行全体の傾き（wobble_strength & tilt_mul 連動 & 上限角度クランプ）
    raw_tilt = rng.uniform(-2.8, 2.8) * w * tilt_mul if w > 0.001 else 0.0
    if max_tilt_deg is not None:
        limit_deg = max(0.0, float(max_tilt_deg))
        line_tilt = float(np.clip(raw_tilt, -limit_deg, limit_deg))
    else:
        line_tilt = raw_tilt

    if abs(line_tilt) > 0.10:
        line_canvas = line_canvas.rotate(line_tilt, resample=Image.Resampling.BICUBIC, expand=True)

    bbox_tight = line_canvas.getbbox()
    if bbox_tight:
        line_canvas = line_canvas.crop(bbox_tight)

    return line_canvas


def render_instant_film_frame(
    img_np: np.ndarray,
    config: InstantFrameConfig,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """
    入力画像 (H, W, 3) float32 [0.0, 1.0] に対してインスタントフィルム現像・フレーム・手書き文字を合成する。
    Returns:
        out_img: (H_out, W_out, 3) float32 [0.0, 1.0]
        window_mask: (H_out, W_out) float32 [0.0, 1.0] (写真窓領域のマスク)
        card_mask: (H_out, W_out) float32 [0.0, 1.0] (外枠角丸を含むカード本体のマスク)
        rendered_text: 実際に描画されたテキスト (caption + date)
    """
    # Level 1: 構図（Frame Format）の解決
    eff_format = config.frame_format or "Portrait (Vertical)"

    # Level 2: アスペクト適合（Fit Mode）の解決
    fit_mode = config.fit_mode or "Crop to Window"

    # Auto Aspect 判定: 入力画像の比率から最適な実在フィルム規格を自動選択
    in_h, in_w, _ = img_np.shape
    in_aspect = in_w / max(1.0, float(in_h))
    if fit_mode == "Auto Aspect":
        if in_aspect < 0.88:
            eff_format = "Portrait (Vertical)"
        elif in_aspect <= 1.15:
            eff_format = "Square (Polaroid)"
        else:
            eff_format = "Landscape (Wide)"

    spec = FRAME_SPECS.get(eff_format, FRAME_SPECS["Portrait (Vertical)"])
    target_aspect = spec["aspect_ratio"] if fit_mode != "Keep Aspect" else None

    # Level 3: フィルム現像トーンの解決 (構図連動 Smart Default または個別指定)
    emulation_val = config.emulation_strength
    paper_texture_val = config.paper_texture

    tone_key = config.film_tone
    if not tone_key or tone_key == "Auto (Match Format)":
        tone_key = DEFAULT_FORMAT_TONES.get(eff_format, "Modern Clear (instax)")
    tone_profile = FILM_TONES.get(tone_key, FILM_TONES["Modern Clear (instax)"])

    # Level 4: 印画紙マテリアルの解決 (構図連動 Smart Default または個別指定)
    paper_tone_key = config.paper_tone
    if not paper_tone_key or paper_tone_key == "Auto (Match Format)":
        paper_tone_key = DEFAULT_FORMAT_PAPERS.get(eff_format, "Pure White")
    paper_tone = PAPER_TONES.get(paper_tone_key, PAPER_TONES["Pure White"])

    # Level 5: 手書きタイポグラフィ ＆ インクの解決
    handwriting_style = config.handwriting_style or "Diary Pen (Casual Notes)"
    ink_color_key = resolve_ink_key(config.ink_color)
    layout_mode = config.layout_mode or "Center Caption + Right Date"
    ink_rgb = get_ink_color_rgb(ink_color_key)
    ink_profile = get_ink_physics(ink_color_key)

    # Stage 1: 窓トリミング & アスペクト適合
    cropped_np = _crop_and_fit_window(
        img_np,
        target_aspect,
        crop_position=config.crop_position,
        pan_x=config.pan_x,
        pan_y=config.pan_y,
        subject_mask=config.subject_mask,
        subject_bbox=config.subject_bbox,
        focus_point=config.focus_point,
    )
    win_h, win_w, _ = cropped_np.shape

    # Stage 2: 現像エミュレーション (0〜100)
    strength = max(0.0, min(1.0, float(emulation_val) / 100.0))
    emulated_np = _apply_instant_emulation(cropped_np, strength, tone_profile, config.seed)

    # Stage 3: フレーム寸法と新・物理スキャン印画紙キャンバスの構築
    s_ref = min(win_w, win_h)
    m_top = max(12, int(round(s_ref * spec["margin_top"])))
    m_bottom_raw = max(36, int(round(s_ref * spec["margin_bottom"])))

    # シミュラークル保護: Keep Aspect 時に縦長画像であってもアゴの存在感を保つ
    if fit_mode == "Keep Aspect" and win_h > win_w:
        m_bottom_raw = max(m_bottom_raw, int(round(win_h * 0.18)))

    m_side_raw = max(10, int(round(s_ref * spec["margin_sides"])))

    # Mod-8 アライメント (VAE / 下流ノード互換性のため幅・高さを8の倍数に整列)
    raw_w = win_w + 2 * m_side_raw
    canvas_w = _align_dimension(raw_w, 8)
    total_side = canvas_w - win_w
    m_side_l = total_side // 2
    m_side_r = total_side - m_side_l

    raw_h = win_h + m_top + m_bottom_raw
    canvas_h = _align_dimension(raw_h, 8)
    m_bottom = canvas_h - win_h - m_top

    win_x0 = m_side_l
    win_y0 = m_top
    win_x1 = win_x0 + win_w
    win_y1 = win_y0 + win_h

    # 印画紙質感スライダー強度 (0.0〜1.0)
    texture_strength = max(0.0, min(1.0, float(paper_texture_val) / 100.0))
    canvas_np, emboss_height = _generate_scanned_instant_paper(
        canvas_h,
        canvas_w,
        (win_x0, win_y0, win_x1, win_y1),
        paper_tone,
        texture_strength=texture_strength,
        seed=config.seed,
    )

    # 内窓のダイカット角丸マスク（四隅パッチ高速化）
    inner_r = max(2, int(round(s_ref * spec.get("inner_radius", 0.006))))
    if inner_r > 0:
        cw = min(win_w, inner_r + 2)
        ch = min(win_h, inner_r + 2)
        patch_box = Image.new("L", (cw * 2, ch * 2), 0)
        draw_b = ImageDraw.Draw(patch_box)
        draw_b.rounded_rectangle([0, 0, cw * 2 - 1, ch * 2 - 1], radius=inner_r, fill=255)
        tl = np.array(patch_box.crop((0, 0, cw, ch)), dtype=np.float32) / 255.0

        win_cut_arr = np.ones((win_h, win_w), dtype=np.float32)
        win_cut_arr[:ch, :cw] = tl
        win_cut_arr[:ch, -cw:] = tl[:, ::-1]
        win_cut_arr[-ch:, :cw] = tl[::-1, :]
        win_cut_arr[-ch:, -cw:] = tl[::-1, ::-1]
    else:
        win_cut_arr = np.ones((win_h, win_w), dtype=np.float32)

    # 窓枠落ち影（左上光源ペナンブラ + 全周密着アンブラ: 1Dプロファイル直積高速化）
    shadow_depth = max(4, int(round(s_ref * 0.015)))
    radius = max(1.0, shadow_depth * 0.32)

    sy = np.ones((win_h, 1), dtype=np.float32)
    for d in range(shadow_depth):
        t = (shadow_depth - d) / shadow_depth
        sy[d, 0] *= (1.0 - 0.28 * (t ** 1.6))
    for d in range(min(3, shadow_depth)):
        t = (min(3, shadow_depth) - d) / min(3, shadow_depth)
        sy[-(d + 1), 0] *= (1.0 - 0.10 * t)
    py = Image.fromarray((sy * 255.0).astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=radius))
    sy_soft = np.array(py, dtype=np.float32).ravel() * (1.0 / 255.0)

    sx = np.ones((1, win_w), dtype=np.float32)
    for d in range(shadow_depth):
        t = (shadow_depth - d) / shadow_depth
        sx[0, d] *= (1.0 - 0.24 * (t ** 1.6))
    for d in range(min(3, shadow_depth)):
        t = (min(3, shadow_depth) - d) / min(3, shadow_depth)
        sx[0, -(d + 1)] *= (1.0 - 0.10 * t)
    px = Image.fromarray((sx * 255.0).astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=radius))
    sx_soft = np.array(px, dtype=np.float32).ravel() * (1.0 / 255.0)

    shadow_soft = sy_soft[:, None] * sx_soft[None, :]

    emulated_shadowed = emulated_np * shadow_soft[:, :, None]

    # 写真窓と印画紙キャンバスを角丸アンチエイリアスでブレンド
    alpha_win = win_cut_arr[:, :, None]
    canvas_np[win_y0:win_y1, win_x0:win_x1, :] = (
        canvas_np[win_y0:win_y1, win_x0:win_x1, :] * (1.0 - alpha_win)
        + emulated_shadowed * alpha_win
    )

    # 外枠のダイカット角丸処理 & カード本体マスクの生成（四隅パッチ高速化）
    outer_r = max(3, int(round(s_ref * spec.get("corner_radius", 0.018))))
    if outer_r > 0:
        cw = min(canvas_w, outer_r + 2)
        ch = min(canvas_h, outer_r + 2)
        patch_box = Image.new("L", (cw * 2, ch * 2), 0)
        draw_b = ImageDraw.Draw(patch_box)
        draw_b.rounded_rectangle([0, 0, canvas_w * 2 - 1, canvas_h * 2 - 1], radius=outer_r * 2, fill=255)
        patch_corner = patch_box.resize((cw, ch), Image.Resampling.LANCZOS)
        tl = np.array(patch_corner, dtype=np.float32) / 255.0

        card_mask = np.ones((canvas_h, canvas_w), dtype=np.float32)
        card_mask[:ch, :cw] = tl
        card_mask[:ch, -cw:] = tl[:, ::-1]
        card_mask[-ch:, :cw] = tl[::-1, :]
        card_mask[-ch:, -cw:] = tl[::-1, ::-1]
    else:
        card_mask = np.ones((canvas_h, canvas_w), dtype=np.float32)

    if texture_strength > 0 and outer_r > 0:
        scanner_bg = np.array([22 / 255.0, 23 / 255.0, 26 / 255.0], dtype=np.float32)
        canvas_np = canvas_np * card_mask[:, :, None] + scanner_bg * (1.0 - card_mask[:, :, None])

    # 窓マスクの作成 (1.0 = 写真領域, 0.0 = フレーム余白)
    window_mask = np.zeros((canvas_h, canvas_w), dtype=np.float32)
    window_mask[win_y0:win_y1, win_x0:win_x1] = win_cut_arr

    # Stage 4: 余白の短文 & 日付の手書き描画
    resolved_date = resolve_date_string(config.date_string, config.seed)
    caption = config.caption_text.strip()

    # 高速パス: テキストと日付が両方空の場合は PIL 往復を完全スキップ
    if not resolved_date and not caption:
        return canvas_np, window_mask, card_mask, ""

    chin_y0 = win_y1
    chin_y1 = canvas_h
    chin_h = chin_y1 - chin_y0
    chin_w = canvas_w

    safe_pad_x = max(8, int(round(s_ref * 0.02)))
    safe_pad_y = max(6, int(round(chin_h * 0.08)))
    max_avail_w = max(40, canvas_w - m_side_l - m_side_r - 2 * safe_pad_x)
    max_avail_h = max(20, chin_h - 2 * safe_pad_y)

    # 揺らぎ度 (0〜100) -> 0.0〜1.0
    wobble_val = getattr(config, "handwriting_wobble", 50)
    if wobble_val is None:
        wobble_val = 50
    wobble_strength = max(0.0, min(1.0, float(wobble_val) / 100.0))
    w_rng = random.Random((config.seed + 104729) & 0xFFFFFFFF)

    font_file, font_norm = resolve_handwriting_font(handwriting_style, getattr(config, "font_choice", None))
    kinematics = get_handwriting_kinematics(font_file, pen_type=ink_profile.get("pen_type", "marker"))

    base_font_size = max(14, int(round(chin_h * 0.25 * config.font_scale * font_norm)))
    date_font_size = max(11, int(round(base_font_size * 0.78)))

    # 1. 日付レイヤーの先行生成（サイズ・位置把握のため）
    layer_date = None
    date_w = 0
    date_h = 0
    if resolved_date:
        fit_date_size, clean_date = _auto_fit_font_and_text(
            resolved_date,
            font_file,
            date_font_size,
            max_w=max_avail_w * 0.45,
            max_h=max_avail_h * 0.60,
            min_size=9,
            wobble_strength=wobble_strength,
            font_kinematics=kinematics,
        )
        max_tilt_date = min(1.6, 2.0 * kinematics.get("tilt_mul", 1.0))
        layer_date = _render_handwritten_text_layer(
            clean_date,
            font_file,
            fit_date_size,
            ink_rgb,
            ink_profile,
            seed=config.seed + 37,
            wobble_strength=wobble_strength,
            max_tilt_deg=max_tilt_date,
            is_date=True,
        )
        if layer_date:
            date_w = layer_date.width
            date_h = layer_date.height

    # 2. レイアウトモード別のキャプション最大寸法と衝突回避計算
    if layout_mode == "Center Caption + Right Date":
        max_caption_w = max_avail_w
        if layer_date:
            dy_relative = chin_h - max(6, int(chin_h * 0.20)) - date_h
            max_caption_h = max(12, int(dy_relative - safe_pad_y))
        else:
            max_caption_h = max_avail_h * 0.85

    elif layout_mode == "Left Stacked (Caption & Date)":
        max_caption_w = max_avail_w
        if layer_date:
            max_caption_h = max(12, int(max_avail_h * 0.55))
        else:
            max_caption_h = max_avail_h * 0.85

    elif layout_mode == "Caption Only (Centered)":
        max_caption_w = max_avail_w
        max_caption_h = max_avail_h * 0.85

    elif layout_mode == "Date Only (Bottom Right)":
        max_caption_w = 0
        max_caption_h = 0
    else:
        max_caption_w = max_avail_w
        max_caption_h = max_avail_h * 0.85

    # 3. キャプションレイヤーの自動縮小・生成
    layer_caption = None
    final_caption_str = caption
    if caption and max_caption_w > 0:
        fit_cap_size, final_caption_str = _auto_fit_font_and_text(
            caption,
            font_file,
            base_font_size,
            max_w=max_caption_w,
            max_h=max_caption_h,
            min_size=7,
            wobble_strength=wobble_strength,
            font_kinematics=kinematics,
        )
        # 余白高さ予算に基づく行全体の上限傾斜角動的算出 (長文時の余白食い潰しを防止)
        est_cap_w = max(20.0, _measure_text_width(final_caption_str, font_file, fit_cap_size))
        avail_tilt_h = max(3.0, max_caption_h * 0.35)
        max_tilt_cap = min(2.8, math.degrees(math.atan2(avail_tilt_h, est_cap_w)))

        layer_caption = _render_handwritten_text_layer(
            final_caption_str,
            font_file,
            fit_cap_size,
            ink_rgb,
            ink_profile,
            seed=config.seed + 11,
            wobble_strength=wobble_strength,
            max_tilt_deg=max_tilt_cap,
            is_date=False,
        )

    rendered_text = " | ".join(filter(None, [final_caption_str, resolved_date]))
    if layer_date is None and layer_caption is None:
        return canvas_np, window_mask, card_mask, rendered_text

    # アゴ領域（Chin）のみを PIL RGBA に変換して合成（全画面変換を回避）
    chin_uint8 = (canvas_np[chin_y0:chin_y1, :, :] * 255.0).astype(np.uint8)
    pil_chin = Image.fromarray(chin_uint8, mode="RGB").convert("RGBA")
    emboss_chin = emboss_height[chin_y0:chin_y1, :]

    # 4. 余白内への配置レイアウト (レイヤーA: 充填率連動マクロアンカー揺らぎ) & 印画紙シボ連動合成
    safe_min_x = m_side_l + safe_pad_x
    safe_max_x = canvas_w - m_side_r - safe_pad_x
    safe_min_y = safe_pad_y
    safe_max_y = chin_h - safe_pad_y

    cap_fill_ratio = (float(layer_caption.width) if layer_caption else 0.0) / max(1.0, float(safe_max_x - safe_min_x))
    # 充填率が高い長文ほどマクロジッターをダンピングし、写真窓や境界との衝突を防止
    fill_damp = max(0.18, 1.0 - 0.70 * (min(1.0, cap_fill_ratio) ** 1.4))

    if layout_mode == "Center Caption + Right Date":
        date_pos = None
        if layer_date:
            base_dx = canvas_w - m_side_r - layer_date.width - safe_pad_x
            base_dy = chin_h - max(6, int(chin_h * 0.20)) - layer_date.height

            date_dx_jitter = (w_rng.uniform(-safe_pad_x * 0.35, safe_pad_x * 0.80) * wobble_strength) if wobble_strength > 0 else 0.0
            date_dy_jitter = (w_rng.uniform(-chin_h * 0.05, chin_h * 0.05) * wobble_strength) if wobble_strength > 0 else 0.0

            dx = int(round(np.clip(base_dx - date_dx_jitter, safe_min_x, max(safe_min_x, safe_max_x - layer_date.width))))
            dy = int(round(np.clip(base_dy + date_dy_jitter, safe_min_y, max(safe_min_y, safe_max_y - layer_date.height))))
            date_pos = (dx, dy)
            _composite_text_with_paper_grain(pil_chin, layer_date, (dx, dy), emboss_chin, texture_strength)

        if layer_caption:
            base_tx = (chin_w - layer_caption.width) / 2.0
            slack_x = max(0.0, float(safe_max_x - safe_min_x - layer_caption.width))
            cap_dx_jitter = (w_rng.uniform(-0.25, 0.25) * slack_x * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0
            tx = int(round(np.clip(base_tx + cap_dx_jitter, safe_min_x, max(safe_min_x, safe_max_x - layer_caption.width))))

            if date_pos is not None:
                dx, dy = date_pos
                available_top = safe_pad_y
                # キャプションと日付の横方向衝突判定
                overlaps_x = not (tx + layer_caption.width < dx - safe_pad_x or tx > dx + layer_date.width + safe_pad_x)
                if overlaps_x:
                    cap_max_y = max(safe_min_y, dy - layer_caption.height - max(2, int(safe_pad_y * 0.5)))
                    center_y = (available_top + cap_max_y) / 2.0
                    slack_y = max(0.0, float(cap_max_y - safe_min_y))
                    cap_dy_jitter = (w_rng.uniform(-0.22, 0.22) * slack_y * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0
                    ty = int(round(np.clip(center_y + cap_dy_jitter, safe_min_y, max(safe_min_y, cap_max_y))))
                else:
                    center_y = (chin_h * 0.45) - (layer_caption.height / 2.0)
                    slack_y = max(0.0, float(safe_max_y - safe_min_y - layer_caption.height))
                    cap_dy_jitter = (w_rng.uniform(-0.22, 0.22) * slack_y * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0
                    ty = int(round(np.clip(center_y + cap_dy_jitter, safe_min_y, max(safe_min_y, safe_max_y - layer_caption.height))))
            else:
                center_y = (chin_h * 0.40) - (layer_caption.height / 2.0)
                slack_y = max(0.0, float(safe_max_y - safe_min_y - layer_caption.height))
                cap_dy_jitter = (w_rng.uniform(-0.22, 0.22) * slack_y * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0
                ty = int(round(np.clip(center_y + cap_dy_jitter, safe_min_y, max(safe_min_y, safe_max_y - layer_caption.height))))

            _composite_text_with_paper_grain(pil_chin, layer_caption, (tx, ty), emboss_chin, texture_strength)

    elif layout_mode == "Left Stacked (Caption & Date)":
        base_start_x = m_side_l + safe_pad_x
        cap_x_jitter = (w_rng.uniform(-safe_pad_x * 0.15, safe_pad_x * 0.80) * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0
        cap_y_jitter = (w_rng.uniform(-chin_h * 0.04, chin_h * 0.04) * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0

        tx = int(round(np.clip(base_start_x + cap_x_jitter, safe_min_x, max(safe_min_x, safe_max_x - (layer_caption.width if layer_caption else 0)))))
        curr_y = int(round(np.clip((chin_h * 0.18) + cap_y_jitter, safe_min_y, max(safe_min_y, safe_max_y - (layer_caption.height if layer_caption else 0)))))

        if layer_caption:
            _composite_text_with_paper_grain(pil_chin, layer_caption, (tx, curr_y), emboss_chin, texture_strength)
            base_gap = max(4, int(chin_h * 0.06))
            gap_jitter = (w_rng.uniform(-base_gap * 0.20, base_gap * 0.45) * wobble_strength) if wobble_strength > 0 else 0.0
            curr_y += layer_caption.height + max(2, int(round(base_gap + gap_jitter)))

        if layer_date:
            date_indent = (w_rng.uniform(-safe_pad_x * 0.15, safe_pad_x * 1.40) * wobble_strength) if wobble_strength > 0 else 0.0
            dx = int(round(np.clip(base_start_x + date_indent, safe_min_x, max(safe_min_x, safe_max_x - layer_date.width))))
            dy = int(round(np.clip(curr_y, safe_min_y, max(safe_min_y, safe_max_y - layer_date.height))))
            _composite_text_with_paper_grain(pil_chin, layer_date, (dx, dy), emboss_chin, texture_strength)

    elif layout_mode == "Caption Only (Centered)":
        if layer_caption:
            base_tx = (chin_w - layer_caption.width) / 2.0
            base_ty = (chin_h / 2.0) - (layer_caption.height / 2.0)
            slack_x = max(0.0, float(safe_max_x - safe_min_x - layer_caption.width))
            slack_y = max(0.0, float(safe_max_y - safe_min_y - layer_caption.height))
            tx_jitter = (w_rng.uniform(-0.25, 0.25) * slack_x * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0
            ty_jitter = (w_rng.uniform(-0.25, 0.25) * slack_y * wobble_strength * fill_damp) if wobble_strength > 0 else 0.0
            tx = int(round(np.clip(base_tx + tx_jitter, safe_min_x, max(safe_min_x, safe_max_x - layer_caption.width))))
            ty = int(round(np.clip(base_ty + ty_jitter, safe_min_y, max(safe_min_y, safe_max_y - layer_caption.height))))
            _composite_text_with_paper_grain(pil_chin, layer_caption, (tx, ty), emboss_chin, texture_strength)

    elif layout_mode == "Date Only (Bottom Right)":
        if layer_date:
            base_dx = canvas_w - m_side_r - layer_date.width - safe_pad_x
            base_dy = (chin_h / 2.0) - (layer_date.height / 2.0)
            slack_y = max(0.0, float(safe_max_y - safe_min_y - layer_date.height))
            dx_jitter = (w_rng.uniform(-safe_pad_x * 0.35, safe_pad_x * 0.90) * wobble_strength) if wobble_strength > 0 else 0.0
            dy_jitter = (w_rng.uniform(-0.30, 0.30) * slack_y * wobble_strength) if wobble_strength > 0 else 0.0
            dx = int(round(np.clip(base_dx - dx_jitter, safe_min_x, max(safe_min_x, safe_max_x - layer_date.width))))
            dy = int(round(np.clip(base_dy + dy_jitter, safe_min_y, max(safe_min_y, safe_max_y - layer_date.height))))
            _composite_text_with_paper_grain(pil_chin, layer_date, (dx, dy), emboss_chin, texture_strength)

    final_chin_rgb = pil_chin.convert("RGB")
    canvas_np[chin_y0:chin_y1, :, :] = np.array(final_chin_rgb, dtype=np.float32) / 255.0
    return canvas_np, window_mask, card_mask, rendered_text
