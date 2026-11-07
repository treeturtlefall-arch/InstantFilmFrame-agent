#!/usr/bin/env bash
# AIエージェントの custom-skills / Antigravity skills へ SKILL.md を配置する。
set -euo pipefail

DEST="${1:-$HOME/.gemini/config/skills/instant-film-agent}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_FILE="$REPO_ROOT/skill/SKILL.md"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "エラー: SKILL.md が見つかりません: $SOURCE_FILE" >&2
    exit 1
fi

mkdir -p "$DEST"
cp "$SOURCE_FILE" "$DEST/SKILL.md"
echo "スキル定義を配置しました: $DEST/SKILL.md"

YAML_FILE="$REPO_ROOT/skill/skill.yaml"
if [ -f "$YAML_FILE" ]; then
    cp "$YAML_FILE" "$DEST/skill.yaml"
    echo "スキル定義を配置しました: $DEST/skill.yaml"
fi
