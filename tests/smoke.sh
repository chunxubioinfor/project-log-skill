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
[ "$(ls project-log/entries | wc -l | tr -d ' ')" = "34" ] && pass "34 entries" || fail "34 entries"
grep -q 'cdnjs.cloudflare.com/ajax/libs/plotly.js' project-log/report/project-log.html && [ "$(wc -c < project-log/report/project-log.html)" -lt 1000000 ] \
  && pass "linked chart library keeps the page small" || fail "linked chart library keeps the page small"

f=$(ls project-log/entries/*-bug-*.md | head -1); cp "$f" "$T/keep"; echo "edited" >> "$f"
uv run --quiet "$PL/validate.py" > /dev/null 2>&1 && fail "edited published entry is refused" || pass "edited published entry is refused"
cp "$T/keep" "$f"

g=project-log/figures/out/switch_overview.json; cp "$g" "$T/keepfig"; echo '{}' > "$g"
uv run --quiet "$PL/validate.py" > /dev/null 2>&1 && fail "changed published figure is refused" || pass "changed published figure is refused"
cp "$T/keepfig" "$g"

cp "$f" "${f%.md} 2.md"
out=$(uv run --quiet "$PL/validate.py" 2>&1 || true)
echo "$out" | grep -q "file-sync tool" && pass "sync-tool copy is detected" || fail "sync-tool copy is detected"
rm "${f%.md} 2.md"

echo '[{"type":"decision","thread":"switch","title":"x","resolves":"@nope"}]' | python3 "$PL/new_event.py" --batch - > /dev/null 2>&1 \
  && fail "unknown @ref is refused" || pass "unknown @ref is refused"

H="$ROOT/skills/project-log/hooks/progress_reminder.py"
echo "{\"session_id\":\"smoke$$\",\"tool_input\":{\"file_path\":\"$T/demo/docs/PROGRESS.md\"}}" | python3 "$H" | grep -q additionalContext \
  && pass "hook reminds after a progress-notes edit" || fail "hook reminds after a progress-notes edit"
quiet=$(echo "{\"session_id\":\"smoke$$b\",\"tool_input\":{\"file_path\":\"$T/demo/README.md\"}}" | python3 "$H")
[ -z "$quiet" ] && pass "hook stays quiet for other files" || fail "hook stays quiet for other files"

n=$(ls project-log/entries | wc -l)
echo '[{"type":"followup","thread":"switch","title":"ok"},{"type":"result","thread":"switch","title":"no so-what"}]' \
  | python3 "$PL/new_event.py" --batch - > /dev/null 2>&1 && fail "bad batch is refused" || true
[ "$(ls project-log/entries | wc -l)" = "$n" ] && pass "a bad batch writes nothing" || fail "a bad batch writes nothing"

python3 "$PL/new_event.py" --type progress --thread switch --ts 2026-11-01T09:00:00Z \
  --title "$(python3 -c 'print("Removed <!-- TODO --> and </script> markers \x80 pasted from a PDF")')" \
  --body $'First part.\n\n---\n\nSecond part, see [docs](https://e.com/"onmouseover="alert(1)) and [[R&D]].' > /dev/null
python3 "$PL/new_event.py" --type term --title 'R&D' --body "Research and development." > /dev/null
uv run --quiet "$PL/validate.py" > /dev/null && pass "a Z timestamp validates" || fail "a Z timestamp validates"
uv run --quiet "$PL/build.py" > /dev/null
python3 - project-log/report/project-log.html <<'EOF' && pass "tricky text survives the page" || fail "tricky text survives the page"
import json, re, sys
page = open(sys.argv[1], encoding="utf-8").read()
data = re.search(r'id="plog-data"[^>]*>(.*?)</script>', page, re.S).group(1)
s = json.dumps(json.loads(data))           # the embedded log must be valid JSON
assert "Second part" in s, "body cut at ---"
assert 'onmouseover=\\"' not in s, "link attribute injection"
assert 'data-term=\\"r&amp;d\\"' in s, "term key escaped twice"
assert "<table>" in s.replace("\\u003c", "<"), "QC table not rendered"
assert '"image": "data:image/png;base64,' in s, "image figure not embedded"
EOF

uv run --quiet "$PL/validate.py" > /dev/null && pass "demo still validates after the checks" || fail "demo still validates"
echo "smoke test passed"
