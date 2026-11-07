"""install_skill.sh の配置先キーワード (muse / gemini / 任意パス) の回帰テスト。

HOME を tmp に差し替えて実行するので、実ユーザーの skills は汚染しない。
PowerShell 版 (install_skill.ps1) は Windows 側で同じキーワード仕様を実装しているが、
このテストは bash 版のみを対象にする。
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "install_skill.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash が必要です")


def run_install(tmp_path: Path, *args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(tmp_path)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_ROOT,
        env=env,
    )


def assert_skill_installed(dest: Path):
    assert (dest / "SKILL.md").is_file()
    assert (dest / "skill.yaml").is_file()


def test_install_skill_muse_keyword(tmp_path):
    cp = run_install(tmp_path, "muse")
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / "workspace" / "custom-skills" / "instant-film-agent")


def test_install_skill_gemini_keyword_and_default(tmp_path):
    cp = run_install(tmp_path, "gemini")
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / ".gemini" / "config" / "skills" / "instant-film-agent")

    # 無指定時は gemini が既定 (従来互換)
    other = tmp_path / "other_home"
    other.mkdir()
    cp2 = run_install(other)
    assert cp2.returncode == 0, cp2.stderr
    assert_skill_installed(other / ".gemini" / "config" / "skills" / "instant-film-agent")


def test_install_skill_explicit_path(tmp_path):
    dest = tmp_path / "anywhere" / "my-skill"
    cp = run_install(tmp_path, str(dest))
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(dest)


def test_install_skill_env_var(tmp_path):
    cp = run_install(tmp_path, extra_env={"INSTANT_FILM_SKILL_DEST": "muse"})
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / "workspace" / "custom-skills" / "instant-film-agent")

    # 引数が環境変数より優先される
    dest = tmp_path / "arg_wins"
    cp2 = run_install(tmp_path, str(dest), extra_env={"INSTANT_FILM_SKILL_DEST": "muse"})
    assert cp2.returncode == 0, cp2.stderr
    assert_skill_installed(dest)
