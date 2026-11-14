#!/usr/bin/env python3
"""Set up project-log in a repo. Safe to run again: every step is idempotent.

Stdlib only. Run from the repo root after the kickoff round (see references/setup.md):

  setup_project.py --title "..." --owner "Alex Doe" --group "Example Lab, Example University" \\
      --audience layered --tabs overview,timeline,results,side,loops,next,digests,glossary,changelog \\
      --conventions "The baseline is amber, the variant under test is teal." \\
      --progress-file docs/PROGRESS.md \\
      --thread "baseline|Baseline|main|Run the standard pipeline and lock it as the reference"

  setup_project.py --hooks-only --settings /path/to/parent/.claude/settings.json
      # add the hook to another settings file too (e.g. a cluster where sessions start one folder up)

What it does
  1. project-log/ folders, and project.yaml if it does not exist yet (never overwritten)
  2. a "Project log" section in CLAUDE.md, between markers (replaced on rerun, never duplicated)
  3. the progress-notes reminder hook in .claude/settings.json (added once)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plog  # noqa: E402

START, END = "<!-- project-log:start -->", "<!-- project-log:end -->"
HOOK_ID = "project-log/hooks/progress_reminder.py"
SKILL_DIR = Path(__file__).resolve().parents[1]
# Installed as a plugin, the plugin's own hooks/hooks.json runs the reminder in every project: nothing to add.
AS_PLUGIN = "/plugins/cache/" in SKILL_DIR.as_posix()


def hook_cmd() -> str:
    """Runs this installed copy's hook, written as $HOME/... so a committed settings.json works for collaborators.
    Silent where the file is missing (e.g. a collaborator on the plugin, whose own hook covers it)."""
    f = SKILL_DIR / "hooks" / "progress_reminder.py"
    try:
        f = "$HOME/" + f.relative_to(Path.home().resolve()).as_posix()
    except ValueError:
        f = f.as_posix()
    return f'f="{f}"; [ -f "$f" ] && python3 "$f" || true'

def claude_section(owner: str, progress_file: str) -> str:
    who = owner.split()[0] if owner else "the user"
    return f"""{START}
## Project log (skill: project-log)

This repo keeps a structured, append-only log in `project-log/`. The page `project-log/report/project-log.html` is built from it; never edit the page by hand.

