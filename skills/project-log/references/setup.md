# Setup: start a project log

Use this when the user asks to set up the project log in a repo that has no `project-log/project.yaml` yet.

## 1. Look before asking

Read the README, the project brief, CLAUDE.md and the newest progress notes. From them, work out the facts yourself:
- the research question and the title
- the owner and group
- the main stages and the side projects (the threads)
- where data versions are recorded (run manifests, database fetch logs, accession numbers)

Do not ask the user for facts. Ask only for decisions.

## 2. Kickoff round (one message)

Ask three numbered questions. Each comes with a recommended answer, worded so the user can reply "1 yes, 2 yes, 3 …":

1. **Audience.** Who reads the page?
   ➡️ Recommended: *layered*. A two-minute summary for the supervisor on top, full detail below for the user.
   Other options: *self* (dense lab notebook), *others* (polished, internal detail kept minimal), *non-technical* (heavier explanation).
2. **Tabs.** Which tabs should the page have? Overview, Timeline, Results, Side projects, Open loops, Next steps, Digests, Glossary, Changelog.
   ➡️ Recommended: all. Drop Side projects if there are none.
3. **Figure conventions.** Propose one or two that fit the project, e.g. "baseline is always amber and the variant teal", "samples always in the same order", "counts exclude controls".
   ➡️ Recommended: the proposal, unless the user has a house style.

Also show the proposed threads as a short table (id, name, main/side, one-line goal) and ask the user to confirm or correct them.

## 3. Run the setup script

From the repo root:

```bash
python3 $PL/setup_project.py --title "..." --lede "..." --owner "..." --group "..." \
  --audience layered --tabs overview,timeline,results,side,loops,next,digests,glossary,changelog \
  --conventions "..." \
  --thread "baseline|Baseline|main|Run the standard pipeline and lock it as the reference" \
  --thread "norm-v2|Normalisation v2|main|Does the new normalisation reduce batch effects?" \
  --thread "tool-bug|Upstream tool bug|side|Report and work around a crash in a dependency"
```

It creates the `project-log/` folders, writes `project.yaml` (an existing one is never overwritten), adds a "Project log" section to CLAUDE.md between markers, and adds the PROGRESS.md reminder hook to `.claude/settings.json`. It is safe to run again.

**If sessions start in a different folder** (e.g. on a shared cluster where Claude Code is started one folder above the repo), hooks are read only from that root's `.claude/`. The script prints a note when it sees a parent `.claude/`. Add the hook there too:

```bash
python3 $PL/setup_project.py --hooks-only --settings /path/to/parent/.claude/settings.json
```

The hook calls the installed skill at `~/.claude/skills/project-log/hooks/progress_reminder.py`, and stays silent if that file is missing. Every machine that should get reminders needs the skill installed.

## 4. Then

- If the repo has history, run the backfill ([backfill.md](backfill.md)).
- Otherwise, write a first `progress` entry ("Project log started"), and build.
- Commit `project-log/`, CLAUDE.md and `.claude/settings.json` following the project's git rules. Hooks from project settings run only once the folder is trusted in Claude Code.

## Synced folders

If the repo is inside iCloud Drive (Desktop & Documents sync), Dropbox or OneDrive, the sync tool can create copies such as `entry 2.md`. The validator reports them. Mention this to the user once: keeping git repos outside synced folders avoids the problem entirely.
