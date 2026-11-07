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

    # 1. 通常の入力画像
    for i in range(2):
        img = Image.new("RGB", (300, 300), color=(i * 50, 100, 150))
        img.save(in_dir / f"img_{i}.jpg")

    # 2. 'instant' が名前に含まれるが生成物ではない画像 (処理対象になるべき)
    instant_camera_img = in_dir / "instant_camera.jpg"
    Image.new("RGB", (300, 300), color=(10, 20, 30)).save(instant_camera_img)

    # 3. 以前生成されたアーティファクト (スキップされるべき)
    old_artifact = in_dir / "old_instant.jpg"
    old_mask = in_dir / "old_instant_window_mask.png"
    Image.new("RGB", (300, 300), color=(0, 0, 0)).save(old_artifact)
    Image.new("RGB", (300, 300), color=(0, 0, 0)).save(old_mask)

    report = batch(input_dir=in_dir, output_dir=out_dir)
    assert report["ok"] is True
    # img_0, img_1, instant_camera の計3件が処理対象
    assert report["total"] == 3
    assert report["success"] == 3
    assert report["failed"] == 0
