# Changelog

## 0.3.1 (2026-11-19): the log keeps up with the commits

- **Reminders follow the commits.** In a 10-day project the log fell 5 days behind, because the only reminder fired when PROGRESS.md was edited. The hook now also runs at session start and after each `git commit`: if commits landed since the newest entry, it lists them and asks Claude to log them. It also checks repos one folder down, for sessions started above the repo. Manual installs: run `setup_project.py` again to add the new triggers.
- **PROGRESS.md is created at setup** from a short template, if the project has none. An existing file is never touched.
- **The online page stays in sync.** Once `published_url` is set, every build republishes the artifact, without asking; the build prints a reminder.

## 0.3.0 (2026-11-14): plugin, smaller pages, a real-looking demo

- **Install as a Claude Code plugin** (`/plugin marketplace add chunxubioinfor/project-log-skill`). The plugin brings the progress-notes hook along, so setup no longer writes one into the project. A manual install writes the hook with the real install path.
- **Small pages.** A new kickoff question picks how charts load: `link` (from a CDN, page about 0.3 MB, the default) or `embed` (about 5 MB, works offline). The setting is `figures.plotly` in `project.yaml`.
- **Tables** in entry bodies (Markdown pipe tables).
- **Images as figures.** A result's figure can be a PNG, SVG or JPEG, such as a plot made in R, embedded in the page and locked by checksum like Plotly figures. Tools' own plots no longer have to be redrawn.
- **Thread status at setup** (`id|name|kind|goal|paused`), so a stage that hasn't started isn't drawn as running.
- **Fixes:** Kaleido pinned below 1.5, whose SVG export is broken, and a failed SVG export no longer blocks the figure. `install.sh` can no longer delete a clone inside the skills folder. A `<!--` in any entry no longer blanks the page. A `---` line no longer cuts an entry's body short. Links can no longer inject HTML. A failing batch now writes nothing. `Z` timestamps work on Python 3.9. Entries from different time zones sort correctly. Text pasted from PDFs no longer breaks the build. Paper links in the timeline show the paper's title. Data files too large to hash now get their size and date recorded.
- **Clearer instructions** where a test run guessed: the shell variable, reruns versus corrections, which commit provenance records, and asking for threads only once.
- **New demo:** a real isoform-switch analysis of IsoformSwitchAnalyzeR's example data (`examples/demo/analysis/run_isoform_switch.R`), logged as 33 entries: a duplicated-looking replicate pair found and checked, a second test that disagrees, bugs from a package upgrade, 4 figures (including IsoformSwitchAnalyzeR's own switchPlot, which then prompts a correction) and tables. The people and a few mishaps are made up.

## 0.2.0 (2026-10-26): first shareable version

- **No personal assumptions.** The text setup adds to `CLAUDE.md` names the project's owner, and the progress-notes file is a setting (`progress_file`, e.g. `notes/LABBOOK.md`). The hook only reacts to that file.
- **Published figures are locked by checksum.** New data goes to a new figure, a new result and a correction.
- **Batch entries** come as JSON on stdin, link to each other by `"ref"` / `"@name"`, and support `--dry-run`.
- **The build prints what changed** (added, closed, corrected, open loops), and the page header warns about uncommitted code or log files.
- **Catch-up procedure** for work done without the skill. Sync-tool copies (iCloud/Dropbox) are detected.
- **A made-up demo project** (`examples/demo`) and a smoke test.

## 0.1.0 (2026-10-18): first working version

Tried out on one real project: a backfill of 25 sessions (199 entries), three tests of Claude Code using it, and a rehearsal on a full copy of the repo.
