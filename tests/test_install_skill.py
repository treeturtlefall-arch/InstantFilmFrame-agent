"""install_skill (bash および powershell) の配置先キーワード回帰テスト。

HOME / USERPROFILE を tmp に差し替えて実行するので、実ユーザーの skills は汚染しない。
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASH_SCRIPT = REPO_ROOT / "scripts" / "install_skill.sh"
PS_SCRIPT = REPO_ROOT / "scripts" / "install_skill.ps1"

HAS_BASH = shutil.which("bash") is not None
PS_EXE = shutil.which("pwsh") or shutil.which("powershell")


def run_install_bash(tmp_path: Path, *args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(tmp_path)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(BASH_SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_ROOT,
        env=env,
    )


def run_install_ps(tmp_path: Path, *args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "USERPROFILE": str(tmp_path), "HOME": str(tmp_path)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [PS_EXE, "-ExecutionPolicy", "Bypass", "-File", str(PS_SCRIPT), *args],
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


@pytest.mark.skipif(not HAS_BASH, reason="bash が必要です")
def test_install_skill_bash_muse_keyword(tmp_path):
    cp = run_install_bash(tmp_path, "muse")
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / "workspace" / "custom-skills" / "instant-film-agent")


@pytest.mark.skipif(not HAS_BASH, reason="bash が必要です")
def test_install_skill_bash_gemini_keyword_and_default(tmp_path):
    cp = run_install_bash(tmp_path, "gemini")
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / ".gemini" / "config" / "skills" / "instant-film-agent")

    other = tmp_path / "other_home"
    other.mkdir()
    cp2 = run_install_bash(other)
    assert cp2.returncode == 0, cp2.stderr
    assert_skill_installed(other / ".gemini" / "config" / "skills" / "instant-film-agent")


@pytest.mark.skipif(not HAS_BASH, reason="bash が必要です")
def test_install_skill_bash_explicit_path(tmp_path):
    dest = tmp_path / "anywhere" / "my-skill"
    cp = run_install_bash(tmp_path, str(dest))
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(dest)


@pytest.mark.skipif(not HAS_BASH, reason="bash が必要です")
def test_install_skill_bash_env_var(tmp_path):
    cp = run_install_bash(tmp_path, extra_env={"INSTANT_FILM_SKILL_DEST": "muse"})
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / "workspace" / "custom-skills" / "instant-film-agent")


@pytest.mark.skipif(PS_EXE is None, reason="PowerShell が必要です")
def test_install_skill_ps_muse_keyword(tmp_path):
    cp = run_install_ps(tmp_path, "muse")
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / "workspace" / "custom-skills" / "instant-film-agent")


@pytest.mark.skipif(PS_EXE is None, reason="PowerShell が必要です")
def test_install_skill_ps_gemini_keyword_and_default(tmp_path):
    cp = run_install_ps(tmp_path, "gemini")
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / ".gemini" / "config" / "skills" / "instant-film-agent")

    other = tmp_path / "other_home"
    other.mkdir()
    cp2 = run_install_ps(other)
    assert cp2.returncode == 0, cp2.stderr
    assert_skill_installed(other / ".gemini" / "config" / "skills" / "instant-film-agent")


@pytest.mark.skipif(PS_EXE is None, reason="PowerShell が必要です")
def test_install_skill_ps_explicit_path(tmp_path):
    dest = tmp_path / "anywhere" / "my-skill-ps"
    cp = run_install_ps(tmp_path, str(dest))
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(dest)


@pytest.mark.skipif(PS_EXE is None, reason="PowerShell が必要です")
def test_install_skill_ps_env_var(tmp_path):
    cp = run_install_ps(tmp_path, extra_env={"INSTANT_FILM_SKILL_DEST": "muse"})
    assert cp.returncode == 0, cp.stderr
    assert_skill_installed(tmp_path / "workspace" / "custom-skills" / "instant-film-agent")
