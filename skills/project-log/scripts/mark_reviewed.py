#!/usr/bin/env python3
"""Mark imported entries as reviewed, after the user has checked the draft page.

Stdlib only. Imported entries can still be edited freely before they are
reviewed and built for the first time (they are not published yet).

  mark_reviewed.py --list                  # what is still waiting for review
  mark_reviewed.py --thread stage1          # approve one thread
  mark_reviewed.py --id <entry-id> ...      # approve single entries
  mark_reviewed.py --all                    # approve everything still waiting
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plog  # noqa: E402

FIELD = re.compile(r'^(\w+):\s*"?([^"\n]*)"?\s*$', re.M)


def head_fields(text: str) -> dict:
    head, _ = plog.split_front_matter(text)
    return {k: v for k, v in FIELD.findall(head)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--all", action="store_true")
    g.add_argument("--thread")
    g.add_argument("--id", nargs="+")
    ap.add_argument("--log-dir")
    a = ap.parse_args()
    log_dir = Path(a.log_dir).resolve() if a.log_dir else plog.find_log_dir()

    waiting = []
    for p in sorted((log_dir / "entries").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        f = head_fields(text)
        if f.get("imported") == "true" and f.get("reviewed") == "false":
            waiting.append((p, f, text))

    if a.list:
        by = {}
        for _, f, _ in waiting:
            by.setdefault(f.get("thread", "(none)"), []).append(f.get("type", "?"))
        for th, types in sorted(by.items()):
            print(f"{th:28s} {len(types):3d}  " + ", ".join(f"{t} {types.count(t)}" for t in sorted(set(types))))
        print(f"{len(waiting)} imported entries waiting for review")
        return

    n = 0
    for p, f, text in waiting:
        if a.all or (a.thread and f.get("thread") == a.thread) or (a.id and f.get("id") in a.id):
            p.write_text(re.sub(r"^reviewed: false$", "reviewed: true", text, count=1, flags=re.M), encoding="utf-8")
            n += 1
    print(f"marked {n} entries as reviewed; {len(waiting) - n} still waiting")


if __name__ == "__main__":
    main()
