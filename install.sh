#!/usr/bin/env bash
# Install or update the project-log skill into ~/.claude/skills/project-log (copies, not a symlink).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/project-log"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/project-log"
mkdir -p "$DEST"
rsync -a --delete --exclude '__pycache__' --exclude '* 2.*' --exclude '.DS_Store' "$SRC/" "$DEST/"
chmod +x "$DEST"/scripts/*.py "$DEST"/hooks/*.py
VERSION=$(grep -o 'TEMPLATE_VERSION = "[^"]*"' "$DEST/scripts/plog.py" | cut -d'"' -f2)
echo "installed project-log $VERSION -> $DEST"
command -v uv >/dev/null || echo "note: uv not found; logging works, but building the page needs uv (https://docs.astral.sh/uv/)"
