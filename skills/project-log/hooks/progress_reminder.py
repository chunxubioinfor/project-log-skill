#!/usr/bin/env python3
"""PostToolUse hook: after the progress notes are edited, remind Claude to log the same facts.

The notes file is `progress_file` in project-log/project.yaml (default: any PROGRESS.md).

Stdlib only. Installed by setup_project.py into the project's .claude/settings.json.
Fails open: any problem means silence, never a blocked tool call. Reminds at most
once per 15 minutes per session, so a burst of PROGRESS.md edits stays quiet.
"""
import json
import re
import sys
import tempfile
import time
from pathlib import Path

PROGRESS_NAMES = {"progress.md"}
QUIET_SECONDS = 15 * 60


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if not path:
        return
    # only in projects that use project-log
    here = Path(path).resolve().parent
    log_dir = next((d / "project-log" for d in [here, *here.parents] if (d / "project-log" / "project.yaml").exists()), None)
    if not log_dir:
        return
    m = re.search(r'^progress_file:\s*["\']?([^"\'#\n]*?)["\']?\s*(?:#.*)?$', (log_dir / "project.yaml").read_text(encoding="utf-8"), re.M)
    if m and m.group(1).strip():
        if Path(path).resolve() != (log_dir.parent / m.group(1).strip()).resolve():
            return
    elif Path(path).name.lower() not in PROGRESS_NAMES:
        return
    name = m.group(1).strip() if m and m.group(1).strip() else Path(path).name
    stamp = Path(tempfile.gettempdir()) / f"project-log-remind-{data.get('session_id', 'x')}"
    try:
        if stamp.exists() and time.time() - stamp.stat().st_mtime < QUIET_SECONDS:
            return
        stamp.touch()
    except OSError:
        pass
    msg = (
        f"{name} was updated. This project keeps a structured log in {log_dir} (skill: project-log). "
        "For each new fact in this update (a bug fixed, decision and its reason, result with numbers, correction, "
        "detour, follow-up, or question for the supervisor), write the matching log entry now with the skill's "
        "new_event.py (use --batch for several). Skip anything already logged this session."
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001  fail open
        pass
    sys.exit(0)
