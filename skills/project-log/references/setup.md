# Setup: start a project log

Use this when the user asks to set up the project log in a repo that has no `project-log/project.yaml` yet.

## 1. Look before asking

Read the README, the project brief, CLAUDE.md and the newest progress notes. From them, work out the facts yourself:
- the research question and a short title (under about 50 characters; details go in the lede)
- the owner and group
- the main stages and the side projects (the threads)
- where data versions are recorded (run manifests, database fetch logs, accession numbers)

Do not ask the user for facts. Ask only for decisions.

## 2. Kickoff round (one message)

Ask four numbered questions. Each comes with a recommended answer, worded so the user can reply "1 yes, 2 yes, 3 …":

1. **Audience.** Who reads the page?
   ➡️ Recommended: *layered*. A two-minute summary for the supervisor on top, full detail below for the user.
   Other options: *self* (dense lab notebook), *others* (polished, internal detail kept minimal), *non-technical* (heavier explanation).
2. **Tabs.** Which tabs should the page have? Overview, Timeline, Results, Side projects, Open loops, Next steps, Digests, Glossary, Changelog.
   ➡️ Recommended: all. Drop Side projects if there are none.
3. **Figure conventions.** Propose one or two that fit the project, e.g. "baseline is always amber and the variant teal", "samples always in the same order", "counts exclude controls".
   ➡️ Recommended: the proposal, unless the user has a house style.
4. **Charts on the page.** Results can carry interactive charts (Plotly). The chart library is about 4.7 MB. Should the page *link* it from a CDN, or *embed* it?
   ➡️ Recommended: *link*. The page stays around 0.3 MB, so committing it after every build costs little; charts need an internet connection to draw.
   Other option: *embed*, for a page that must work offline (e.g. sent as an email attachment to someone without internet). Pass the answer as `--plotly link|embed`; it can be changed later in `project.yaml` under `figures.plotly`.

Also show the proposed threads as a short table (id, name, main/side, one-line goal) and ask the user to confirm or correct them.

## 3. Run the setup script

From the repo root:

```bash
python3 $PL/setup_project.py --title "..." --lede "..." --owner "..." --group "..." \
  --audience layered --tabs overview,timeline,results,side,loops,next,digests,glossary,changelog \
  --conventions "..." --progress-file docs/PROGRESS.md --plotly link \
  --thread "baseline|Baseline|main|Run the standard pipeline and lock it as the reference" \
  --thread "norm-v2|Normalisation v2|main|Does the new normalisation reduce batch effects?" \
  --thread "tool-bug|Upstream tool bug|side|Report and work around a crash in a dependency" \
  --thread "gsea|Pathway analysis|main|Which pathways change?|paused"
```

A thread's optional fifth field sets its status (`active`, `done` or `paused`; default `active`). Use `paused` for a stage that hasn't started, so the Gantt chart doesn't draw it as running.

It creates the `project-log/` folders, writes `project.yaml` (an existing one is never overwritten), adds a "Project log" section to CLAUDE.md between markers, and sets up the PROGRESS.md reminder hook (see below). It is safe to run again.

**If sessions start in a different folder** (e.g. on a shared cluster where Claude Code is started one folder above the repo), hooks are read only from that root's `.claude/`. The script prints a note when it sees a parent `.claude/`. Add the hook there too:

```bash
python3 $PL/setup_project.py --hooks-only --settings /path/to/parent/.claude/settings.json
```

**How the reminder hook is installed** depends on how the skill was installed:
- **As a plugin** (`/plugin install`): the plugin brings the hook along, for every project. It stays silent unless the edited file is the progress notes of a project with a `project-log/` folder. `setup_project.py` adds nothing to `.claude/settings.json`.
- **By hand** (`install.sh`): `setup_project.py` adds the hook to the project's `.claude/settings.json`, pointing at the installed copy (`$HOME/.claude/skills/project-log/...`). It stays silent where that file is missing, e.g. for a collaborator who uses the plugin, whose own hook covers it.

Either way, every machine that should get reminders needs the skill installed.

## 4. Then

- If the repo has history, run the backfill ([backfill.md](backfill.md)).
- Otherwise, write a first `progress` entry ("Project log started"), and build.
- Commit `project-log/`, CLAUDE.md and `.claude/settings.json` following the project's git rules. Hooks from project settings run only once the folder is trusted in Claude Code.

## Synced folders

If the repo is inside iCloud Drive (Desktop & Documents sync), Dropbox or OneDrive, the sync tool can create copies such as `entry 2.md`. The validator reports them. Mention this to the user once: keeping git repos outside synced folders avoids the problem entirely.
