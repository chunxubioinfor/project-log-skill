#!/usr/bin/env python3
"""Capture provenance for a result or entry: git state, script paths, data hashes.

Stdlib only. Prints JSON so it can be pasted or piped into new_event.py.

  python3 provenance.py --script analysis/compare.py --data results/x/summary.tsv
  python3 provenance.py --run-manifest results/stage2_ptm_core/20261014_101233/run_manifest.json
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plog  # noqa: E402


def collect(scripts=(), data=(), run_manifest=None, data_version=(), cwd=None) -> dict:
    cwd = Path(cwd or Path.cwd())
    root = plog.repo_root(cwd)
    prov: dict = {}
    g = plog.git_state(cwd)
    if g:
        prov["git_commit"] = g["git_commit"]
        prov["git_dirty"] = g["git_dirty"]   # uncommitted changes anywhere outside project-log/
    if scripts:
        prov["scripts"] = [plog.rel_to(Path(s), root) for s in scripts]
        missing = [s for s in scripts if not Path(s).exists()]
        if missing:
            print(f"warning: script(s) not found: {', '.join(missing)}", file=sys.stderr)
    items = []
    for d in data:
        p = Path(d)
        item = {"path": plog.rel_to(p, root)}
        h = plog.sha256_file(p)
        if h:
            item["sha256"] = h
        elif p.is_file():  # above the hashing limit (e.g. BAM, FASTQ): record size and time instead
            st = p.stat()
            item["size_bytes"] = st.st_size
            item["modified"] = datetime.fromtimestamp(st.st_mtime).astimezone().replace(microsecond=0).isoformat()
            print(f"note: {d} is too large to hash; recorded its size and modification time", file=sys.stderr)
        elif not p.exists():
            print(f"warning: data file not found: {d}", file=sys.stderr)
        items.append(item)
    for dv in data_version:
        # free-form "NAME=VERSION", e.g. dataset=v2.1 or reference=2026_03
        name, _, ver = dv.partition("=")
        items.append({"name": name, "version": ver or None})
    if items:
        prov["data"] = items
    if run_manifest:
        p = Path(run_manifest)
        prov["run_manifest"] = plog.rel_to(p, root)
        if p.exists():
            try:
                m = json.loads(p.read_text())
                for k in ("run_id", "repo_git_commit", "started_at"):
                    if k in m:
                        prov.setdefault("run", {})[k] = m[k]
            except (json.JSONDecodeError, OSError):
                print(f"warning: could not read {run_manifest}", file=sys.stderr)
        else:
            print(f"warning: run manifest not found: {run_manifest}", file=sys.stderr)
    prov["captured_at"] = plog.now_iso()
    prov["machine"] = socket.gethostname().split(".")[0]
    return prov


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", action="append", default=[], help="script that produced the result (repeatable)")
    ap.add_argument("--data", action="append", default=[], help="input/output data file to hash (repeatable)")
    ap.add_argument("--data-version", action="append", default=[], help="NAME=VERSION for data not on disk (repeatable)")
    ap.add_argument("--run-manifest", help="path to an existing run_manifest.json")
    a = ap.parse_args()
    print(json.dumps(collect(a.script, a.data, a.run_manifest, a.data_version), indent=2))


if __name__ == "__main__":
    main()
