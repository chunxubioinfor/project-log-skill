# Changelog

## 0.2.0 (2026-10-26): first shareable version

- **No personal assumptions.** The text setup adds to `CLAUDE.md` names the project's owner, and the progress-notes file is a setting (`progress_file`, e.g. `notes/LABBOOK.md`). The hook only reacts to that file.
- **Published figures are locked by checksum.** New data goes to a new figure, a new result and a correction.
- **Batch entries** come as JSON on stdin, link to each other by `"ref"` / `"@name"`, and support `--dry-run`.
- **The build prints what changed** (added, closed, corrected, open loops), and the page header warns about uncommitted code or log files.
- **Catch-up procedure** for work done without the skill. Sync-tool copies (iCloud/Dropbox) are detected.
- **A made-up demo project** (`examples/demo`) and a smoke test.

## 0.1.0 (2026-10-18): first working version

Tried out on one real project: a backfill of 25 sessions (199 entries), three tests of Claude Code using it, and a rehearsal on a full copy of the repo.
