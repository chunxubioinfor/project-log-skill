# Entry and project schema

## Contents
- Folder layout
- project.yaml
- Entry files
- Types and when the page shows them
- Links between entries (refs)
- Result block
- Paper block
- Validation rules

## Folder layout

```
<repo>/project-log/
  project.yaml          # project title, threads, tabs, overview summary and tiles (current state; editable)
  entries/              # one .md file per entry (append-only)
  figures/scripts/      # reusable figure scripts
  figures/out/          # generated <name>.json (Plotly) and <name>.svg
  report/project-log.html       # built page (committed)
  report/build-manifest.json    # build history + entry hashes (written by build.py only)
```

Paths inside entries are relative to the repo root (the folder that contains `project-log/`).

## project.yaml

Always use block style for lists of mappings. One-line `{...}` mappings break as soon as a value contains a comma.

```yaml
title: Does the new normalisation reduce batch effects?
lede: One or two sentences under the title.
owner: Alex Doe
group: Example Lab, Example University
audience: layered            # set by the kickoff round
progress_file: docs/PROGRESS.md   # optional: the hand-written progress notes the reminder hook watches
tabs: [overview, timeline, results, side, loops, next, digests, glossary, changelog]
figures:
  conventions: One sentence per agreed convention (e.g. "the baseline is always amber").
threads:
  - id: norm-v2              # short, lowercase, used by --thread
    name: Normalisation v2
    kind: main               # main | side
    status: active           # active | done | paused (active draws the hatched "still going" bar)
    goal: Does the new normalisation reduce batch effects without losing biological signal?
overview:
  figure: R12                # optional: one result's figure shown on the Overview (after the Gantt chart)
  summary:                   # 3 short paragraphs, rewritten before each build; [[terms]] allowed
    - ...
  tiles:                     # 3-4 key numbers
    - value: "−38%"
      label: batch effect (silhouette score) vs the baseline
      link: R1               # R<n> | thread:<id> | tab:<name> | <entry id>
published_url: https://claude.ai/artifact/...   # set after the first publish
```

## Entry files

`entries/<id>.md`: YAML front matter, then a Markdown body. Always create entries with `new_event.py`; it writes the front matter.

```markdown
---
id: "2026-10-11T1647-bug-2-of-the-first-3-batch-jobs-failed"
ts: "2026-10-11T16:47:00+02:00"      # date-only "2026-10-11" allowed for imported entries
type: "bug"
title: "2 of the first 3 batch jobs failed"
thread: "norm-v2"
refs:
  commits: ["8a41c07"]
provenance:
  git_commit: "cb5c892"
  git_dirty: false     # uncommitted changes in the repo outside project-log/
  machine: "cluster-node"
---

**Why:** The overnight batch of 24 samples would have stopped.

**What we did:** Each one-sample config kept its original index, but the tool needs it to start at 1. Renumbered, added a test, restarted at 17:05.
```

Body Markdown: paragraphs, `- ` lists, `**bold**`, `*italic*`, `` `code` ``, `[text](https://...)`, `[[term]]` or `[[term|shown text]]`.

Optional fields: `verdict` (detours), `status` (loop types; default open), `aliases` (terms), `imported` + `reviewed` (backfill).

## Types and when the page shows them

| Type | Page | Colour group |
|---|---|---|
| progress, thread | Timeline | grey |
| milestone, result | Timeline (diamond in the Gantt chart), Results | green |
| bug, blocker | Timeline (red mark in the Gantt chart); blocker also in Open loops | red |
| detour, correction | Timeline; a correction adds a "Corrected later" banner to its target | amber |
| decision, question | Timeline; open questions also in Overview "Needs a decision" and Open loops | blue |
| followup, plan | Timeline; open follow-ups in Open loops, open plans in Next steps | purple |
| paper | Timeline (short) and Digests (full card) | grey |
| session | Digests only | – |
| term | Glossary only; hover popups everywhere | – |

Loop types (followup, blocker, question, plan) stay open until an entry with `refs.resolves: [<id>]` exists.

## Links between entries (refs)

| Key | Flag | Meaning |
|---|---|---|
| resolves | `--resolves` | closes a followup / blocker / question / plan |
| corrects | `--corrects` | marks an earlier entry as corrected |
| related | `--related` | any other link (e.g. a plan's dependency) |
| results | `--result-ref` | R-numbers this entry is about |
| papers | `--paper` | paper entry id or `doi:...` |
| commits | `--commit` | relevant git commits |

## Result block

```yaml
result:
  id: "R1"                                   # assigned automatically
  so_what: "One sentence: why should the reader care?"
  figure: "project-log/figures/out/batch_effect_v2.json"   # optional
  static: "project-log/figures/out/batch_effect_v2.svg"    # optional
  script: "project-log/figures/scripts/batch_effect.py"    # required if figure is set
  figure_sha256: "…"                                       # written automatically: locks the figure
  key_numbers:
    - {label: "Batch silhouette", value: "0.21 vs 0.34"}
```

## Paper block

```yaml
paper:
  citation: "Author A, Author B. Title of the paper. Journal 2025;12:345."
  doi: "10.xxxx/xxxxx"
  url: "https://..."
  finding: "What the paper showed, in one or two sentences."
  why_it_matters: "Why it matters for this project."
  where_to_look: "Figure 2C and 2D; Methods, section 4.3"
  search_phrase: "a short exact phrase to find the key passage in the PDF"
```

Use the paper's main finding as the entry title, not the paper's own title.

## Validation rules (validate.py)

Errors stop the build:
- a file that looks like a sync-tool copy (`name 2.md`, `name (1).md`, "conflicted copy"). iCloud Desktop sync, Dropbox and OneDrive make these when a file changes while it syncs. Compare the copy with the original, and delete it if they are identical.
- missing id / ts / type / title; id differs from the file name; duplicate id; bad timestamp; unknown type, thread or verdict
- result without `so_what`, figure without `script`, figure/static/script file missing
- `refs` pointing to unknown entries or results; `resolves` pointing to a type that cannot be closed
- `[[term]]` without a term entry
- imported entry with `reviewed: false`
- an entry changed or deleted after it was published (unless `--accept-edits`, which records it)

Warnings: an entry without a thread, a result without a git commit, a paper reference without a paper entry.