- **Log as you go.** When a bug is fixed, a decision is made, a result has numbers, an approach is dropped, an earlier claim turns out wrong, or something is left for later, write the entry right away with the project-log skill (`new_event.py`). Every update to `{progress_file}` should have matching log entries.
- **Never edit or delete an entry.** Mistakes get a `correction` entry; finished follow-ups get an entry that resolves them.
- **Results need a "so what"** and their provenance (script, run manifest, data).
- **At the end of a session,** do the project-log wrap-up: list what was logged and what is still open, ask {who} what to add, write a session digest.
- **"Update the project log"** means: refresh the overview in `project-log/project.yaml`, run the build, and report what changed. Commit it following the rules above.
{END}
"""


def yaml_field(log_dir: Path, key: str) -> str:
    """Read one top-level scalar from project.yaml without PyYAML."""
    p = log_dir / "project.yaml"
    if not p.exists():
        return ""
    m = re.search(rf'^{key}:\s*["\']?([^"\'#\n]*?)["\']?\s*(?:#.*)?$', p.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else ""


def repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start,
                             capture_output=True, text=True, check=True).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def write_project_yaml(log_dir: Path, a) -> str:
    p = log_dir / "project.yaml"
    if p.exists():
        return f"kept existing {p}"
    lines = [f"title: {yaml_str(a.title)}"]
    if a.lede:
        lines.append(f"lede: {yaml_str(a.lede)}")
    lines += [f"owner: {yaml_str(a.owner)}"] if a.owner else []
    lines += [f"group: {yaml_str(a.group)}"] if a.group else []
    lines.append(f"audience: {a.audience}")
    lines.append(f"progress_file: {yaml_str(a.progress_file)}")
    lines.append(f"tabs: [{', '.join(a.tabs)}]")
    lines += ["figures:", f"  plotly: {a.plotly}"] + ([f"  conventions: {yaml_str(a.conventions)}"] if a.conventions else [])
    lines.append("threads:")
    for t in a.thread or ["main|Main work|main|"]:
        tid, name, kind, goal, status = (t.split("|") + ["", "", "", "", ""])[:5]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", tid):
            raise SystemExit(f"thread id '{tid}' must be short, lowercase letters, digits, - or _")
        if status and status not in ("active", "done", "paused"):
            raise SystemExit(f"thread {tid}: status must be active, done or paused, not '{status}'")
        bare = re.fullmatch(r"[a-z][a-z0-9_-]*", tid) and tid not in ("y", "n", "yes", "no", "on", "off", "true", "false", "null")
        lines += [f"  - id: {tid if bare else yaml_str(tid)}", f"    name: {yaml_str(name)}", f"    kind: {kind or 'main'}",
                  f"    status: {status or 'active'}"] + ([f"    goal: {yaml_str(goal)}"] if goal else [])
    lines += ["overview:", "  summary: []", "  tiles: []"]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"wrote {p}"


def patch_claude_md(root: Path, section: str) -> str:
    p = root / "CLAUDE.md"
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", lambda m: section, text, flags=re.S)
        verb = "updated"
    else:
        new = text.rstrip("\n") + ("\n\n" if text else "") + section
        verb = "added"
    if new == text:
        return f"CLAUDE.md section already current ({p})"
    p.write_text(new, encoding="utf-8")
    return f"{verb} the Project log section in {p}"


def patch_settings(path: Path) -> str:
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return f"SKIPPED {path}: not valid JSON, add the hook by hand (see references/setup.md)"
    hooks = data.setdefault("hooks", {}) if isinstance(data, dict) else None
    post = hooks.setdefault("PostToolUse", []) if isinstance(hooks, dict) else None
    if not isinstance(post, list) or not all(isinstance(g, dict) and isinstance(g.get("hooks", []), list) for g in post):
        return f"SKIPPED {path}: unexpected layout, add the hook by hand (see references/setup.md)"
    if any(HOOK_ID in h.get("command", "") for grp in post for h in grp.get("hooks", []) if isinstance(h, dict)):
        return f"hook already present in {path}"
    post.append({"matcher": "Edit|Write|MultiEdit|NotebookEdit",
                 "hooks": [{"type": "command", "command": hook_cmd(), "timeout": 10}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"added the progress-notes reminder hook to {path}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title"), ap.add_argument("--lede"), ap.add_argument("--owner"), ap.add_argument("--group")
    ap.add_argument("--audience", default="layered", choices=["layered", "self", "others", "non-technical"])
    ap.add_argument("--tabs", default=",".join(plog.ALL_TABS), type=lambda s: [t.strip() for t in s.split(",") if t.strip()])
    ap.add_argument("--conventions", help="figure conventions agreed in the kickoff round")
    ap.add_argument("--plotly", choices=["link", "embed"], default="link",
                    help="charts: load the chart library from a CDN (small page, needs internet) or embed it (about 5 MB, offline)")
    ap.add_argument("--thread", action="append", help='"id|name|main or side|goal[|active, done or paused]" (repeatable; status defaults to active)')
    ap.add_argument("--progress-file", help="the hand-written progress notes the hook watches "
                    "(default: docs/PROGRESS.md if it exists, else PROGRESS.md)")
    ap.add_argument("--settings", action="append", default=[], help="extra settings.json to add the hook to")
    ap.add_argument("--hooks-only", action="store_true")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args()
    bad = [t for t in a.tabs if t not in plog.ALL_TABS]
    if bad:
        ap.error(f"unknown tab(s): {', '.join(bad)}")
    root = repo_root(Path(a.repo).resolve())
    report = []
    if not a.hooks_only:
        log_dir = root / plog.LOG_DIR_NAME
        for sub in ("entries", "figures/scripts", "figures/out", "report"):
            (log_dir / sub).mkdir(parents=True, exist_ok=True)
        if not (log_dir / "project.yaml").exists() and not a.title:
            ap.error("--title is required for a new project")
        if not a.progress_file:
            a.progress_file = yaml_field(log_dir, "progress_file") or (
                "docs/PROGRESS.md" if (root / "docs" / "PROGRESS.md").exists() else "PROGRESS.md")
        report.append(write_project_yaml(log_dir, a))
        owner = yaml_field(log_dir, "owner") or a.owner or ""
        report.append(patch_claude_md(root, claude_section(owner, yaml_field(log_dir, "progress_file") or a.progress_file)))
        if AS_PLUGIN:
            report.append("reminder hook: comes with the project-log plugin, nothing added to .claude/settings.json")
        else:
            report.append(patch_settings(root / ".claude" / "settings.json"))
        parent_claude = root.parent / ".claude"
        if parent_claude.is_dir() and not a.settings and not AS_PLUGIN:
            report.append(f"NOTE: {parent_claude} exists. If Claude Code sessions start in {root.parent}, "
                          f"also run: setup_project.py --hooks-only --settings {parent_claude / 'settings.json'}")
    for s in a.settings:
        report.append(patch_settings(Path(s).expanduser()))
    print("\n".join(report))


if __name__ == "__main__":
    main()
