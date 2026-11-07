#!/usr/bin/env bash
# AIエージェントの skills へ SKILL.md / skill.yaml を配置する。
# 使い方: bash scripts/install_skill.sh [muse|gemini|<配置先パス>]
#   muse       -> $HOME/workspace/custom-skills/instant-film-agent (Muse)
#   gemini     -> $HOME/.gemini/config/skills/instant-film-agent (Gemini CLI / Antigravity、既定)
#   antigravity -> gemini と同じ
#   <パス>     -> そのディレクトリへそのまま配置する (従来互換)
# 環境変数 INSTANT_FILM_SKILL_DEST でも指定できる (引数が優先、無指定時の既定は gemini)。
set -euo pipefail

TARGET="${1:-${INSTANT_FILM_SKILL_DEST:-gemini}}"
case "$TARGET" in
  muse) DEST="$HOME/workspace/custom-skills/instant-film-agent" ;;
  gemini|antigravity) DEST="$HOME/.gemini/config/skills/instant-film-agent" ;;
  *) DEST="$TARGET" ;;
esac

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
