import json
import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess:
    env = {**subprocess.os.environ, "PYTHONPATH": str(PACKAGE_ROOT / "src")}
    return subprocess.run(
        [PYTHON, "-m", "instant_film_agent", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PACKAGE_ROOT,
        env=env,
    )


def test_cli_doctor_json():
    cp = run_cli("doctor", "--json")
    assert cp.returncode == 0
    data = json.loads(cp.stdout)
    assert data["ok"] is True
    names = [c["name"] for c in data["checks"]]
    assert "engine_integrity" in names
    assert "fonts" in names


def test_cli_capabilities_json():
    cp = run_cli("capabilities", "--json")
    assert cp.returncode == 0
    data = json.loads(cp.stdout)
    assert data["ok"] is True
    assert "axes" in data
    assert "presets" in data


def test_cli_presets_list_json():
    cp = run_cli("presets", "list", "--json")
    assert cp.returncode == 0
    data = json.loads(cp.stdout)
    assert data["ok"] is True
    assert len(data["presets"]) >= 10


def test_cli_apply_json(sample_image: Path, tmp_path: Path):
    out = tmp_path / "cli_out.jpg"
    cp = run_cli("apply", str(sample_image), "-o", str(out), "--json")
    assert cp.returncode == 0
    data = json.loads(cp.stdout)
    assert data["ok"] is True
    assert data["output"] == str(out)
    assert out.is_file()


def test_cli_apply_invalid_input():
    cp = run_cli("apply", "non_existent_file.png", "--json")
    assert cp.returncode != 0
    data = json.loads(cp.stdout)
    assert data["ok"] is False
    assert data["error"]["code"] == "input_not_found"
