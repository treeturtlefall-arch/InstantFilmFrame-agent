from pathlib import Path
from PIL import Image
from instant_film_agent.runner import apply, batch


def test_apply_default(sample_image: Path, tmp_path: Path):
    out = tmp_path / "out.jpg"
    res = apply(sample_image, output_path=out)
    assert res["ok"] is True
    assert out.is_file()
    assert res["frame_format"] == "Portrait (Vertical)"
    assert res["preset_slug"] == "instax-mini-vertical-snap"

    # 出力画像のサイズ確認
    with Image.open(out) as img:
        w, h = img.size
        # 縦長チェキ比率 (54:86 ≈ 1:1.59)
        assert h > w


def test_apply_polaroid_square(sample_image: Path, tmp_path: Path):
    out = tmp_path / "out_polaroid.jpg"
    res = apply(sample_image, output_path=out, preset="polaroid-600", caption="Hello")
    assert res["ok"] is True
    assert out.is_file()
    assert res["frame_format"] == "Square (Polaroid)"
    assert "Hello" in res["rendered_text"]


def test_apply_save_masks(sample_image: Path, tmp_path: Path):
    out = tmp_path / "out_mask.jpg"
    res = apply(sample_image, output_path=out, save_masks=True)
    assert res["ok"] is True
    assert res["masks"] is not None
    win_mask = Path(res["masks"]["window_mask"])
    card_mask = Path(res["masks"]["card_mask"])
    assert win_mask.is_file()
    assert card_mask.is_file()


def test_batch_processing(tmp_path: Path):
    in_dir = tmp_path / "batch_in"
    in_dir.mkdir()
    out_dir = tmp_path / "batch_out"

    for i in range(2):
        img = Image.new("RGB", (300, 300), color=(i * 50, 100, 150))
        img.save(in_dir / f"img_{i}.jpg")

    report = batch(input_dir=in_dir, output_dir=out_dir)
    assert report["ok"] is True
    assert report["total"] == 2
    assert report["success"] == 2
    assert report["failed"] == 0
