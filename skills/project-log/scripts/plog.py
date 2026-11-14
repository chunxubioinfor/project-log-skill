"""Shared helpers for the project-log scripts.

Stdlib only at import time, so new_event.py and provenance.py run on any
machine. Functions that parse YAML import PyYAML lazily (build/validate run
through `uv run`, which provides it).
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR_NAME = "project-log"
TEMPLATE_VERSION = "0.3.0"

TYPES = {
    "progress": "Progress",
    "result": "Result",
    "bug": "Bug fixed",
    "blocker": "Blocker",
    "detour": "Detour",
    "decision": "Decision",
    "correction": "Correction",
    "followup": "Follow-up",
    "question": "Needs a decision",
    "milestone": "Milestone",
    "plan": "Next step",
    "paper": "Paper",
    "session": "Session digest",
    "term": "Glossary term",
    "thread": "Thread",
}
# Types that stay "open" until a later entry resolves them.
LOOP_TYPES = {"followup", "blocker", "question", "plan"}
VERDICTS = {"kept", "kept-after-review", "archived", "pivoted", "iterate", "corrected", "open", "abandoned"}
ALL_TABS = ["overview", "timeline", "results", "side", "loops", "next", "digests", "glossary", "changelog"]


# ---------------------------------------------------------------- locations

def find_log_dir(start: Path | None = None) -> Path:
    """Walk up from `start` to the folder holding project-log/project.yaml."""
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        cand = d / LOG_DIR_NAME
        if (cand / "project.yaml").exists():
            return cand
        if d.name == LOG_DIR_NAME and (d / "project.yaml").exists():
            return d
    raise SystemExit(
        f"No {LOG_DIR_NAME}/project.yaml found above {here}. "
        "Run the project-log setup first (see SKILL.md, workflow 1)."
    )


def repo_root(path: Path) -> Path | None:
    out = _git(["rev-parse", "--show-toplevel"], path)
    return Path(out) if out else None


def _git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


# ---------------------------------------------------------------- provenance

def git_state(cwd: Path) -> dict:
    """Commit, short hash, branch and dirty flag of the whole repo containing cwd.

    dirty = tracked files changed anywhere in the repo (code, configs, docs),
    except the project log itself, which changes on every entry and build.
    log_uncommitted = entry files / project.yaml not yet committed (incl. never-added).
    """
    commit = _git(["rev-parse", "HEAD"], cwd)
    if not commit:
        return {}
    status = _git(["status", "--porcelain", "--untracked-files=no", "--", ":(top)",
                   f":(exclude,top){LOG_DIR_NAME}"], cwd)
    log_status = _git(["status", "--porcelain", "--untracked-files=all", "--",
                       f":(top){LOG_DIR_NAME}/entries", f":(top){LOG_DIR_NAME}/project.yaml"], cwd)
    return {
        "git_commit": commit[:7],
        "git_commit_full": commit,
        "git_branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd),
        "git_dirty": bool(status),
        "log_uncommitted": len([l for l in log_status.splitlines() if l.strip()]),
    }


IMAGE_TYPES = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp"}   # figures that are pictures (R, ggplot, tools' own plots), shown as they are


def sha256_file(path: Path, limit_mb: int = 2048) -> str | None:
    """sha256 of a file; None for missing files or files above `limit_mb`."""
    if not path.is_file() or path.stat().st_size > limit_mb * 1024 * 1024:
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_to(path: Path, root: Path | None) -> str:
    path = path.resolve()
    if root:
        try:
            return str(path.relative_to(root.resolve()))
        except ValueError:
            pass
    return str(path)


# ---------------------------------------------------------------- time / ids

def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen].rstrip("-")) or "entry"


def make_id(ts: str, etype: str, title: str) -> str:
    """2026-10-12T0732-detour-comparison-script (date-only ts -> 2026-10-12-...)."""
    if "T" in ts:
        day, clock = ts.split("T", 1)
        stamp = f"{day}T{clock[:2]}{clock[3:5]}"
    else:
        stamp = ts[:10]
    return f"{stamp}-{etype}-{slugify(title)}"


def sort_key(ts: str, etype: str = "") -> str:
    """Sortable string for full or date-only timestamps.

    Date-only entries sort at noon, except session digests, which close their day.
    """
    ts = str(ts)
    if "T" in ts:
        try:  # compare instants, so entries logged in different time zones interleave correctly
            d = datetime.fromisoformat(re.sub(r"Z$", "+00:00", ts))
            return (d.astimezone(timezone.utc) if d.tzinfo else d).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return ts
    return f"{ts}T23:59:59" if etype == "session" else f"{ts}T12:00:00"


# ---------------------------------------------------------------- YAML front matter

_YAML_UNSAFE = re.compile("[\x7f-\x9f\u2028\u2029\ufeff]")


def dump_front_matter(data: dict) -> str:
    """Minimal YAML emitter: block mappings/lists, JSON-quoted scalars.

    JSON string literals are valid YAML double-quoted scalars, so this stays
    stdlib-only and round-trips through PyYAML safely.
    """
    lines: list[str] = []

    def scalar(v):
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return json.dumps(v)
        # escape what YAML reads as a line break or rejects (C1 controls, NEL, LS/PS, BOM), e.g. text pasted from a PDF
        return _YAML_UNSAFE.sub(lambda m: "\\u%04x" % ord(m.group()), json.dumps(str(v), ensure_ascii=False))

    def emit(obj, indent):
        pad = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)) and v:
                    lines.append(f"{pad}{k}:")
                    emit(v, indent + 1)
                elif isinstance(v, (dict, list)):
                    lines.append(f"{pad}{k}: {'{}' if isinstance(v, dict) else '[]'}")
                else:
                    lines.append(f"{pad}{k}: {scalar(v)}")
        else:  # list
            for item in obj:
                if isinstance(item, dict) and item:
                    first = True
                    for k, v in item.items():
                        lead = f"{pad}- " if first else f"{pad}  "
                        first = False
                        if isinstance(v, (dict, list)) and v:
                            lines.append(f"{lead}{k}:")
                            emit(v, indent + 2)
                        else:
                            lines.append(f"{lead}{k}: {scalar(v) if not isinstance(v, (dict, list)) else ('{}' if isinstance(v, dict) else '[]')}")
                else:
                    lines.append(f"{pad}- {scalar(item)}")

    emit(data, 0)
    return "---\n" + "\n".join(lines) + "\n---\n"


def split_front_matter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        raise ValueError("entry has no YAML front matter (must start with ---)")
    m = re.match(r"---[ \t]*\n(.*?)^---[ \t]*$\n?(.*)", text, re.S | re.M)
    if not m:
        raise ValueError("front matter is not closed with ---")
    return m.group(1), m.group(2)  # the body keeps any later "---" lines (rules, tables)


def load_yaml(text: str):
    import yaml  # provided by uv run --with pyyaml

    return yaml.safe_load(text)


def load_project(log_dir: Path) -> dict:
    return load_yaml((log_dir / "project.yaml").read_text(encoding="utf-8")) or {}


# "name 2.md", "name (1).md", Syncthing/Dropbox conflict names: copies made by file-sync tools
# (entry ids never contain spaces, so only names with spaces/brackets or Syncthing's marker match)
CONFLICT = re.compile(r"( \d+| \(\d+\)| \([^)]*conflict[^)]*\)|\.sync-conflict-[^/]*)\.md$", re.I)


def conflict_copies(log_dir: Path) -> list[Path]:
    return [p for p in sorted((log_dir / "entries").glob("*.md")) if CONFLICT.search(p.name)]


def load_entries(log_dir: Path) -> list[dict]:
    """All entries, oldest first. Each dict gets _path, _body, _sha.

    Sync-conflict copies are skipped here; validate.py reports them.
    """
    entries = []
    for p in sorted((log_dir / "entries").glob("*.md")):
        if CONFLICT.search(p.name):
            continue
        raw = p.read_text(encoding="utf-8-sig")  # an editor may have added a byte-order mark
        try:
            head, body = split_front_matter(raw)
            meta = load_yaml(head) or {}
        except Exception as exc:  # name the file, or one bad entry hides which one blocks the build
            raise ValueError(f"{p.name}: {exc}") from None
        meta["_path"] = p
        meta["_body"] = body.strip()
        meta["_sha"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if meta.get("ts") is not None:
            meta["ts"] = _ts_str(meta["ts"])
        entries.append(meta)
    entries.sort(key=lambda e: (sort_key(e.get("ts", ""), e.get("type", "")), e.get("id", "")))
    return entries


def _ts_str(v) -> str:
    # PyYAML turns unquoted timestamps into datetime/date objects.
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


# ---------------------------------------------------------------- markdown

_TERM = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def term_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def md_inline(text: str) -> str:
    s = html.escape(text)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\w)", r"<i>\1</i>", s)
    s = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        s,
    )
    s = _TERM.sub(
        lambda m: '<span class="term" tabindex="0" data-term="{}">{}</span>'.format(
            html.escape(term_key(html.unescape(m.group(1)))), m.group(2) or m.group(1)
        ),
        s,
    )
    return s


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def md_table(rows: list[str]) -> str:
    """A pipe table: header row, |---|---:| separator (a colon on the right aligns that column right), body rows."""
    head, aligns = _cells(rows[0]), _cells(rows[1])
    right = [a.endswith(":") and not a.startswith(":") for a in aligns]

    def row(cells, tag):
        cells = (cells + [""] * len(head))[:len(head)]
        return "<tr>" + "".join(f'<{tag}{" class=num" if right[i] else ""}>{md_inline(c)}</{tag}>'
                                for i, c in enumerate(cells)) + "</tr>"
    return ('<div class="mdtable"><table><thead>' + row(head, "th") + "</thead><tbody>" +
            "".join(row(_cells(r), "td") for r in rows[2:]) + "</tbody></table></div>")


_TABLE_SEP = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")


def md_block(text: str) -> str:
    """Paragraphs, '- ' lists, '> ' quotes and pipe tables. Enough for log entries."""
    out, para, items, table = [], [], [], []

    def flush():
        if table:
            out.append(md_table(table) if len(table) >= 2 and _TABLE_SEP.match(table[1])
                       else "<p>" + md_inline(" ".join(table)) + "</p>")
            table.clear()
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{md_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in text.splitlines():
        st = line.strip()
        if not st:
            flush()
        elif st.startswith("|") and (table or not para):
            if items:
                flush()
            table.append(st)
        elif re.match(r"^[-*] ", st):
            if para:
                flush()
            items.append(st[2:])
        elif items and line.startswith("  "):
            items[-1] += " " + st
        else:
            if items or table:
                flush()
            para.append(st.lstrip("> ").strip() if st.startswith(">") else st)
    flush()
    return "\n".join(out)


def terms_used(text: str) -> list[str]:
    return [term_key(m.group(1)) for m in _TERM.finditer(text or "")]
