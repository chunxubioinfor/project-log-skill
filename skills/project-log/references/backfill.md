# Backfill: import a project's history

Use this once, when project-log is set up in a project that already has history (a PROGRESS.md, git commits, run folders, results documents). The import produces draft entries marked `imported`. The user reviews them on a draft page before anything is published.

## Contents
- Steps
- Reading the sources
- What becomes an entry
- Timestamps
- Provenance for past results
- Glossary and papers
- Quality bar
- Review with the user

## Steps

1. **Scan.** From the repo root, run `python3 $PL/backfill_scan.py`. This writes `project-log/backfill/scan.md`: PROGRESS.md sections with line ranges, the git log, run manifests, documents, and the DOIs, PMIDs, PRIDE accessions and GitHub issues found.
2. **Threads.** Read the brief, the README and the newest PROGRESS entry. Propose the threads (main stages and side projects) to the user as a short table: id, name, kind, status, one-line goal. Write them to `project.yaml` once agreed.
3. **Read the history once, oldest first.** Go through the PROGRESS.md sections in date order, using `scan.md` for the line ranges. Next to each section, read the commits from those days (`scan.json` → `git`) and the results documents and run manifests it mentions.
4. **Write the entries** with `new_event.py --imported --batch <file>.json`, one JSON file per session, in chronological order. Give each entry that later entries may close, correct or cite a short `"ref"` name, and point at it later as `"@name"` in `resolves` / `corrects` / `related` / `paper`. Keys are remembered across batches in `project-log/keys.json` (commit it). JSON avoids all shell-quoting trouble with apostrophes, `$`, backticks and leading dashes. Run from the repo root, so script and data paths resolve correctly.
5. **Glossary, papers, overview.** Add term entries, paper entries, one session digest per session, and a draft `overview` in project.yaml.
6. **Check.** Run `uv run $PL/build.py --draft` until it reports no errors. It writes `report/draft.html`.
7. **Review with the user** (see the last section).

## Reading the sources

| Source | Gives |
|---|---|
| PROGRESS.md / session notes | the story: what was done, decided, corrected, left open |
| git log | exact times; commits to cite with `--commit`; work that never reached the notes |
| run manifests (`run_manifest.json`) | when a run started, the commit it ran on, database and sample-sheet hashes, the one setting changed |
| results documents (`*_RESULTS.md`, comparison JSON) | the numbers for result entries |
| handoff documents | side projects: goal, status, glossary ("Words used"), references |
| primers, explainers | wording for glossary definitions |

Notes in a progress file are often uneven: sessions folded together, duplicate numbers, headings without dates, blocks moved around. Rely on the dates in the text and on the git log, not on the session numbers.

## What becomes an entry

Use the type table in SKILL.md. Rules of thumb:

- **Every** bug fixed, blocker, decision (with its reason), correction of an earlier claim, and result with numbers becomes an entry. These are what get forgotten.
- A **detour** is any approach tried and dropped, any wrong assumption, or any redone work. Give it a verdict.
- A **correction** points at the entry it corrects (`--corrects`). If the corrected claim never got an entry, write the correction on its own and say in the body what was wrong.
- **Follow-ups**: write the ones that mattered. When a later session closes one, write the closing entry with `--resolves`. Items still open in the newest notes stay as open follow-ups or questions; these become the Open loops tab.
- **Milestones**: first successful runs, locked baselines, handoffs.
- Aim for about 4–10 entries per session. Merge trivial steps. Never pad.
- **Session digest**: one `session` entry per session (or per folded block of sessions), dated at the end of that session.

## Timestamps

- If an entry matches a specific commit, use that commit's timestamp (`--ts` with the full ISO time) and pass `--commit <hash>`.
- If a run manifest gives the start time, use it for the "run started" entry.
- Otherwise use the date only (`--ts 2026-09-21`). The page shows these entries as "imported", without a time.
- Never invent a clock time.

## Provenance for past results

Today's git state says nothing about a past result, so imported entries don't capture it. Instead, pass what the history records:

```bash
python3 $PL/new_event.py --imported --type result --thread norm-v2 --ts "2026-10-03" \
  --title "Normalisation v2 cuts the batch effect by a third" \
  --why "..." --what "..." --so-what "..." \
  --run-manifest results/norm_v2/20261002_160326/run_manifest.json \
  --script analysis/<comparison script>.py \
  --key "Batch silhouette=0.21 vs 0.34" --key "Runtime=1.4x baseline"
```

Two commits can belong to one result, and they are kept apart:
- `--run-manifest` records the run's commit (`run.repo_git_commit`, shown as "Run commit").
- `--git-commit` records the commit of the analysis or comparison script ("Analysis commit").
- `--commit` lists commits the entry is about, such as the fix itself.

Imported entries do not record the importing machine. Pass `--machine <name>` only when the source says where the work ran.

**What counts as a result:** a number someone could cite or compare against later, from a finished run, comparison or diagnostic. A diagnostic that only says "it works now" is a `milestone` or `bug`, not a result. A result whose numbers exist only in a document (no script in the repo) still gets an entry: pass the document as `--data`, and say in the body where the numbers come from. Result entries usually have no figure yet: list the figures worth making in the review summary, and make them later through the figure workflow, once the user agrees.

## Glossary and papers

- Write a `term` entry for each technical term the entries use, dated at its first use. Prefer the project's own definitions (primer, explainer, "Words used" sections), rewritten to one or two plain sentences. Wrap the terms in `[[ ]]` in entry bodies.
- Write a `paper` entry only for papers the project actually discussed. Fill in only the fields the sources support. Leave out `where_to_look` and `search_phrase` unless they are written down somewhere. Never fill a field from memory.

## Quality bar

- Plain language, following writing-style.md. Every entry must make sense to someone who never saw the session.
- Facts only from the sources. When a source is unclear, say so in the entry ("the notes don't say why").
- Keep the original people and decisions: "Alex decided…", "Sam asked…".
- No invented numbers, dates, commits or quotes.

## Catching up after a gap

Use this when work happened without logging: a session on another machine where the skill isn't installed, a stretch before setup, or days when only PROGRESS.md was updated.

1. **Find the gap.** Note the date of the newest entry. Pull first if the project's rules say to. Then read the PROGRESS.md sections and the commits after that date (`git log --since <date>`).
2. **Follow the backfill rules above.** Entries are `--imported`, and the user reviews them on a `--draft` page.
3. **Never edit published entries.** When new work supersedes a published result (e.g. a rerun after a bug fix), log the new run as a new result with a new R-number and a figure under a new output name (see figures.md). Add a `correction` entry that `--corrects` the old result and says what changed and why. When a published open item was settled during the gap, write the closing entry with `--resolves`.
4. **Refresh the overview** in project.yaml, then run the draft build.

## Review with the user

Give the user:
1. The draft page (`report/draft.html`). Offer to publish it as a private link if the Artifact tool is available, and publish only if the user agrees.
2. A summary: entries per thread and type (`python3 $PL/mark_reviewed.py --list`), the open loops carried over, the results that have no figure yet (with a suggested chart for each), and anything uncertain.
3. A question: approve all, approve some threads, or change something?

Fix whatever the user flags by editing the imported files; they are not published yet. Then run `mark_reviewed.py --all` (or `--thread`), followed by a normal build.
