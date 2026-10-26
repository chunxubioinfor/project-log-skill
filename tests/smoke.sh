#!/usr/bin/env bash
# Smoke test: build the demo from scratch, then check that the guarantees hold.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PL="$ROOT/skills/project-log/scripts"
T="$ROOT/.test/smoke"
rm -rf "$T"
PL="$PL" "$ROOT/examples/demo/make_demo.sh" "$T/demo" > /dev/null
cd "$T/demo"
pass() { echo "  ok  $1"; }
fail() { echo "  FAIL $1"; exit 1; }

uv run --quiet "$PL/validate.py" > /dev/null && pass "demo validates" || fail "demo validates"
grep -q 'id="plog-data"' project-log/report/project-log.html && pass "page embeds the log" || fail "page embeds the log"
[ "$(ls project-log/entries | wc -l | tr -d ' ')" = "15" ] && pass "15 entries" || fail "15 entries"

f=$(ls project-log/entries/*-bug-*.md | head -1); cp "$f" "$T/keep"; echo "edited" >> "$f"
uv run --quiet "$PL/validate.py" > /dev/null 2>&1 && fail "edited published entry is refused" || pass "edited published entry is refused"
cp "$T/keep" "$f"

g=project-log/figures/out/batch_effect_v2.json; cp "$g" "$T/keepfig"; echo '{}' > "$g"
uv run --quiet "$PL/validate.py" > /dev/null 2>&1 && fail "changed published figure is refused" || pass "changed published figure is refused"
cp "$T/keepfig" "$g"

cp "$f" "${f%.md} 2.md"
out=$(uv run --quiet "$PL/validate.py" 2>&1 || true)
echo "$out" | grep -q "file-sync tool" && pass "sync-tool copy is detected" || fail "sync-tool copy is detected"
rm "${f%.md} 2.md"

echo '[{"type":"decision","thread":"norm-v2","title":"x","resolves":"@nope"}]' | python3 "$PL/new_event.py" --batch - > /dev/null 2>&1 \
  && fail "unknown @ref is refused" || pass "unknown @ref is refused"

H="$ROOT/skills/project-log/hooks/progress_reminder.py"
echo "{\"session_id\":\"smoke$$\",\"tool_input\":{\"file_path\":\"$T/demo/docs/PROGRESS.md\"}}" | python3 "$H" | grep -q additionalContext \
  && pass "hook reminds after a progress-notes edit" || fail "hook reminds after a progress-notes edit"
quiet=$(echo "{\"session_id\":\"smoke$$b\",\"tool_input\":{\"file_path\":\"$T/demo/README.md\"}}" | python3 "$H")
[ -z "$quiet" ] && pass "hook stays quiet for other files" || fail "hook stays quiet for other files"

uv run --quiet "$PL/validate.py" > /dev/null && pass "demo still validates after the checks" || fail "demo still validates"
echo "smoke test passed"
