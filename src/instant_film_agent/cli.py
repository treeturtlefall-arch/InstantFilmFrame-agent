"""InstantFilmFrame Agent CLI インターフェース。"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .capabilities import build_capabilities, human_summary
from .engine import ENGINE_DIR, FONTS_DIR, engine_file_sha256, load as load_engine
from .errors import (
    EXIT_ENGINE,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_OUTPUT_EXISTS,
    EXIT_USAGE,
    AgentError,
)
from .presets import (
    create_preset,
    get_builtin_presets,
    list_all_presets,
    load_favorites,
    resolve_preset,
    set_user_favorite,
    user_config_dir,
    user_favorites_file,
)
from .runner import apply as run_apply, batch as run_batch

# Windows コンソール等での UnicodeEncodeError を防止
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _emit(report: Dict[str, Any], as_json: bool, human: Optional[str] = None) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif human is not None:
        print(human)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


def _fail(err: AgentError, as_json: bool) -> int:
    if as_json:
        print(json.dumps(err.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"エラー: {err.message}", file=sys.stderr)
        candidates = err.extra.get("candidates")
        if candidates:
            print(f"利用可能な候補: {', '.join(candidates)}", file=sys.stderr)
    return err.exit_code


def _wants_json(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False))


def cmd_apply(args: argparse.Namespace) -> int:
    as_json = _wants_json(args)
    try:
        report = run_apply(
            input_path=args.input,
            output_path=args.output,
            preset=args.preset,
            frame_format=args.format,
            fit_mode=args.fit,
            crop_position=args.crop_pos,
            pan_x=args.pan_x,
            pan_y=args.pan_y,
            film_tone=args.tone,
            emulation_strength=args.emulation,
            paper_tone=args.paper,
            paper_texture=args.paper_texture,
            caption=args.caption,
            date=args.date,
            at=args.at,
            handwriting_style=args.style,
            font_choice=args.font,
            ink_color=args.ink,
            layout_mode=args.layout,
            font_scale=args.scale,
            handwriting_wobble=args.wobble,
            seed=args.seed,
            bbox=args.bbox,
            focus_point=args.focus_point,
            overwrite=args.overwrite,
            save_masks=args.save_masks,
        )
    except AgentError as err:
        return _fail(err, as_json)
    except Exception as e:
        return _fail(AgentError("unexpected_error", EXIT_ENGINE, f"予期せぬエラー: {e}"), as_json)

    human = None
    if not as_json:
        rendered = report.get("rendered_text") or "なし"
        dims = report.get("dimensions", {})
        human = (
            f"完了: {report['output']}\n"
            f"  プリセット: {report['preset_resolved']}\n"
            f"  構図・適合: {report['frame_format']} / {report['fit_mode']}\n"
            f"  トーン・強度: {report['film_tone']} (強さ: {report['emulation_strength']})\n"
            f"  手書き文字: {rendered}\n"
            f"  画像サイズ: {dims.get('input', ['-','-'])[0]}x{dims.get('input', ['-','-'])[1]} -> "
            f"{dims.get('output', ['-','-'])[0]}x{dims.get('output', ['-','-'])[1]}"
        )
        if report.get("masks"):
            human += f"\n  マスク保存: {report['masks'].get('window_mask')} / {report['masks'].get('card_mask')}"

    _emit(report, as_json, human)
    return EXIT_OK


def cmd_batch(args: argparse.Namespace) -> int:
    as_json = _wants_json(args)
    try:
        report = run_batch(
            input_dir=args.input_dir,
            output_dir=args.output,
            recursive=args.recursive,
            preset=args.preset,
            frame_format=args.format,
            fit_mode=args.fit,
            crop_position=args.crop_pos,
            pan_x=args.pan_x,
            pan_y=args.pan_y,
            film_tone=args.tone,
            emulation_strength=args.emulation,
            paper_tone=args.paper,
            paper_texture=args.paper_texture,
            caption=args.caption,
            date=args.date,
            at=args.at,
            handwriting_style=args.style,
            font_choice=args.font,
            ink_color=args.ink,
            layout_mode=args.layout,
            font_scale=args.scale,
            handwriting_wobble=args.wobble,
            seed=args.seed,
            bbox=args.bbox,
            focus_point=args.focus_point,
            overwrite=args.overwrite,
            save_masks=args.save_masks,
        )
    except AgentError as err:
        return _fail(err, as_json)
    except Exception as e:
        return _fail(AgentError("unexpected_error", EXIT_ENGINE, f"予期せぬエラー: {e}"), as_json)

    human = None
    if not as_json:
        human = (
            f"一括処理完了: 合計 {report['total']} 件 "
            f"(成功 {report['success']} 件 / 失敗 {report['failed']} 件)\n"
            f"出力ディレクトリ: {report['output_dir']}"
        )
    _emit(report, as_json, human)
    return EXIT_OK if report["ok"] else EXIT_ENGINE


def cmd_presets(args: argparse.Namespace) -> int:
    as_json = _wants_json(args)
    action = getattr(args, "presets_action", "list")

    if action == "list":
        items = list_all_presets()
        report = {
            "ok": True,
            "presets": [
                {
                    "name": disp,
                    "slug": s,
                    "source": src,
                    "format": cfg.get("frame_format"),
                    "fit_mode": cfg.get("fit_mode"),
                    "tone": cfg.get("film_tone"),
                    "emulation": cfg.get("emulation_strength"),
                    "description": cfg.get("description", ""),
                }
                for disp, s, cfg, src, path in items
            ],
        }
        human = None
        if not as_json:
            lines = ["利用可能なプリセット一覧:"]
            for disp, s, cfg, src, _ in items:
                desc = f" - {cfg.get('description')}" if cfg.get("description") else ""
                lines.append(f"  • {disp} ({s}) [{src}]{desc}")
            human = "\n".join(lines)
        _emit(report, as_json, human)
        return EXIT_OK

    elif action == "show":
        query = args.name
        try:
            resolved = resolve_preset(query)
        except AgentError as err:
            return _fail(err, as_json)

        report = {
            "ok": True,
            "preset": {
                "name": resolved.name,
                "slug": resolved.slug,
                "source": resolved.source,
                "file": str(resolved.file_path) if resolved.file_path else None,
                "config": resolved.config_dict,
            },
        }
        human = None
        if not as_json:
            cfg = resolved.config_dict
            human = (
                f"プリセット詳細: {resolved.name} ({resolved.slug}) [{resolved.source}]\n"
                f"  構図・適合: {cfg.get('frame_format')} / {cfg.get('fit_mode')}\n"
                f"  トーン・強度: {cfg.get('film_tone')} (強度: {cfg.get('emulation_strength')})\n"
                f"  用紙・質感: {cfg.get('paper_tone')} (粗さ: {cfg.get('paper_texture')})\n"
                f"  手書きペン: {cfg.get('handwriting_style')} / インク: {cfg.get('ink_color')}\n"
                f"  説明: {cfg.get('description', 'なし')}"
            )
        _emit(report, as_json, human)
        return EXIT_OK

    return EXIT_USAGE


def cmd_favorite(args: argparse.Namespace) -> int:
    as_json = _wants_json(args)
    if args.name:
        try:
            set_user_favorite(args.name)
            resolved = resolve_preset("favorite")
            report = {"ok": True, "favorite": resolved.slug, "name": resolved.name}
            human = f"お気に入りを '{resolved.name}' ({resolved.slug}) に設定しました。"
            _emit(report, as_json, human)
            return EXIT_OK
        except AgentError as err:
            return _fail(err, as_json)
    else:
        try:
            resolved = resolve_preset("favorite")
            report = {
                "ok": True,
                "favorite": resolved.slug,
                "name": resolved.name,
                "config": resolved.config_dict,
                "source": resolved.source,
            }
            human = f"現在のお気に入り: {resolved.name} ({resolved.slug}) [{resolved.source}]"
            _emit(report, as_json, human)
            return EXIT_OK
        except AgentError as err:
            return _fail(err, as_json)


def cmd_capabilities(args: argparse.Namespace) -> int:
    as_json = _wants_json(args)
    caps = build_capabilities()
    _emit(caps, as_json, human_summary(caps) if not as_json else None)
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    as_json = _wants_json(args)
    checks: List[Dict[str, Any]] = []

    # 1. Python バージョン
    py_ok = sys.version_info >= (3, 10)
    checks.append({
        "name": "python",
        "ok": py_ok,
        "detail": f"Python {platform.python_version()} (3.10+ required)",
    })

    # 2. NumPy
    try:
        import numpy as np
        checks.append({"name": "numpy", "ok": True, "detail": f"v{np.__version__}"})
    except ImportError as e:
        checks.append({"name": "numpy", "ok": False, "detail": str(e)})

    # 3. Pillow
    try:
        import PIL
        checks.append({"name": "pillow", "ok": True, "detail": f"v{PIL.__version__}"})
    except ImportError as e:
        checks.append({"name": "pillow", "ok": False, "detail": str(e)})

    # 4. エンジン整合性
    manifest_path = Path(__file__).resolve().parent / "data" / "engine_hashes.json"
    hashes: Dict[str, str] = {}
    if manifest_path.is_file():
        try:
            hashes = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    engine_ok = True
    engine_details = []
    for rel_path, expected_hash in hashes.items():
        actual_file = ENGINE_DIR / rel_path
        actual_hash = engine_file_sha256(actual_file)
        if actual_hash != expected_hash:
            engine_ok = False
            engine_details.append(f"{rel_path}: mismatch (got {actual_hash[:8]}..., expected {expected_hash[:8]}...)")

    checks.append({
        "name": "engine_integrity",
        "ok": engine_ok,
        "detail": f"{len(hashes)} files verified" if engine_ok else "; ".join(engine_details),
    })

    # 5. フォントの存在
    instant_config, _ = load_engine()
    font_missing = []
    # 登録されているフォントファイルをチェック
    all_fonts = set(instant_config.HANDWRITING_FONTS.values())

    for fn in sorted(all_fonts):
        fp = FONTS_DIR / fn
        if not fp.is_file():
            font_missing.append(fn)

    checks.append({
        "name": "fonts",
        "ok": len(font_missing) == 0,
        "detail": f"All {len(all_fonts)} handwriting fonts present" if not font_missing else f"Missing: {font_missing}",
    })

    all_ok = all(c["ok"] for c in checks)
    report = {"ok": all_ok, "checks": checks}

    human = None
    if not as_json:
        lines = ["環境診断 (doctor):"]
        for c in checks:
            mark = "[OK]" if c["ok"] else "[NG]"
            lines.append(f"  {mark} {c['name']}: {c['detail']}")
        lines.append("\n全チェック合格。正常に動作可能です。" if all_ok else "\n一部チェックに不合格があります。")
        human = "\n".join(lines)

    _emit(report, as_json, human)
    return EXIT_OK if all_ok else EXIT_ENGINE


def _add_common_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("-p", "--preset", help="プリセット名またはエイリアス（例: instax-mini, polaroid-600, sx70）")
    # Level 1
    p.add_argument("--format", dest="format", choices=["Portrait (Vertical)", "Square (Polaroid)", "Landscape (Wide)"], help="構図規格")
    # Level 2
    p.add_argument("--fit", dest="fit", choices=["Crop to Window", "Auto Aspect", "Keep Aspect"], help="アスペクト適合方式")
    p.add_argument("--crop-pos", dest="crop_pos", help="クロップ位置（Center, Top, Bottom等）")
    p.add_argument("--pan-x", type=float, help="横方向パン (-1.0〜1.0)")
    p.add_argument("--pan-y", type=float, help="縦方向パン (-1.0〜1.0)")
    # Level 3
    p.add_argument("--tone", dest="tone", help="フィルム現像トーン（例: 'Modern Clear (instax)', 'Cool Cyan (90s Snap)' 等）")
    p.add_argument("--emulation", type=int, help="現像エミュレーション強度 (0〜100)")
    # Level 4
    p.add_argument("--paper", dest="paper", help="印画紙カラー（Pure White, Warm Ivory, Aged Vintage, Matte Black）")
    p.add_argument("--paper-texture", type=int, help="印画紙テクスチャ粗さ (0〜100)")
    # Level 5
    p.add_argument("-c", "--caption", help="余白キャプション文字列")
    p.add_argument("-d", "--date", help="日付指定 ('photo'=EXIF撮影日, 'today'=今日, 'random'=昔のランダム, 'none'=非表示, または任意文字列)")
    p.add_argument("--at", help="撮影日時指定 ('YYYY-MM-DD' または 'YYYY-MM-DDTHH:MM')")
    p.add_argument("--style", dest="style", help="手書きフォントスタイル（例: 'Diary Pen (Casual Notes)', 'Cute Round Pop (Kawaii)' 等）")
    p.add_argument("--font", dest="font", help="フォントファイル直接指定")
    p.add_argument("--ink", dest="ink", help="インクカラー（例: 'Marker Black (Permanent)', 'Gel Ink Blue (Ballpoint)' 等）")
    p.add_argument("--layout", dest="layout", help="レイアウトモード")
    p.add_argument("--scale", type=float, help="フォント倍率")
    p.add_argument("--wobble", type=int, help="手ブレ・傾き揺らぎ量 (0〜100)")
    # System
    p.add_argument("--seed", type=int, help="乱数シード")
    p.add_argument("--bbox", help="被写体バウンディングボックス 'x0,y0,x1,y1' (0.0〜1.0)")
    p.add_argument("--focus-point", help="被写体注視点 'cx,cy' (0.0〜1.0)")
    p.add_argument("--save-masks", action="store_true", help="写真窓およびカード外枠のマスク画像をPNG保存する")
    p.add_argument("--overwrite", action="store_true", help="出力ファイルが既に存在する場合に上書きする")
    p.add_argument("--json", action="store_true", help="機械可読なJSON形式で出力する")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instant-film-agent",
        description="インスタント写真フレーム＆現像エミュレーション AI エージェント CLI",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="機械可読なJSON形式で出力する")

    sub = parser.add_subparsers(dest="subcommand", required=False)

    # 1. apply
    p_apply = sub.add_parser("apply", help="単一画像にインスタント写真加工を適用する")
    p_apply.add_argument("input", help="入力画像ファイルのパス")
    p_apply.add_argument("-o", "--output", help="出力先画像ファイルのパス")
    _add_common_options(p_apply)

    # 2. batch
    p_batch = sub.add_parser("batch", help="ディレクトリ内の画像を一括処理する")
    p_batch.add_argument("input_dir", help="対象ディレクトリ")
    p_batch.add_argument("-o", "--output", help="出力ディレクトリ")
    p_batch.add_argument("-r", "--recursive", action="store_true", help="再帰的に探索")
    _add_common_options(p_batch)

    # 3. presets
    p_presets = sub.add_parser("presets", help="プリセット一覧または詳細を表示する")
    p_presets.add_argument("--json", action="store_true", help="JSON出力")
    sub_presets = p_presets.add_subparsers(dest="presets_action", required=False)

    p_p_list = sub_presets.add_parser("list", help="プリセット一覧")
    p_p_list.add_argument("--json", action="store_true", help="JSON出力")

    p_p_show = sub_presets.add_parser("show", help="プリセット詳細")
    p_p_show.add_argument("name", help="プリセット名またはエイリアス")
    p_p_show.add_argument("--json", action="store_true", help="JSON出力")

    # 4. favorite
    p_fav = sub.add_parser("favorite", help="現在のお気に入りを表示または新しいお気に入りを設定する")
    p_fav.add_argument("name", nargs="?", help="新しくお気に入りに設定するプリセット名")
    p_fav.add_argument("--json", action="store_true", help="JSON出力")

    # 5. capabilities
    p_cap = sub.add_parser("capabilities", help="対応機能・パラメータ一覧をJSON出力する")
    p_cap.add_argument("--json", action="store_true", help="JSON出力")

    # 6. doctor
    p_doc = sub.add_parser("doctor", help="動作環境および同梱素材の整合性を診断する")
    p_doc.add_argument("--json", action="store_true", help="JSON出力")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return EXIT_USAGE

    dispatch = {
        "apply": cmd_apply,
        "batch": cmd_batch,
        "presets": cmd_presets,
        "favorite": cmd_favorite,
        "capabilities": cmd_capabilities,
        "doctor": cmd_doctor,
    }

    fn = dispatch.get(args.subcommand)
    if fn is None:
        parser.print_help()
        return EXIT_USAGE

    return fn(args)
