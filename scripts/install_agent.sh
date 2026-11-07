#!/bin/bash
# AIエージェント向け一括導入スクリプト。
# venv 作成 → パッケージ導入 → コマンド登録（~/.local/bin への symlink）→ doctor 検証までを1回で行う。
# 使い方: bash scripts/install_agent.sh
# 再実行しても安全（venv と symlink は再利用・上書きされる）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
BIN_LINK_DIR="$HOME/.local/bin"

echo "[1/4] venv を用意します: $VENV_DIR"
if [ ! -x "$VENV_DIR/bin/instant-film-agent" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv "$VENV_DIR"
  else
    python3 -m venv "$VENV_DIR"
  fi
fi

echo "[2/4] パッケージを導入します"
if command -v uv >/dev/null 2>&1; then
  VIRTUAL_ENV="$VENV_DIR" uv pip install "$REPO_ROOT"
else
  "$VENV_DIR/bin/pip" install "$REPO_ROOT"
fi

echo "[3/4] コマンドを登録します: $BIN_LINK_DIR/instant-film-agent"
mkdir -p "$BIN_LINK_DIR"
ln -sf "$VENV_DIR/bin/instant-film-agent" "$BIN_LINK_DIR/instant-film-agent"
case ":$PATH:" in
  *":$BIN_LINK_DIR:"*) ;;
  *) echo "注意: $BIN_LINK_DIR が PATH に含まれていません。フルパス $VENV_DIR/bin/instant-film-agent でも実行できます。" ;;
esac

echo "[4/4] doctor で検証します"
"$BIN_LINK_DIR/instant-film-agent" doctor --json

echo "導入完了。続けてスキル配置を行ってください: bash scripts/install_skill.sh"
