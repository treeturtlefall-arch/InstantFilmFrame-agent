"""インスタント写真フレームおよび現像エミュレーションの合成実行モジュール。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageOps

from . import __version__
from .engine import load as load_engine
from .errors import (
    EXIT_ENGINE,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_OUTPUT_EXISTS,
    EXIT_USAGE,
    AgentError,
)
from .exif import get_photo_datetime
from .presets import FAVORITE_WORDS, ResolvedPreset, load_favorites, resolve_preset

DATA_UPSTREAM = Path(__file__).resolve().parent / "data" / "upstream.json"

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"
}


def _engine_info() -> Dict[str, Any]:
    try:
        info = json.loads(DATA_UPSTREAM.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        info = {}
    return {
        "engine": info.get("repo", "InstantFilmFrame"),
        "snapshot": info.get("snapshot", "2026-11-08"),
        "agent_version": __version__,
    }


def _validate_input(path: Path) -> None:
    if not path.exists():
        raise AgentError("input_not_found", EXIT_INPUT, f"入力ファイルが見つかりません: {path}")
    if not path.is_file():
        raise AgentError("input_not_file", EXIT_INPUT, f"入力パスはファイルである必要があります: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise AgentError(
            "unsupported_format",
            EXIT_INPUT,
            f"未対応の画像形式です: {path.suffix}（対応: {', '.join(sorted(SUPPORTED_EXTENSIONS))}）",
        )


def _resolve_unique_output(input_path: Path, output: Optional[str], overwrite: bool) -> Path:
    """出力パスを解決する。未指定時は連番で一意のファイル名を決定する。"""
    if output:
        dest = Path(output).expanduser()
        if dest.is_dir():
            dest = dest / f"{input_path.stem}_instant{input_path.suffix}"
        if dest.exists() and not overwrite:
            raise AgentError(
                "output_exists",
                EXIT_OUTPUT_EXISTS,
                f"出力先が既に存在します: {dest}（上書きするには --overwrite を指定してください）",
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest

    dest_dir = input_path.parent
    stem = input_path.stem
    suffix = input_path.suffix if input_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else ".jpg"

    candidate = dest_dir / f"{stem}_instant{suffix}"
    if not candidate.exists() or overwrite:
        return candidate

    idx = 1
    while True:
        candidate = dest_dir / f"{stem}_instant_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def parse_at_datetime(at_str: str) -> datetime:
    cleaned = at_str.strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    raise AgentError("invalid_at_date", EXIT_USAGE, f"--at の日時形式を解析できません: '{at_str}'")


def resolve_date_input(
    date_arg: Optional[str],
    at_arg: Optional[str],
    preset_cfg: Dict[str, Any],
    input_path: Path,
) -> Tuple[str, str]:
    """
    日付文字列と検出ソースを解決する。
    戻り値: (描画用date_string, date_source)
    """
    # 1. --at 指定時
    if at_arg:
        dt = parse_at_datetime(at_arg)
        return dt.strftime("'%y %m %d"), "at_argument"

    # 2. --date 指定時
    raw_date = date_arg.strip() if date_arg else None

    if raw_date and raw_date.lower() in ("photo", "exif", "camera"):
        dt, source = get_photo_datetime(input_path)
        if dt:
            return dt.strftime("'%y %m %d"), f"photo_{source}"
        now = datetime.now()
        return now.strftime("'%y %m %d"), "fallback_now"

    if raw_date and raw_date.lower() in ("auto", "today", "now"):
        return "today", "auto_today"

    if raw_date and raw_date.lower() == "random":
        return "random", "random"

    if raw_date and raw_date.lower() in ("none", "off", "disable", "no"):
        return "", "none"

    if raw_date:
        return raw_date, "custom_string"

    # 3. 指定が無い場合はプリセットの設定
    preset_date = preset_cfg.get("date_string", "today")
    p_lower = str(preset_date).strip().lower()

    if p_lower in ("photo", "exif"):
        dt, source = get_photo_datetime(input_path)
        if dt:
            return dt.strftime("'%y %m %d"), f"photo_{source}"
        return "today", "fallback_today"

    return preset_date, "preset_default"


def parse_bbox(bbox_str: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not bbox_str:
        return None
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError
        return (parts[0], parts[1], parts[2], parts[3])
    except Exception:
        raise AgentError("invalid_bbox", EXIT_USAGE, f"--bbox は 'x0,y0,x1,y1' (0.0~1.0) の形式で指定してください: '{bbox_str}'")


def parse_focus_point(point_str: Optional[str]) -> Optional[Tuple[float, float]]:
    if not point_str:
        return None
    try:
        parts = [float(x.strip()) for x in point_str.split(",")]
        if len(parts) != 2:
            raise ValueError
        return (parts[0], parts[1])
    except Exception:
        raise AgentError("invalid_focus_point", EXIT_USAGE, f"--focus-point は 'cx,cy' (0.0~1.0) の形式で指定してください: '{point_str}'")


def apply(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    preset: Optional[str] = None,
    # Level 1: 構図選択
    frame_format: Optional[str] = None,
    # Level 2: アスペクト適合
    fit_mode: Optional[str] = None,
    crop_position: Optional[str] = None,
    pan_x: Optional[float] = None,
    pan_y: Optional[float] = None,
    # Level 3: 現像エミュレーション
    film_tone: Optional[str] = None,
    emulation_strength: Optional[int] = None,
    # Level 4: 印画紙マテリアル
    paper_tone: Optional[str] = None,
    paper_texture: Optional[int] = None,
    # Level 5: 手書きタイポグラフィ
    caption: Optional[str] = None,
    date: Optional[str] = None,
    at: Optional[str] = None,
    handwriting_style: Optional[str] = None,
    font_choice: Optional[str] = None,
    ink_color: Optional[str] = None,
    layout_mode: Optional[str] = None,
    font_scale: Optional[float] = None,
    handwriting_wobble: Optional[int] = None,
    # System
    seed: Optional[int] = None,
    bbox: Optional[str] = None,
    focus_point: Optional[str] = None,
    overwrite: bool = False,
    save_masks: bool = False,
) -> Dict[str, Any]:
    """
    単一画像に対してインスタントフィルム現像・フレーム・手書き文字を適用する。
    """
    in_p = Path(input_path).expanduser().resolve()
    _validate_input(in_p)

    out_p = _resolve_unique_output(in_p, str(output_path) if output_path else None, overwrite)

    # エンジンロード
    try:
        instant_config, instant_frame = load_engine()
    except Exception as e:
        raise AgentError("engine_load_failed", EXIT_ENGINE, f"エンジンのロードに失敗しました: {e}")

    # プリセット解決
    resolved = resolve_preset(preset)
    cfg_dict = dict(resolved.config_dict)

    # 日付解決
    date_str, date_source = resolve_date_input(date, at, cfg_dict, in_p)

    # パラメータの上書き
    if frame_format is not None:
        cfg_dict["frame_format"] = frame_format
    if fit_mode is not None:
        cfg_dict["fit_mode"] = fit_mode
    if crop_position is not None:
        cfg_dict["crop_position"] = crop_position
    if pan_x is not None:
        cfg_dict["pan_x"] = pan_x
    if pan_y is not None:
        cfg_dict["pan_y"] = pan_y
    if film_tone is not None:
        cfg_dict["film_tone"] = film_tone
    if emulation_strength is not None:
        cfg_dict["emulation_strength"] = int(emulation_strength)
    if paper_tone is not None:
        cfg_dict["paper_tone"] = paper_tone
    if paper_texture is not None:
        cfg_dict["paper_texture"] = int(paper_texture)
    if caption is not None:
        cfg_dict["caption_text"] = caption
    if handwriting_style is not None:
        cfg_dict["handwriting_style"] = handwriting_style
    if font_choice is not None:
        cfg_dict["font_choice"] = font_choice
    if ink_color is not None:
        cfg_dict["ink_color"] = ink_color
    if layout_mode is not None:
        cfg_dict["layout_mode"] = layout_mode
    if font_scale is not None:
        cfg_dict["font_scale"] = float(font_scale)
    if handwriting_wobble is not None:
        cfg_dict["handwriting_wobble"] = int(handwriting_wobble)
    if seed is not None:
        cfg_dict["seed"] = int(seed)

    cfg_dict["date_string"] = date_str

    subject_bbox_val = parse_bbox(bbox)
    focus_point_val = parse_focus_point(focus_point)

    # 画像読み込み & EXIF回転補正
    try:
        with Image.open(in_p) as raw_img:
            img_transposed = ImageOps.exif_transpose(raw_img)
            if img_transposed.mode != "RGB":
                # 透明度がある場合は白背景合成
                if img_transposed.mode in ("RGBA", "LA") or (img_transposed.mode == "P" and "transparency" in img_transposed.info):
                    bg = Image.new("RGB", img_transposed.size, (255, 255, 255))
                    rgba = img_transposed.convert("RGBA")
                    bg.paste(rgba, mask=rgba.split()[3])
                    img_rgb = bg
                else:
                    img_rgb = img_transposed.convert("RGB")
            else:
                img_rgb = img_transposed.copy()
    except Exception as e:
        raise AgentError("image_open_failed", EXIT_INPUT, f"入力画像を開けません: {in_p}: {e}")

    # float32 [0.0, 1.0] 配列化
    img_np = np.array(img_rgb, dtype=np.float32) / 255.0

    # InstantFrameConfig 構築
    try:
        config_obj = instant_config.InstantFrameConfig(
            frame_format=cfg_dict.get("frame_format", "Portrait (Vertical)"),
            fit_mode=cfg_dict.get("fit_mode", "Crop to Window"),
            crop_position=cfg_dict.get("crop_position", "Center"),
            pan_x=float(cfg_dict.get("pan_x", 0.0)),
            pan_y=float(cfg_dict.get("pan_y", 0.0)),
            film_tone=cfg_dict.get("film_tone", "Auto (Match Format)"),
            emulation_strength=int(cfg_dict.get("emulation_strength", 65)),
            paper_tone=cfg_dict.get("paper_tone", "Auto (Match Format)"),
            paper_texture=int(cfg_dict.get("paper_texture", 30)),
            caption_text=str(cfg_dict.get("caption_text", "")),
            date_string=str(cfg_dict.get("date_string", "")),
            handwriting_style=cfg_dict.get("handwriting_style", "Diary Pen (Casual Notes)"),
            font_choice=cfg_dict.get("font_choice", "Auto"),
            ink_color=cfg_dict.get("ink_color", "Marker Black (Permanent)"),
            layout_mode=cfg_dict.get("layout_mode", "Center Caption + Right Date"),
            font_scale=float(cfg_dict.get("font_scale", 1.0)),
            handwriting_wobble=int(cfg_dict.get("handwriting_wobble", 50)),
            seed=int(cfg_dict.get("seed", 0)),
            subject_bbox=subject_bbox_val,
            focus_point=focus_point_val,
        )
    except Exception as e:
        raise AgentError("invalid_config", EXIT_USAGE, f"設定パラメータが不正です: {e}")

    # レンダリング実行
    try:
        out_np, window_mask, card_mask, rendered_text = instant_frame.render_instant_film_frame(
            img_np,
            config_obj,
        )
    except Exception as e:
        raise AgentError("render_failed", EXIT_ENGINE, f"レンダリング処理が失敗しました: {e}")

    # 出力保存
    try:
        out_uint8 = np.clip(out_np * 255.0 + 0.5, 0, 255).astype(np.uint8)
        out_pil = Image.fromarray(out_uint8, mode="RGB")

        if out_p.suffix.lower() in (".jpg", ".jpeg"):
            out_pil.save(out_p, "JPEG", quality=95, optimize=True)
        else:
            out_pil.save(out_p)
    except Exception as e:
        raise AgentError("save_failed", EXIT_ENGINE, f"出力画像の保存に失敗しました: {out_p}: {e}")

    # マスクの保存 (オプション)
    saved_masks: Dict[str, str] = {}
    if save_masks:
        try:
            mask_stem = out_p.parent / f"{out_p.stem}"
            win_mask_path = out_p.parent / f"{mask_stem.name}_window_mask.png"
            card_mask_path = out_p.parent / f"{mask_stem.name}_card_mask.png"

            win_uint8 = np.clip(window_mask * 255.0 + 0.5, 0, 255).astype(np.uint8)
            card_uint8 = np.clip(card_mask * 255.0 + 0.5, 0, 255).astype(np.uint8)

            Image.fromarray(win_uint8, mode="L").save(win_mask_path)
            Image.fromarray(card_uint8, mode="L").save(card_mask_path)

            saved_masks["window_mask"] = str(win_mask_path)
            saved_masks["card_mask"] = str(card_mask_path)
        except Exception as e:
            # マスク保存失敗は致命的エラーにはしない
            saved_masks["error"] = str(e)

    h_in, w_in = img_np.shape[:2]
    h_out, w_out = out_np.shape[:2]

    return {
        "ok": True,
        "input": str(in_p),
        "output": str(out_p),
        "preset_resolved": resolved.name,
        "preset_slug": resolved.slug,
        "rendered_text": rendered_text,
        "date_resolved": config_obj.date_string,
        "date_source": date_source,
        "frame_format": config_obj.frame_format,
        "fit_mode": config_obj.fit_mode,
        "film_tone": config_obj.film_tone,
        "emulation_strength": config_obj.emulation_strength,
        "paper_tone": config_obj.paper_tone,
        "dimensions": {
            "input": [w_in, h_in],
            "output": [w_out, h_out],
        },
        "masks": saved_masks if save_masks else None,
        "engine_info": _engine_info(),
    }


def batch(
    input_dir: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    recursive: bool = False,
    preset: Optional[str] = None,
    overwrite: bool = False,
    save_masks: bool = False,
    **apply_kwargs,
) -> Dict[str, Any]:
    """ディレクトリ内の一括画像処理を行う。"""
    src_dir = Path(input_dir).expanduser().resolve()
    if not src_dir.is_dir():
        raise AgentError("dir_not_found", EXIT_INPUT, f"対象ディレクトリが見つかりません: {src_dir}")

    out_d = Path(output_dir).expanduser().resolve() if output_dir else src_dir / "instant_batch_out"
    out_d.mkdir(parents=True, exist_ok=True)

    pattern = "**/*" if recursive else "*"
    files = [
        p for p in src_dir.glob(pattern)
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS and "instant" not in p.name
    ]

    results: List[Dict[str, Any]] = []
    success_count = 0
    fail_count = 0

    for p in sorted(files):
        target_out = out_d / f"{p.stem}_instant{p.suffix if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp') else '.jpg'}"
        try:
            res = apply(
                input_path=p,
                output_path=target_out,
                preset=preset,
                overwrite=overwrite,
                save_masks=save_masks,
                **apply_kwargs,
            )
            results.append(res)
            success_count += 1
        except AgentError as err:
            results.append({
                "ok": False,
                "input": str(p),
                "error": err.to_dict()["error"],
            })
            fail_count += 1
        except Exception as e:
            results.append({
                "ok": False,
                "input": str(p),
                "error": {"code": "unknown_error", "message": str(e)},
            })
            fail_count += 1

    return {
        "ok": fail_count == 0,
        "input_dir": str(src_dir),
        "output_dir": str(out_d),
        "total": len(files),
        "success": success_count,
        "failed": fail_count,
        "items": results,
    }
