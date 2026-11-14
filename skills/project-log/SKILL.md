---
name: project-log
description: Keeps a structured, append-only log of a research project (progress, results, bugs fixed, detours, decisions, open follow-ups, side projects, papers, glossary) and builds one interactive HTML report from it with a timeline, Gantt chart, figures and provenance. Use when the project has a project-log/ folder, when the user asks to log progress, record a result, note a follow-up, update or publish the project log, make the progress page, or wrap up a session, and whenever the project's progress notes (e.g. PROGRESS.md) are updated.
---

# project-log

The log in `<repo>/project-log/` is the source of truth. The HTML page is a build output: never edit `report/project-log.html` by hand.

Scripts live next to this file in `scripts/`. Here and in the references, `$PL` means `${CLAUDE_SKILL_DIR}/scripts` (normally `~/.claude/skills/project-log/scripts`). Shell variables do not carry over between Bash calls, so start each command with `PL="${CLAUDE_SKILL_DIR}/scripts";` or write the full path.

- `new_event.py` writes one entry. It uses only the standard library, so it runs on any machine.
- `provenance.py` captures the git commit, script paths and data hashes. Standard library only.
- `validate.py` and `build.py` need PyYAML and Plotly. Run them with `uv run`, which supplies both.

## Ground rules

1. **Append-only.** Never edit or delete an entry once it has been in a build. A mistake gets a `correction` entry (`--corrects <id>`). A finished follow-up gets a closing entry (`--resolves <id>`). The validator blocks silent edits.
2. **Plain language.** Write for a supervisor reading in two minutes, and for the user six weeks from now. Follow [references/writing-style.md](references/writing-style.md). Mark jargon as `[[term]]`, and create a `term` entry the first time a term appears.
3. **Every result answers "so what".** A result entry needs `--so-what`, one sentence on why the reader should care.
4. **Provenance is captured, never typed.** Let `new_event.py` record the commit and hashes. Pass `--script`, `--data`, `--run-manifest` or `--data-version` for anything that produced a number.
   - The captured commit is the repo's state *now*. For a run that happened earlier or elsewhere, also pass `--run-manifest` or `--git-commit <the run's commit>`, and say in the body if the data in the repo is not from that run.
5. **Respect the project's own rules.** Follow its CLAUDE.md on git: who commits, authorship, and whether to push. Never add AI co-author trailers in a project that forbids them.
   - If the project's rules don't say when to commit, ask before committing.
   - Never push unless those rules or the user say to.
   - If `project-log/` has never been committed, the page header and the build output say so. Tell the user, because the other machine cannot see the log until it is committed.

## Workflow: capture while working

Write an entry when one of these happens. Don't save them up for later.

| Moment | Type | Extra flags |
|---|---|---|
| A run finished, or a number or figure was produced | `result` | `--so-what`, provenance, `--key "label=value"`, figure (see below) |
| Something was fixed (bug, config, data problem) | `bug` | `--commit` |
| Work is stuck on something outside our control | `blocker` | |
| An approach was tried and dropped, or changed course | `detour` | `--verdict archived\|pivoted\|kept\|kept-after-review\|iterate\|corrected` |
| A choice was made between options | `decision` | `--resolves <question id>` if it answers one |
| An earlier statement turned out wrong | `correction` | `--corrects <id>` |
| Something to do later, or to check | `followup` | |
| A decision is needed from the user or supervisor | `question` | |
| Planned next work | `plan` | `--related <id>` for what it depends on |
| A notable step reached | `milestone` | |
| Other meaningful progress | `progress` | |
| A paper was read or discussed | `paper` | `--citation --doi --finding --why-it-matters --where-to-look --search-phrase` |
| A new technical term was used | `term` | title = the term, body = 1–2 sentence definition, `--alias` |
| A side project starts | add a thread to `project.yaml` (`kind: side`), then a `progress` entry | |

```bash
python3 $PL/new_event.py --type bug --thread norm-v2 \
  --title "Sample indices broke the batch" \
  --why "2 of the first 3 runs failed." \
  --what "One-sample configs kept their original index; the tool needs 1. Renumbered and added a test." \
  --commit 8a41c07
