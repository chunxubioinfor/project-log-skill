#!/usr/bin/env python3
"""Write project-log entries (one Markdown file each, with YAML front matter).

Stdlib only, so it runs on every machine. Fills in id, timestamp and
provenance automatically. Never overwrites an existing entry.

One entry
  new_event.py --type bug --thread setup --title "Injection numbers broke the batch" \\
      --why "2 of the first 3 runs failed." \\
      --what "One-sample configs kept their original index; the tool needs 1. Renumbered, added a test." \\
      --commit 8a41c07

  A title or value that starts with "-" needs the = form: --title="-resume flag ignored".

Many entries (preferred for backfills and for several entries at once)
  new_event.py --batch entries.json        # or: new_event.py --batch - <<'EOF' ... EOF

  The input is a JSON list of objects. Field names are the flag names without "--"
  (dashes or underscores). Repeatable flags take lists ("key": result key numbers).
  Give an entry a short "ref" name and point at it later as "@name" in resolves /
  corrects / related / paper; names are remembered across batches in
  project-log/keys.json (commit it with the log).
  --dry-run checks a whole batch, @key links included, without writing.

    [{"ref": "mq-first", "type": "progress", "thread": "maxquant", "ts": "2026-10-01",
      "title": "MaxQuant overlap first computed as 92.9%", "why": "...", "what": "...", "imported": true},
     {"type": "correction", "thread": "maxquant", "ts": "2026-10-02", "corrects": ["@mq-first"],
      "title": "Overlap corrected to 92.2%", "why": "...", "what": "...", "imported": true}]

Body text: --why / --what build the standard body. Use --body-file (or '-' for
stdin) for longer Markdown. Jargon: write [[FDR]] or [[decoy|decoys]].
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plog  # noqa: E402
import provenance as provmod  # noqa: E402

LIST_ARGS = {"resolves", "corrects", "related", "result_ref", "paper", "commit", "script", "data",
             "data_version", "key", "alias"}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", help="JSON file with a list of entries (see above)")
    ap.add_argument("--type", choices=sorted(plog.TYPES))
    ap.add_argument("--title", help="short, plain-language headline")
    ap.add_argument("--thread", help="thread id from project.yaml (main stage or side project)")
    ap.add_argument("--ts", help="ISO timestamp; default now. Date-only (YYYY-MM-DD) allowed for imports")
    ap.add_argument("--why"), ap.add_argument("--what"), ap.add_argument("--body")
    ap.add_argument("--body-file", help="Markdown body file, or '-' for stdin")
    ap.add_argument("--verdict", choices=sorted(plog.VERDICTS), help="detours: how it ended")
    ap.add_argument("--status", choices=["open", "closed"], help="loops: initial status (default open)")
    ap.add_argument("--resolves", action="append", default=[], help="id (or @key) of a follow-up/blocker/question/plan this closes")
    ap.add_argument("--corrects", action="append", default=[], help="id (or @key) of an earlier entry this corrects")
    ap.add_argument("--related", action="append", default=[], help="id (or @key) of a related entry")
    ap.add_argument("--result-ref", action="append", default=[], help="result id (R3) this entry refers to")
    ap.add_argument("--paper", action="append", default=[], help="paper entry id or DOI cited (doi:10.xxx)")
    ap.add_argument("--commit", action="append", default=[], help="git commit(s) this entry is about (e.g. the fix)")
    # provenance
    ap.add_argument("--script", action="append", default=[], help="script that produced the numbers")
    ap.add_argument("--data", action="append", default=[], help="data file to hash")
    ap.add_argument("--data-version", action="append", default=[], help="NAME=VERSION")
    ap.add_argument("--run-manifest", help="run_manifest.json of the run behind a result")
    ap.add_argument("--git-commit", help="commit of the analysis code (imports: the historical commit)")
    ap.add_argument("--no-provenance", action="store_true", help="skip git/data capture")
    ap.add_argument("--machine", help="machine the work ran on (imports: only if the source says)")
    # result block
    ap.add_argument("--so-what", help="results: one line on why the reader should care")
    ap.add_argument("--figure", help="results: Plotly JSON written by a figure script")
    ap.add_argument("--static", help="results: static SVG/PNG of the figure")
    ap.add_argument("--fig-script", help="results: script that makes the figure")
    ap.add_argument("--key", action="append", default=[], help='results: "label=value" key number (repeatable)')
    ap.add_argument("--result-id", help="results: force an id (default next R-number)")
    # paper block
    ap.add_argument("--citation"), ap.add_argument("--doi"), ap.add_argument("--url")
    ap.add_argument("--finding"), ap.add_argument("--why-it-matters"), ap.add_argument("--where-to-look")
    ap.add_argument("--search-phrase")
    # term block
    ap.add_argument("--alias", action="append", default=[], help="terms: other spellings and inflections")
    # misc
    ap.add_argument("--imported", action="store_true", help="created by backfill; needs review before build")
    ap.add_argument("--log-dir", help="path to project-log/ (default: search upward)")
    ap.add_argument("--dry-run", action="store_true")
    return ap


def next_result_id(entries_dir: Path) -> str:
    """Next free R-number, read from existing entry files without PyYAML."""
    nums = [0]
    for p in entries_dir.glob("*.md"):
        for m in re.finditer(r'^\s+id:\s*"?R(\d+)"?\s*$', p.read_text(encoding="utf-8"), re.M):
            nums.append(int(m.group(1)))
    return f"R{max(nums) + 1}"


def build_body(a) -> str:
    if a.body_file:
        return (sys.stdin.read() if a.body_file == "-" else Path(a.body_file).read_text(encoding="utf-8")).strip()
    parts = []
    if a.why:
        parts.append(f"**Why:** {a.why.strip()}")
    if a.what:
        parts.append(f"**What we did:** {a.what.strip()}")
    if a.body:
        parts.append(a.body.strip())
    return "\n\n".join(parts)


def write_entry(a, log_dir: Path, planned: set | None = None) -> dict:
    """Create one entry from parsed options. Raises ValueError on bad input.

    planned: ids created earlier in the same dry-run batch (they count as existing).
    """
    if not a.type or not a.title:
        raise ValueError("--type and --title are required")
    if a.type not in plog.TYPES:
        raise ValueError(f"unknown type '{a.type}'")
    if a.verdict and a.verdict not in plog.VERDICTS:
        raise ValueError(f"unknown verdict '{a.verdict}' (allowed: {', '.join(sorted(plog.VERDICTS))})")
    entries_dir = log_dir / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    for field in ("resolves", "corrects", "related"):
        for ref in getattr(a, field) or []:
            if not (entries_dir / f"{ref}.md").exists() and ref not in (planned or set()):
                near = sorted(p.stem for p in entries_dir.glob(f"{ref[:24]}*.md"))[:3]
                raise ValueError(f"--{field} {ref}: no such entry" + (f" (did you mean {', '.join(near)}?)" if near else ""))

    ts = a.ts or plog.now_iso()
    base = plog.make_id(ts, a.type, a.title)
    eid, n = base, 2
    while (entries_dir / f"{eid}.md").exists():
        eid, n = f"{base}-{n}", n + 1
    path = entries_dir / f"{eid}.md"

    meta: dict = {"id": eid, "ts": ts, "type": a.type, "title": a.title.strip()}
    if a.thread:
        meta["thread"] = a.thread
    if a.verdict:
        meta["verdict"] = a.verdict
    if a.type in plog.LOOP_TYPES:
        meta["status"] = a.status or "open"
    refs = {k: v for k, v in {
        "resolves": a.resolves, "corrects": a.corrects, "related": a.related,
        "results": a.result_ref, "papers": a.paper, "commits": a.commit,
    }.items() if v}
    if refs:
        meta["refs"] = refs

    if a.type == "result":
        if not a.so_what:
            raise ValueError("--so-what is required for results")
        res = {"id": a.result_id or next_result_id(entries_dir), "so_what": a.so_what}
        repo = log_dir.parent
        for k, v in (("figure", a.figure), ("static", a.static), ("script", a.fig_script)):
            if v:
                res[k] = v
        # lock the figure files: validate.py refuses a build if they change later
        for k in ("figure", "static"):
            if res.get(k):
                h = plog.sha256_file(repo / res[k])
                if h is None:
                    raise ValueError(f"--{k} {res[k]}: file not found (paths are relative to the repo root)")
                res[f"{k}_sha256"] = h
        if a.key:
            res["key_numbers"] = [
                {"label": k.partition("=")[0].strip(), "value": k.partition("=")[2].strip()} for k in a.key
            ]
        meta["result"] = res
    if a.type == "paper":
        paper = {k: v for k, v in {
            "citation": a.citation, "doi": a.doi, "url": a.url, "finding": a.finding,
            "why_it_matters": a.why_it_matters, "where_to_look": a.where_to_look,
            "search_phrase": a.search_phrase,
        }.items() if v}
        if not paper.get("citation"):
            raise ValueError("--citation is required for papers")
        meta["paper"] = paper
    if a.type == "term" and a.alias:
        meta["aliases"] = a.alias

    if a.imported:
        # History: today's git state and hostname say nothing about a past event,
        # so record only what was given. The run's own commit stays under run.repo_git_commit.
        prov = {}
        if a.git_commit:
            prov["git_commit"] = a.git_commit
        if a.run_manifest or a.script or a.data_version or a.data:
            got = provmod.collect(a.script, a.data, a.run_manifest, a.data_version, cwd=log_dir)
            for k in ("scripts", "data", "run_manifest", "run"):
                if k in got:
                    prov[k] = got[k]
        if a.machine:
            prov["machine"] = a.machine
        if prov:
            meta["provenance"] = prov
        meta["imported"] = True
        meta["reviewed"] = False
    elif not a.no_provenance:
        prov = provmod.collect(a.script, a.data, a.run_manifest, a.data_version, cwd=log_dir)
        prov.pop("captured_at", None)
        if a.git_commit:
            prov["git_commit"] = a.git_commit
        if a.machine:
            prov["machine"] = a.machine
        meta["provenance"] = prov

    text = plog.dump_front_matter(meta) + "\n" + build_body(a) + "\n"
    out = {"id": eid, "path": str(path)}
    if "result" in meta:
        out["result_id"] = meta["result"]["id"]
    if a.dry_run:
        out["text"] = text
        return out
    path.write_text(text, encoding="utf-8")
    return out


def run_batch(ap, a, log_dir: Path) -> None:
    raw = sys.stdin.read() if a.batch == "-" else Path(a.batch).read_text(encoding="utf-8")
    items = json.loads(raw)
    if not isinstance(items, list):
        raise SystemExit("--batch input must be a JSON list of entries")
    keys_file = log_dir / "keys.json"
    keys = json.loads(keys_file.read_text()) if keys_file.exists() else {}
    defaults = vars(ap.parse_args([]))
    written, planned = [], set()
    verb = "would have been written (dry run)" if a.dry_run else "were written"
    for i, item in enumerate(items, 1):
        ns = argparse.Namespace(**{k: (list(v) if isinstance(v, list) else v) for k, v in defaults.items()})
        local_key = item.pop("ref", None)
        for k, v in item.items():
            name = k.lstrip("-").replace("-", "_")
            if name not in defaults:
                raise SystemExit(f"batch item {i}: unknown field '{k}'")
            if name in LIST_ARGS and not isinstance(v, list):
                v = [v]
            setattr(ns, name, v)
        for field in ("resolves", "corrects", "related", "paper"):
            resolved = []
            for ref in getattr(ns, field):
                if isinstance(ref, str) and ref.startswith("@"):
                    if ref[1:] not in keys:
                        raise SystemExit(f"batch item {i} ('{item.get('title')}'): unknown ref {ref}")
                    ref = keys[ref[1:]]
                resolved.append(ref)
            setattr(ns, field, resolved)
        ns.imported = ns.imported or a.imported
        ns.dry_run = a.dry_run
        try:
            out = write_entry(ns, log_dir, planned)
        except ValueError as exc:
            raise SystemExit(f"batch item {i} ('{item.get('title')}'): {exc}. "
                             f"{len(written)} earlier items {verb}.")
        planned.add(out["id"])
        if local_key:
            if local_key in keys and keys[local_key] != out["id"]:
                raise SystemExit(f"batch item {i}: ref '{local_key}' is already used for {keys[local_key]}")
            keys[local_key] = out["id"]
        written.append(out)
    if not a.dry_run and keys:
        keys_file.write_text(json.dumps(keys, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({("would_write" if a.dry_run else "written"): len(written), "entries": [
        {k: v for k, v in w.items() if k != "text"} for w in written]}, indent=1))


def main():
    ap = build_parser()
    a = ap.parse_args()
    log_dir = Path(a.log_dir).resolve() if a.log_dir else plog.find_log_dir()
    if a.batch:
        run_batch(ap, a, log_dir)
        return
    try:
        out = write_entry(a, log_dir)
    except ValueError as exc:
        ap.error(str(exc))
    if a.dry_run:
        print(out.pop("text"))
        return
    print(json.dumps(out))


if __name__ == "__main__":
    main()
