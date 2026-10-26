#!/usr/bin/env python3
"""Collect raw material for a backfill. Writes project-log/backfill/scan.json and scan.md.

Stdlib only. It does not interpret anything: Claude reads scan.md and the source
files, then writes `imported` entries with new_event.py (see references/backfill.md).

  python3 backfill_scan.py                       # run from the repo root
  python3 backfill_scan.py --progress docs/PROGRESS.md
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

DATE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:/(\d{2}))?")
SESSION = re.compile(r"Session\s+(\d+)", re.I)
REFS = {
    "doi": re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>)\]`,;]+[^\s\"'<>)\]`,;.])"),
    "pmid": re.compile(r"PMID:?\s*(\d{6,9})"),
    "pmc": re.compile(r"\b(PMC\d{6,9})\b"),
    "pride": re.compile(r"\b(PXD\d{6})\b"),
    "gh_issue": re.compile(r"\b([\w.-]+/[\w.-]+#\d+)\b"),
}
SKIP_DIRS = {".git", "node_modules", "work", ".nextflow", "project-log", ".venv"}


def progress_sections(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    heads = [i for i, l in enumerate(lines) if l.startswith("## ")]
    out = []
    for n, start in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        head = lines[start][3:].strip()
        body = "\n".join(lines[start + 1:end])
        dates = DATE.findall(head) or DATE.findall("\n".join(lines[start + 1:start + 4]))
        sess = SESSION.search(head) or SESSION.search("\n".join(lines[start + 1:start + 4]))
        subs = [l[4:].strip() for l in lines[start + 1:end] if l.startswith("### ")]
        out.append({
            "heading": head,
            "line_start": start + 1, "line_end": end,
            "dates": [d[0] + ("/" + d[1] if d[1] else "") for d in dates][:3],
            "session": int(sess.group(1)) if sess else None,
            "is_next_block": "NEXT SESSION" in head.upper(),
            "subsections": subs,
            "n_lines": end - start,
            "lead_ins": sorted(set(re.findall(r"\*\*([A-Z][A-Za-z /'()-]{2,40}?)[:.]?\*\*", body)))[:30],
        })
    return out


def git_log(repo: Path) -> list[dict]:
    try:
        raw = subprocess.run(
            ["git", "log", "--reverse", "--format=%h%x09%aI%x09%an%x09%s"],
            cwd=repo, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    out = []
    for line in raw.splitlines():
        h, ts, author, subj = (line.split("\t", 3) + ["", "", "", ""])[:4]
        out.append({"hash": h, "ts": ts, "author": author, "subject": subj})
    return out


def walk(repo: Path, pattern: str):
    for p in sorted(repo.rglob(pattern)):
        if not SKIP_DIRS.intersection(p.relative_to(repo).parts):
            yield p


def manifests(repo: Path) -> list[dict]:
    out = []
    for p in walk(repo, "run_manifest.json"):
        try:
            m = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        item = {"path": str(p.relative_to(repo))}
        for k in ("run_id", "stage", "variant", "started_at", "repo_git_commit", "pipeline_version",
                  "nextflow_version", "one_variable_changed", "resume_used"):
            if k in m:
                item[k] = m[k]
        for k in ("database", "sdrf"):
            if isinstance(m.get(k), dict):
                item[k] = {kk: m[k][kk] for kk in ("path", "provenance", "sha256") if kk in m[k]}
        cmp_files = list(p.parent.rglob("comparison_results.json"))
        if cmp_files:
            try:
                c = json.loads(cmp_files[0].read_text())
                item["comparison"] = {
                    "path": str(cmp_files[0].relative_to(repo)),
                    "keys": sorted(c.keys())[:40],
                    "generated_date": c.get("generated_date"),
                    "caveats": c.get("caveats", [])[:8],
                }
            except (json.JSONDecodeError, OSError):
                pass
        out.append(item)
    return out


def docs_and_refs(repo: Path) -> tuple[list[dict], dict]:
    docs, refs = [], {k: {} for k in REFS}
    for p in list(walk(repo, "*.md")) + list(walk(repo, "*.html")) + list(walk(repo, "*.ndjson")):
        rel = str(p.relative_to(repo))
        if "run_reports" in p.parts or p.name.startswith(("execution_", "pipeline_dag")):
            continue  # Nextflow's own reports: large, no project prose
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        title = next((l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("# ")), "")
        if not title:
            m = re.search(r"<title>(.*?)</title>", text, re.S)
            title = m.group(1).strip() if m else ""
        docs.append({"path": rel, "title": title[:120], "kb": round(p.stat().st_size / 1024, 1)})
        for kind, rx in REFS.items():
            for m in rx.finditer(text):
                refs[kind].setdefault(m.group(1), set()).add(rel)
    refs = {k: {ref: sorted(files) for ref, files in v.items()} for k, v in refs.items()}
    return docs, refs


def write_md(scan: dict, out: Path) -> None:
    L = [f"# Backfill scan of {scan['repo']}", ""]
    L += ["## PROGRESS.md sections (read these line ranges)", "",
          "| lines | session | dates | heading |", "|---|---|---|---|"]
    for s in scan["progress"]:
        L.append(f"| {s['line_start']}–{s['line_end']} | {s['session'] or ''} | {', '.join(s['dates'])} | "
                 f"{s['heading'][:110].replace('|', '/')} |")
    g = scan["git"]
    if g:
        L += ["", f"## Git: {len(g)} commits, {g[0]['ts'][:10]} to {g[-1]['ts'][:10]}", "",
              "Commits per day: " + ", ".join(
                  f"{d} ({n})" for d, n in sorted({c['ts'][:10]: sum(1 for x in g if x['ts'][:10] == c['ts'][:10]) for c in g}.items()))]
    L += ["", f"## Run manifests ({len(scan['manifests'])})", "", "| path | stage | variant | started | commit |", "|---|---|---|---|---|"]
    for m in scan["manifests"]:
        L.append(f"| {m['path']} | {m.get('stage', '')} | {m.get('variant', '')} | {m.get('started_at', '')} | {m.get('repo_git_commit', '')[:7] if m.get('repo_git_commit') else ''} |")
    L += ["", "## Documents", ""] + [f"- `{d['path']}` ({d['kb']} kB): {d['title']}" for d in scan["docs"]]
    L += ["", "## References found", ""]
    for kind, items in scan["refs"].items():
        if items:
            L.append(f"- **{kind}** ({len(items)}): " + ", ".join(sorted(items)[:40]))
    out.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--progress", help="progress file (default: first PROGRESS.md found)")
    ap.add_argument("--out", help="output folder (default: <repo>/project-log/backfill)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    prog = Path(a.progress) if a.progress else next(iter(walk(repo, "PROGRESS.md")), None)
    scan = {
        "repo": str(repo), "scanned_at": plog.now_iso(),
        "progress_file": str(prog.relative_to(repo)) if prog else None,
        "progress": progress_sections(prog) if prog else [],
        "git": git_log(repo),
        "manifests": manifests(repo),
    }
    scan["docs"], scan["refs"] = docs_and_refs(repo)
    out = Path(a.out) if a.out else repo / plog.LOG_DIR_NAME / "backfill"
    out.mkdir(parents=True, exist_ok=True)
    (out / "scan.json").write_text(json.dumps(scan, indent=1, ensure_ascii=False), encoding="utf-8")
    write_md(scan, out / "scan.md")
    print(json.dumps({"scan_md": str(out / "scan.md"), "sections": len(scan["progress"]),
                      "commits": len(scan["git"]), "manifests": len(scan["manifests"]),
                      "docs": len(scan["docs"])}))


if __name__ == "__main__":
    main()