```

Each entry except `term`, `paper` and `session` needs a `--thread` from `project.yaml`. If none fits, add a thread first. The full field list is in [references/event-schema.md](references/event-schema.md).

**Several entries at once** (e.g. at wrap-up): pass them as a JSON list on stdin, with `new_event.py --batch - <<'EOF' [...] EOF`. A quoted heredoc means no shell quoting to get wrong.
- Entries can refer to each other by `"ref": "name"` / `"@name"` (also in `paper`); `"key"` stays the result key-number field. Keys are kept in `project-log/keys.json`; commit that file with the log.
- `--dry-run` checks the whole batch first.
- See `new_event.py --help`.
- A single-entry title that starts with "-" needs the `--title="-..."` form.

**When the progress notes are updated** (`progress_file` in project.yaml, usually PROGRESS.md): each new fact in that update (bug, decision, result, open item) also becomes a log entry. PROGRESS.md stays the handoff note; the log is the structured record. If you notice the two have drifted apart (a fact in one and not the other), fill the gap in whichever is missing it. Neither one "wins": both should hold the fact.

Choosing types, in common cases:
- **News that closes an open item:** write one entry that `--resolves` it. If the news also shows an earlier claim was wrong, the same entry may `--corrects` it too.
- **A decision relayed by the user** ("the supervisor decided…"): log it as a `decision`, and say in the body who decided and how it reached us.
- **An agreed action that waits on someone** ("the user will email the supervisor"): write a `followup` with `--related` to the open question. Don't open a second question for the same thing.
- **A rerun that replaces a result:** log the new result with `--related` to the old one. Add a `correction` only if the old result was *wrong* (a bug, bad input). A deliberate change (dropping a sample, a new setting) supersedes it without making it wrong.
- **Other documents that the news makes stale** (dashboards, results docs): don't edit them unless asked. Log a `followup` and mention it to the user.

Timestamps default to the system clock. Pass `--ts` only when the user gives a different time, or when logging something that happened earlier.

## Workflow: figures for results

1. Check whether a figure already exists for the result. If not, propose a chart in one sentence: the chart type and why it fits the comparison. Ask before writing the script.
2. Write a reusable script in `project-log/figures/scripts/<name>.py` that follows [references/figures.md](references/figures.md). It reads the data, writes `figures/out/<name>.json` (interactive Plotly) and `<name>.svg` (static), and runs with `uv run`.
   When a tool draws the figure itself (an R package's plot, ggplot), don't redraw it: save its own output as a PNG or SVG from a script in `figures/scripts/` and log that image as the figure (see figures.md).
3. Run it, then log the result with `--figure`, `--static` and `--fig-script` pointing at those files. The page then shows the chart with the result, in the Timeline and Results tabs; `overview.figure` puts one chart on the Overview as well.

## Workflow: session wrap-up

When the user ends the session ("let's wrap up", "that's all for today"). A one-off request in the middle of work is not a session end.

1. **List what was logged this session**, meaning entries since the conversation started or since the last `session` entry, whichever is later. Also list every open follow-up, blocker and question. Ask: "Anything to add or correct?"
2. **Log the conversation itself.** Things that were discussed or agreed but never logged become entries too, as do the user's additions (corrections as `correction` entries).
3. **Write one `session` entry.** Give it a title like "16 Oct: v2 approved, first blocker", one short paragraph on what happened and what is next, and a `--thread` only if the session was about one thread. Write it directly; the user can correct it later.
4. **Follow the project's own end-of-session rules** as well (e.g. its handoff note in PROGRESS.md, committing).
5. **Offer to rebuild the page**, and to republish the shared link if `published_url` is set.

## Workflow: update the page (build)

When the user asks to update, rebuild or refresh the project log or the page:

1. **Catch up.** Skim PROGRESS.md and the conversation for facts that were never logged, and log them first.
2. **Refresh the overview in `project.yaml`.** This is current state, so editing it is fine. Read [references/writing-style.md](references/writing-style.md) first.
   - `overview.summary`: three cards (Where we are / What we learned / What's next), each 2–3 short bullets of about 12 words at most.
   - `overview.tiles`: 3–4 key numbers, each linked to `R<n>`, `thread:<id>` or `tab:<name>`. Labels are one short line. Change a tile when its number is superseded, or when a newer result matters more to the supervisor.
   - `overview.figure` (optional): the R-number of the one figure that best shows where the project stands.
3. **Build.** Run `uv run $PL/build.py`, from inside the repo. It validates first and stops on errors; fix them, never work around them. If an entry really must change after publishing, run `--accept-edits`, which lists the edit in the Changelog.
4. **Report.** Use the build's printed summary: what was added, closed and corrected, the open loops, and any uncommitted-state notes. Give the page path.
5. **Commit** following ground rule 5, in this order:
   1. Commit the entries, `project.yaml`, `keys.json`, the figures and any code.
   2. Rebuild.
   3. Commit `project-log/report/`.

   A page built before its entries were committed records them as "not committed" for good.
6. **Republish.** If `published_url` is set, offer in one line to republish the shared link. Republish without asking only if the user asked to share or publish.

## Workflow: publish a shareable link

When the user asks for a link to share: publish `project-log/report/project-log.html` with the Artifact tool, if one is available. On the first publish, use the project's short title and the icon `timeline`. Afterwards, republish to the same artifact URL, recorded in `project.yaml` under `published_url`. The link is private until the user shares it from the page's Share menu.

## Setup and backfill

- New project, or "set up the project log": [references/setup.md](references/setup.md). It covers the kickoff round (audience, tabs, figure conventions, how charts load), `setup_project.py`, the CLAUDE.md section and the PROGRESS.md hook.
- Existing history: [references/backfill.md](references/backfill.md). The import from PROGRESS.md, git and run manifests produces `imported` entries. The user reviews them on a `--draft` page and approves them with `mark_reviewed.py` before the first build.

## Problems

- **Validator errors:** fix the cause, never work around it.
- **Files named like `entry 2.md`** are sync-tool copies (iCloud, Dropbox). Compare each with the original, and delete it if they are identical.
- **A lost or damaged log** can be rebuilt from any built page, because every page embeds all entries.
