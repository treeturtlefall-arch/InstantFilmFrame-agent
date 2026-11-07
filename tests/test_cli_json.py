import json
import subprocess
import sys
from pathlib import Path
import pytest
from instant_film_agent.cli import main

PYTHON = sys.executable
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def run_cli_inprocess(capsys, *args: str) -> tuple[int, dict]:
    code = main(list(args))
    captured = capsys.readouterr()
    output = captured.out or captured.err
    data = json.loads(output)
    return code, data


def test_cli_doctor_json(capsys):
    code, data = run_cli_inprocess(capsys, "doctor", "--json")
    assert code == 0
    assert data["ok"] is True
    names = [c["name"] for c in data["checks"]]
    assert "engine_integrity" in names
    assert "fonts" in names


def test_cli_json_flag_order_doctor(capsys):
    """--json がサブコマンドの前にある場合でも正しく JSON 出力される。"""
    code, data = run_cli_inprocess(capsys, "--json", "doctor")
    assert code == 0
    assert data["ok"] is True


def test_cli_capabilities_json(capsys):
    code, data = run_cli_inprocess(capsys, "capabilities", "--json")
    assert code == 0
    assert data["ok"] is True
    assert "axes" in data
    assert "presets" in data


def test_cli_presets_list_json(capsys):
    code, data = run_cli_inprocess(capsys, "presets", "list", "--json")
    assert code == 0
    assert data["ok"] is True
    assert len(data["presets"]) >= 10


def test_cli_apply_json(sample_image: Path, tmp_path: Path, capsys):
    out = tmp_path / "cli_out.jpg"
    code, data = run_cli_inprocess(capsys, "apply", str(sample_image), "-o", str(out), "--json")
    assert code == 0
    assert data["ok"] is True
    assert data["output"] == str(out)
    assert out.is_file()


def test_cli_apply_invalid_input(capsys):
    code, data = run_cli_inprocess(capsys, "apply", "non_existent_file.png", "--json")
    assert code != 0
    assert data["ok"] is False
    assert data["error"]["code"] == "input_not_found"


def test_cli_subprocess_smoke():
    """サブプロセスとして python -m instant_film_agent が起動できるスモークテスト。"""
    env = {**subprocess.os.environ, "PYTHONPATH": str(PACKAGE_ROOT / "src")}
    cp = subprocess.run(
        [PYTHON, "-m", "instant_film_agent", "doctor", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PACKAGE_ROOT,
        env=env,
    )
    assert cp.returncode == 0
    data = json.loads(cp.stdout)
    assert data["ok"] is True
