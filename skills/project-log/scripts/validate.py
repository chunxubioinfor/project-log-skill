# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml>=6"]
# ///
"""Check the project log before a build. Exit code 1 if anything blocks the build.

  uv run validate.py                 # from anywhere inside the project
  uv run validate.py --log-dir path/to/project-log
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plog  # noqa: E402

REQUIRED = ("id", "ts", "type", "title")
NEEDS_THREAD = {"progress", "result", "bug", "blocker", "detour", "decision", "correction",
                "followup", "question", "milestone", "plan", "thread"}


def _ts_ok(ts: str) -> bool:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", ts):
            date.fromisoformat(ts)
        else:
            datetime.fromisoformat(re.sub(r"Z$", "+00:00", ts))  # Python < 3.11 rejects "Z"
        return True
    except ValueError:
        return False


def load_manifest(log_dir: Path) -> dict:
    p = log_dir / "report" / "build-manifest.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"builds": [], "entries": {}}


def validate(log_dir: Path, accept_edits: bool = False, draft: bool = False):
    errors: list[str] = []
    warnings: list[str] = []
    base = log_dir.parent  # paths in entries are relative to the repo root

    try:
        project = plog.load_project(log_dir)
    except Exception as exc:  # noqa: BLE001
        return [f"project.yaml: cannot parse ({exc})"], [], {}
    if not project.get("title"):
        errors.append("project.yaml: missing 'title'")
    threads = {}
    for t in project.get("threads") or []:
        if not isinstance(t, dict) or not t.get("id") or not t.get("name"):
            errors.append(f"project.yaml: thread needs id and name: {t!r}")
            continue
        if t.get("kind", "main") not in ("main", "side"):
            errors.append(f"project.yaml: thread {t['id']}: kind must be main or side")
        threads[t["id"]] = t
    for tab in project.get("tabs") or []:
        if tab not in plog.ALL_TABS:
            errors.append(f"project.yaml: unknown tab '{tab}' (allowed: {', '.join(plog.ALL_TABS)})")

    for p in plog.conflict_copies(log_dir):
        m = plog.CONFLICT.search(p.name)
        orig = p.name[:m.start()] + ".md"
        errors.append(f"{p.name}: looks like a copy made by a file-sync tool (iCloud, Dropbox, OneDrive). "
                      f"Compare it with {orig}; if they are identical, delete the copy")
    try:
        entries = plog.load_entries(log_dir)
    except Exception as exc:  # noqa: BLE001
        return errors + [f"entries: cannot parse ({exc})"], warnings, {}

    ids, rids, terms = {}, {}, {}
    for e in entries:
        where = e["_path"].name
        for k in REQUIRED:
            if not e.get(k):
                errors.append(f"{where}: missing '{k}'")
        if e.get("id") and e["id"] != e["_path"].stem:
            errors.append(f"{where}: id '{e['id']}' does not match the file name")
        if e.get("id") in ids:
            errors.append(f"{where}: duplicate id '{e['id']}'")
        ids[e.get("id")] = e
        if e.get("ts") and not _ts_ok(str(e["ts"])):
            errors.append(f"{where}: ts '{e['ts']}' is not ISO 8601")
        et = e.get("type")
        if et and et not in plog.TYPES:
            errors.append(f"{where}: unknown type '{et}'")
        th = e.get("thread")
        if th and th not in threads:
            errors.append(f"{where}: thread '{th}' is not defined in project.yaml")
        if et in NEEDS_THREAD and not th:
            warnings.append(f"{where}: no thread; it will not appear in the Gantt chart")
        if e.get("verdict") and e["verdict"] not in plog.VERDICTS:
            errors.append(f"{where}: unknown verdict '{e['verdict']}'")
        if et == "result":
            r = e.get("result") or {}
            if not r.get("id"):
                errors.append(f"{where}: result needs result.id (R-number)")
            elif r["id"] in rids:
                errors.append(f"{where}: result id {r['id']} already used by {rids[r['id']]['_path'].name}")
            else:
                rids[r["id"]] = e
            if not (r.get("so_what") or "").strip():
                errors.append(f"{where}: result needs a one-line 'so_what'")
            for k in ("figure", "static", "script"):
                if r.get(k) and not (base / r[k]).exists():
                    errors.append(f"{where}: result.{k} not found: {r[k]}")
            for k in ("figure", "static"):
                want = r.get(f"{k}_sha256")
                if want and r.get(k) and (base / r[k]).exists() and plog.sha256_file(base / r[k]) != want:
                    msg = (f"{where}: {r[k]} changed after {r.get('id')} was logged. A published figure must not "
                           "change: write new data to a new output name, log a new result, and add a correction")
                    (warnings if accept_edits else errors).append(msg)
            if r.get("figure") and not r.get("script"):
                errors.append(f"{where}: a figure needs result.script (how to remake it)")
            prov = e.get("provenance") or {}
            if not e.get("imported") and not prov.get("git_commit"):
                warnings.append(f"{where}: result has no git commit in provenance")
        if et == "paper" and not (e.get("paper") or {}).get("citation"):
            errors.append(f"{where}: paper needs paper.citation")
        if et == "term":
            for name in [e.get("title", ""), *(e.get("aliases") or [])]:
                terms[plog.term_key(name)] = e
            if not e["_body"]:
                errors.append(f"{where}: term needs a definition in the body")
        if e.get("imported") and not e.get("reviewed") and not draft:
            errors.append(f"{where}: imported entry not reviewed yet (check the draft page, then run mark_reviewed.py)")

    papers = {e["id"] for e in entries if e.get("type") == "paper"}
    papers |= {str((e.get("paper") or {}).get("doi", "")).lower() for e in entries if e.get("type") == "paper"}
    for e in entries:
        where = e["_path"].name
        refs = e.get("refs") or {}
        for k in ("resolves", "corrects", "related"):
            for target in refs.get(k) or []:
                if target not in ids:
                    errors.append(f"{where}: refs.{k} points to unknown entry '{target}'")
                elif k == "resolves" and ids[target].get("type") not in plog.LOOP_TYPES:
                    errors.append(f"{where}: refs.resolves '{target}' is a {ids[target].get('type')}, "
                                  f"not one of {', '.join(sorted(plog.LOOP_TYPES))}")
        for rid in refs.get("results") or []:
            if rid not in rids:
                errors.append(f"{where}: refs.results points to unknown result '{rid}'")
        for pid in refs.get("papers") or []:
            key = str(pid).lower().removeprefix("doi:")
            if pid not in papers and key not in papers:
                warnings.append(f"{where}: paper '{pid}' has no paper entry yet (no digest card)")
        for t in plog.terms_used(e["_body"]):
            if t not in terms:
                errors.append(f"{where}: [[{t}]] has no glossary term entry")

    overview = project.get("overview") or {}
    for card in overview.get("summary") or []:
        body = card.get("items", card.get("text", "")) if isinstance(card, dict) else card
        for t in plog.terms_used(" ".join(map(str, body)) if isinstance(body, list) else str(body)):
            if t not in terms:
                errors.append(f"project.yaml overview.summary: [[{t}]] has no glossary term entry")
    fig = overview.get("figure")
    if fig and (fig not in rids or not (rids[fig].get("result") or {}).get("figure")):
        errors.append(f"project.yaml overview.figure: {fig} is not a result with a figure")
    for tile in overview.get("tiles") or []:
        link = str(tile.get("link", ""))
        if link.startswith("thread:") and link[7:] not in threads:
            errors.append(f"project.yaml tile '{tile.get('label')}': unknown thread {link[7:]}")
        elif re.fullmatch(r"R\d+", link) and link not in rids:
            errors.append(f"project.yaml tile '{tile.get('label')}': unknown result {link}")

    manifest = load_manifest(log_dir)
    # figures of published results, as they were at the last build
    for rel, want in (manifest.get("figures") or {}).items():
        p = base / rel
        if p.exists() and plog.sha256_file(p) != want:
            msg = (f"{rel} changed since it was published. A published figure must not change: "
                   "write new data to a new output name, log a new result, and add a correction")
            if f"{rel} changed after" not in " ".join(errors + warnings):
                (warnings if accept_edits else errors).append(msg)
    edited = []
    for e in entries:
        old = manifest.get("entries", {}).get(e.get("id"))
        if old and old != e["_sha"]:
            edited.append(e["id"])
            msg = (f"{e['_path'].name}: changed after it was published. The log is append-only: "
                   "add a 'correction' entry instead, or rebuild with --accept-edits to record the edit in the Changelog")
            (warnings if accept_edits else errors).append(msg)
    published = set(manifest.get("entries", {}))
    missing = sorted(published - set(ids))
    for m in missing:
        msg = f"entry '{m}' was published before but its file is gone"
        (warnings if accept_edits else errors).append(msg)

    ctx = {"project": project, "entries": entries, "threads": threads, "ids": ids,
           "rids": rids, "terms": terms, "manifest": manifest, "edited": edited, "removed": missing}
    return errors, warnings, ctx


def report(errors, warnings, n_entries) -> None:
    for w in warnings:
        print(f"  warning  {w}")
    for e in errors:
        print(f"  ERROR    {e}")
    status = "OK" if not errors else f"{len(errors)} error(s)"
    print(f"validate: {n_entries} entries, {len(warnings)} warning(s), {status}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log-dir")
    ap.add_argument("--accept-edits", action="store_true", help="allow edits to published entries (recorded)")
    ap.add_argument("--draft", action="store_true", help="do not count unreviewed imports as errors")
    a = ap.parse_args()
    log_dir = Path(a.log_dir).resolve() if a.log_dir else plog.find_log_dir()
    errors, warnings, ctx = validate(log_dir, a.accept_edits, a.draft)
    report(errors, warnings, len(ctx.get("entries", [])))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
