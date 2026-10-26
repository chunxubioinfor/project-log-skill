# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6", "plotly>=5"]
# ///
"""Build project-log/report/project-log.html from the log. Validates first.

  uv run build.py                    # from anywhere inside the project
  uv run build.py --accept-edits     # allow (and record) edits to published entries
  uv run build.py --dry-run          # validate and assemble, write nothing
  uv run build.py --draft            # review page incl. unreviewed imports -> report/draft.html
                                     # (not published: build history and hashes are not touched)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plog  # noqa: E402
import validate as V  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MARKER = re.compile(r"/\*__(CSS|APP|PLOTLY)__\*/|__(DATA|TITLE|VERSION)__")


def category(etype: str) -> str:
    return {
        "result": "result", "milestone": "result",
        "bug": "bug", "blocker": "bug",
        "detour": "detour", "correction": "detour",
        "decision": "decision", "question": "decision",
        "followup": "open", "plan": "open",
    }.get(etype, "progress")


def plotly_js() -> str:
    try:
        import plotly
    except ImportError:
        raise SystemExit("build: figures need Plotly. Run with: uv run build.py")
    p = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    return p.read_text(encoding="utf-8")


def assemble(log_dir: Path, ctx: dict, built_at: str) -> tuple[dict, bool]:
    project, entries, threads = ctx["project"], ctx["entries"], ctx["threads"]
    base = log_dir.parent
    report_dir = log_dir / "report"

    # loop status: open until some later entry resolves it
    resolved_by: dict[str, str] = {}
    corrected_by: dict[str, list[str]] = {}
    for e in entries:
        refs = e.get("refs") or {}
        for t in refs.get("resolves") or []:
            resolved_by.setdefault(t, e["id"])
        for t in refs.get("corrects") or []:
            corrected_by.setdefault(t, []).append(e["id"])

    # glossary + first use
    glossary = {}
    for e in entries:
        if e.get("type") == "term":
            glossary[plog.term_key(e["title"])] = {
                "term": e["title"], "aliases": e.get("aliases") or [],
                "html": plog.md_block(e["_body"]), "text": re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
                                                              lambda m: m.group(2) or m.group(1), e["_body"]),
                "id": e["id"], "first": None,
            }
    alias_to_key = {}
    for k, g in glossary.items():
        alias_to_key[k] = k
        for a in g["aliases"]:
            alias_to_key[plog.term_key(a)] = k
    for e in entries:
        if e.get("type") == "term":
            continue
        for t in plog.terms_used(e["_body"]):
            k = alias_to_key.get(t)
            if k and not glossary[k]["first"]:
                glossary[k]["first"] = e["id"]

    figures, has_fig = {}, False
    out_entries = []
    for e in entries:
        ts = str(e["ts"])
        item = {
            "id": e["id"], "ts": ts, "date": ts[:10],
            "time": ts[11:16] if "T" in ts else None,
            "type": e["type"], "label": plog.TYPES.get(e["type"], e["type"]),
            "cat": category(e["type"]), "thread": e.get("thread"),
            "title": e["title"], "html": plog.md_block(e["_body"]),
            "verdict": e.get("verdict"), "imported": bool(e.get("imported")),
            "refs": e.get("refs") or {}, "aliases": e.get("aliases") or [],
            "corrected_by": corrected_by.get(e["id"], []),
        }
        if e["type"] in plog.LOOP_TYPES:
            closed = e.get("status") == "closed" or e["id"] in resolved_by
            item["status"] = "closed" if closed else "open"
            item["resolved_by"] = resolved_by.get(e["id"])
        if e.get("provenance"):
            item["prov"] = e["provenance"]
        if e.get("result"):
            r = dict(e["result"])
            r["so_what_html"] = plog.md_inline(r.get("so_what", ""))
            if r.get("figure"):
                fig_path = base / r["figure"]
                figures[r["id"]] = json.loads(fig_path.read_text(encoding="utf-8"))
                r["figure_key"] = r["id"]
                has_fig = True
            if r.get("static"):
                r["static_href"] = os.path.relpath(base / r["static"], report_dir)
            item["result"] = r
        if e.get("paper"):
            item["paper"] = e["paper"]
        out_entries.append(item)

    # what changed since the previous build
    manifest = ctx["manifest"]
    prev = manifest.get("builds", [])[-1] if manifest.get("builds") else None
    published = set(manifest.get("entries", {}))
    new_ids = [e["id"] for e in entries if e["id"] not in published]
    changed = {"since": prev["built_at"] if prev else None, "entries": new_ids, "first_build": prev is None}

    overview = project.get("overview") or {}
    git = plog.git_state(log_dir)
    data = {
        "project": {
            "title": project.get("title", "Project log"),
            "lede": project.get("lede", ""),
            "eyebrow": " · ".join(x for x in ["Project log", project.get("group"), project.get("owner")] if x),
            "tabs": project.get("tabs") or plog.ALL_TABS,
        },
        "stamp": {
            "built_at": built_at,
            "git_commit": git.get("git_commit"), "git_dirty": git.get("git_dirty", False),
            "log_uncommitted": git.get("log_uncommitted", 0),
            "n_entries": len(entries), "template_version": plog.TEMPLATE_VERSION,
        },
        "today": built_at[:10],
        "threads": [
            {"id": t["id"], "name": t["name"], "kind": t.get("kind", "main"),
             "status": t.get("status", "active"), "goal": t.get("goal", "")}
            for t in project.get("threads") or []
        ],
        "entries": out_entries,
        "figures": figures,
        "glossary": glossary,
        "alias": alias_to_key,
        "overview": {
            # items are strings, or {label, text} to override the default column headings
            "summary": [
                {"label": p.get("label"), "html": plog.md_inline(p.get("text", ""))} if isinstance(p, dict)
                else {"label": None, "html": plog.md_inline(str(p))}
                for p in overview.get("summary") or []
            ],
            "tiles": overview.get("tiles") or [],
            "figure": overview.get("figure"),   # optional R-number shown on the Overview
        },
        "changed": changed,
        "builds": manifest.get("builds", []),
    }
    return data, has_fig


def render(data: dict, has_fig: bool) -> str:
    template = (ASSETS / "template.html").read_text(encoding="utf-8")
    # U+FFFD is escaped (same meaning in JSON/JS) so publishing tools don't mistake it for a lost character
    payload = (json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
               .replace("�", "\\ufffd"))
    parts = {
        "CSS": (ASSETS / "theme.css").read_text(encoding="utf-8"),
        "APP": (ASSETS / "app.js").read_text(encoding="utf-8"),
        "PLOTLY": plotly_js().replace("</script", "<\\/script").replace("�", "\\uFFFD") if has_fig else "",
        "DATA": payload,
        "TITLE": _esc(data["project"]["title"]),
        "VERSION": plog.TEMPLATE_VERSION,
    }
    # one pass, so inserted content is never re-scanned for markers
    return MARKER.sub(lambda m: parts[m.group(1) or m.group(2)], template)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log-dir")
    ap.add_argument("--accept-edits", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--draft", action="store_true", help="allow unreviewed imports; write report/draft.html only")
    a = ap.parse_args()
    log_dir = Path(a.log_dir).resolve() if a.log_dir else plog.find_log_dir()

    errors, warnings, ctx = V.validate(log_dir, a.accept_edits, draft=a.draft)
    V.report(errors, warnings, len(ctx.get("entries", [])))
    if errors:
        print("build: stopped. Fix the errors above, then build again.")
        sys.exit(1)

    built_at = datetime.now().astimezone().replace(microsecond=0).isoformat()
    data, has_fig = assemble(log_dir, ctx, built_at)

    # this build's record (drives the Changelog and the append-only check)
    entries = ctx["entries"]
    manifest = ctx["manifest"]
    new_ids = data["changed"]["entries"]
    new_set = set(new_ids)
    closed = sorted({t for e in entries if e["id"] in new_set for t in (e.get("refs") or {}).get("resolves", [])})
    corrected = sorted({t for e in entries if e["id"] in new_set for t in (e.get("refs") or {}).get("corrects", [])})
    record = {
        "built_at": built_at, "git_commit": data["stamp"]["git_commit"], "git_dirty": data["stamp"]["git_dirty"],
        "n_entries": len(entries), "added": new_ids, "closed": closed, "corrected": corrected,
        "edited": ctx["edited"], "removed": ctx["removed"], "template_version": plog.TEMPLATE_VERSION,
    }
    data["builds"] = manifest.get("builds", []) + [record]
    if a.draft:
        data["draft"] = sum(1 for e in entries if e.get("imported") and not e.get("reviewed"))

    html = render(data, has_fig)
    out = log_dir / "report" / ("draft.html" if a.draft else "project-log.html")
    if a.draft:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"build: wrote DRAFT {out} ({data['draft']} entries still to review; nothing published)")
        print_changes(data, record)
        return
    if a.dry_run:
        print(f"build: dry run OK ({len(html) / 1e6:.1f} MB would be written to {out})")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    manifest.setdefault("builds", []).append(record)
    manifest["entries"] = {e["id"]: e["_sha"] for e in entries}
    figs = {}
    for e in entries:
        for k in ("figure", "static"):
            rel = (e.get("result") or {}).get(k)
            if rel and (log_dir.parent / rel).exists():
                figs[rel] = plog.sha256_file(log_dir.parent / rel)
    manifest["figures"] = figs
    (log_dir / "report" / "build-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"build: wrote {out} ({len(html) / 1e6:.1f} MB, {len(entries)} entries, {len(new_ids)} new)")
    print_changes(data, record)


def print_changes(data: dict, record: dict) -> None:
    """Plain summary of this build for the reply to the user."""
    by_id = {e["id"]: e for e in data["entries"]}
    title = lambda i: by_id[i]["title"] if i in by_id else i  # noqa: E731
    added = [by_id[i] for i in record["added"] if i in by_id]
    if added:
        print(f"\nAdded ({len(added)}):")
        for e in added:
            print(f"  [{e['label']}] {e['title']}")
    for key, label in (("closed", "Closed"), ("corrected", "Corrected"), ("edited", "Edited after publishing")):
        if record.get(key):
            print(f"\n{label} ({len(record[key])}):")
            for i in record[key]:
                print(f"  {title(i)}")
    open_loops = [e for e in data["entries"] if e.get("status") == "open"]
    print(f"\nOpen loops now: {len(open_loops)} "
          f"({sum(e['type'] == 'question' for e in open_loops)} need a decision, "
          f"{sum(e['type'] == 'blocker' for e in open_loops)} blockers)")
    st = data["stamp"]
    if st.get("git_dirty"):
        print("Note: the repo has uncommitted changes outside project-log/ (shown on the page).")
    if st.get("log_uncommitted"):
        print(f"Note: {st['log_uncommitted']} log file(s) are not committed yet (shown on the page).")


if __name__ == "__main__":
    main()
