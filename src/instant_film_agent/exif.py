"""EXIF メタデータからの撮影日時抽出ユーティリティ。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ExifTags


def get_photo_datetime(image_or_path: Image.Image | Path | str) -> Tuple[Optional[datetime], str]:
    """
    画像ファイルまたは PIL.Image から撮影日時を取得する。
    戻り値: (datetimeオブジェクト または None, 検出ソース名)
    検出ソース: "exif_original", "exif_digitized", "exif_modified", "file_mtime", "none"
    """
    img = None
    close_img = False
    path: Optional[Path] = None

    if isinstance(image_or_path, (str, Path)):
        path = Path(image_or_path)
        if not path.is_file():
            return None, "none"
        try:
            img = Image.open(path)
            close_img = True
        except Exception:
            return None, "none"
    else:
        img = image_or_path
        if hasattr(img, "filename") and img.filename:
            path = Path(img.filename)

    try:
        exif = None
        # Pillow 10+ の getexif()
        if hasattr(img, "getexif"):
            exif = img.getexif()

        if exif:
            # 1. ExifIFD (tag 0x8769 = 34665) から DateTimeOriginal / DateTimeDigitized を探索
            exif_ifd = None
            try:
                exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
            except Exception:
                pass

            if exif_ifd:
                # DateTimeOriginal (0x9003 = 36867)
                dt_str = exif_ifd.get(36867)
                if dt_str and isinstance(dt_str, str):
                    dt = _parse_exif_date(dt_str)
                    if dt:
                        return dt, "exif_original"

                # DateTimeDigitized (0x9004 = 36868)
                dt_str = exif_ifd.get(36868)
                if dt_str and isinstance(dt_str, str):
                    dt = _parse_exif_date(dt_str)
                    if dt:
                        return dt, "exif_digitized"

            # 2. メインIFDの DateTime (0x0132 = 306)
            dt_str = exif.get(306)
            if dt_str and isinstance(dt_str, str):
                dt = _parse_exif_date(dt_str)
                if dt:
                    return dt, "exif_modified"

        # 3. 古い _getexif() フォールバック
        if hasattr(img, "_getexif"):
            raw_exif = img._getexif()
            if raw_exif and isinstance(raw_exif, dict):
                # 36867: DateTimeOriginal
                dt_str = raw_exif.get(36867) or raw_exif.get(36868) or raw_exif.get(306)
                if dt_str and isinstance(dt_str, str):
                    dt = _parse_exif_date(dt_str)
                    if dt:
                        return dt, "exif_original"

        # 4. EXIF に無ければファイルの mtime をフォールバック
        if path and path.is_file():
            try:
                mtime = path.stat().st_mtime
                return datetime.fromtimestamp(mtime), "file_mtime"
            except Exception:
                pass

    finally:
        if close_img and img:
            img.close()

    return None, "none"


def _parse_exif_date(value: str) -> Optional[datetime]:
    """EXIF標準形式 'YYYY:MM:DD HH:MM:SS' または ISO 類似形式を解析する。"""
    cleaned = value.strip().replace("\x00", "")
    for fmt in (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y:%m:%d",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None
