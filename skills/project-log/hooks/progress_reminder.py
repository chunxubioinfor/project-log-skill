#!/usr/bin/env python3
"""Hook: reminds Claude to keep the project log up to date. It runs at three moments:

  SessionStart                 if commits landed since the newest log entry, list them and ask Claude to log them
  PostToolUse on `git commit`  the same check, so work does not pile up unlogged during a session
  PostToolUse on an edit       when the progress notes are edited, ask Claude to log the same facts

The notes file is `progress_file` in project-log/project.yaml (default: any PROGRESS.md).

Stdlib only. Comes with the plugin (hooks/hooks.json), or setup_project.py adds it to .claude/settings.json.
Fails open: any problem means silence, never a blocked tool call. Each reminder that follows a tool call
fires at most once per 15 minutes per session, so a burst of edits or commits stays quiet.
"""
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

PROGRESS_NAMES = {"progress.md"}
QUIET_SECONDS = 15 * 60
GIT_COMMIT = re.compile(r"\bgit\b[^\n;&|]*\bcommit\b")
SHOW = 8


def find_log_dir(start: Path):
    return next((d / "project-log" for d in [start, *start.parents] if (d / "project-log" / "project.yaml").exists()), None)


def log_dirs_near(cwd: Path) -> list:
    """The project log of cwd's repo, or else the logs of repos one folder down (sessions started above the repos)."""
    up = find_log_dir(cwd)
    return [up] if up else sorted(p.parent for p in cwd.glob("*/project-log/project.yaml"))


def recently_reminded(kind: str, session: str) -> bool:
    stamp = Path(tempfile.gettempdir()) / f"project-log-{kind}-{session}"
    try:
        if stamp.exists() and time.time() - stamp.stat().st_mtime < QUIET_SECONDS:
            return True
        stamp.touch()
    except OSError:
        pass
    return False


def newest_entry(entries: Path) -> float:
    """Time of the newest entry, from the entries' own `ts:` (file dates change on clone and sync)."""
    newest = 0.0
    for p in entries.glob("*.md"):
        m = re.search(r'^ts:\s*["\']?([^"\'\s#]+)', p.read_text(encoding="utf-8", errors="replace")[:2000], re.M)
        try:
            newest = max(newest, datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).timestamp())
        except (AttributeError, ValueError):
            pass
    return newest


def unlogged_commits(log_dir: Path) -> list:
    """Commits newer than the newest entry that change files outside project-log/, newest first.
    Stops at the first commit that adds entries: the work before it counts as logged."""
    since = newest_entry(log_dir / "entries")
    if not since:
        return []
    git = ["git", "-C", str(log_dir.parent)]
    prefix = subprocess.run(git + ["rev-parse", "--show-prefix"], capture_output=True, text=True, timeout=5).stdout.strip()
    out = subprocess.run(git + ["log", "-n", "200", "--format=%x00%ct %h %s", "--name-only"],
                         capture_output=True, text=True, timeout=5)
    if out.returncode:
        return []
    log_prefix = prefix + log_dir.name + "/"
    found = []
    for block in out.stdout.split("\0")[1:]:
        head, *files = [line for line in block.splitlines() if line]
        ct, commit = head.split(" ", 1)
        if float(ct) <= since or any(f.startswith(log_prefix + "entries/") for f in files):
            break
        if any(not f.startswith(log_prefix) for f in files):
            found.append(commit)
    return found


def catch_up_msg(log_dir: Path, commits: list, at_start: bool) -> str:
    shown = "\n".join(f"- {c}" for c in commits[:SHOW]) + (f"\n- ... and {len(commits) - SHOW} more" if len(commits) > SHOW else "")
    return (
        f"project-log: {len(commits)} commit(s) since the newest entry in {log_dir} are not in the log:\n{shown}\n"
        + ("Before starting new work, log " if at_start else "Log ")
        + "what matters in them (results with numbers, bugs fixed, decisions and their reasons, detours, corrections, "
        "follow-ups) with the skill's new_event.py (--batch for several). If none deserves its own entry, "
        "write one short progress entry that covers them."
    )


def emit(event: str, msg: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg}}))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    event = data.get("hook_event_name") or "PostToolUse"
    session = data.get("session_id", "x")
    ti = data.get("tool_input") or {}

    if event == "SessionStart" or data.get("tool_name") == "Bash":
        if event != "SessionStart" and not GIT_COMMIT.search(ti.get("command") or ""):
            return
        behind = [(d, c) for d in log_dirs_near(Path(data.get("cwd") or ".").resolve()) for c in [unlogged_commits(d)] if c]
        if behind and (event == "SessionStart" or not recently_reminded("commit", session)):
            emit(event, "\n\n".join(catch_up_msg(d, c, event == "SessionStart") for d, c in behind))
        return

    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if not path:
        return
    # only in projects that use project-log
    log_dir = find_log_dir(Path(path).resolve().parent)
    if not log_dir:
        return
    m = re.search(r'^progress_file:\s*["\']?([^"\'#\n]*?)["\']?\s*(?:#.*)?$', (log_dir / "project.yaml").read_text(encoding="utf-8"), re.M)
    if m and m.group(1).strip():
        if Path(path).resolve() != (log_dir.parent / m.group(1).strip()).resolve():
            return
    elif Path(path).name.lower() not in PROGRESS_NAMES:
        return
    name = m.group(1).strip() if m and m.group(1).strip() else Path(path).name
    if recently_reminded("remind", session):
        return
    emit("PostToolUse", (
        f"{name} was updated. This project keeps a structured log in {log_dir} (skill: project-log). "
        "For each new fact in this update (a bug fixed, decision and its reason, result with numbers, correction, "
        "detour, follow-up, or question for the supervisor), write the matching log entry now with the skill's "
        "new_event.py (use --batch for several). Skip anything already logged this session."
    ))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001  fail open
        pass
    sys.exit(0)
