from pathlib import Path
from instant_film_agent.exif import get_photo_datetime

TEST_IMAGE = Path(__file__).resolve().parent / "data" / "DSC00004.JPG"


def test_get_photo_datetime_exif():
    if not TEST_IMAGE.is_file():
        return
    dt, source = get_photo_datetime(TEST_IMAGE)
    assert dt is not None
    assert source == "exif_original"
    assert dt.year == 2003
    assert dt.month == 10
    assert dt.day == 2
    assert dt.hour == 17
    assert dt.minute == 49


def test_get_photo_datetime_none(tmp_path: Path):
    dummy = tmp_path / "dummy.png"
    dummy.write_bytes(b"not an image")
    dt, source = get_photo_datetime(dummy)
    assert dt is None
    assert source == "none"
