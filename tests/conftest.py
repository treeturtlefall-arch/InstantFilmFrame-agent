import pytest
from pathlib import Path
from PIL import Image

DATA_DIR = Path(__file__).resolve().parent / "data"


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """単体テスト用の単色RGB画像を作成する。"""
    p = tmp_path / "sample.png"
    img = Image.new("RGB", (640, 480), color=(50, 70, 90))
    img.save(p)
    return p


@pytest.fixture
def sample_image_vertical(tmp_path: Path) -> Path:
    """縦長画像を作成する。"""
    p = tmp_path / "sample_vert.png"
    img = Image.new("RGB", (480, 640), color=(70, 90, 50))
    img.save(p)
    return p


@pytest.fixture
def exif_test_image() -> Path:
    """高速テスト用の EXIF 付き極小画像パスを返す。"""
    small = DATA_DIR / "small_exif.jpg"
    if small.is_file():
        return small
    return DATA_DIR / "DSC00004.JPG"
