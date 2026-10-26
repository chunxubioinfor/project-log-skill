#!/usr/bin/env bash
# Build a small, entirely made-up demo project with a project log, in two builds.
# Usage: examples/demo/make_demo.sh <empty-dir>   (needs python3, git, uv; Chrome for the SVG)
# All people, data, numbers and papers here are fictional.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PL="${PL:-$HERE/../../skills/project-log/scripts}"
DIR="${1:?usage: make_demo.sh <empty-dir>}"
mkdir -p "$DIR" && cd "$DIR"
# dates(): replace __D<n>__ (n days ago) and __L<n>__ (its "23 Oct" label) in stdin
dates() { python3 -c '
import re, sys, datetime as dt
t = dt.date.today()
s = sys.stdin.read()
s = re.sub(r"__D(\d+)__", lambda m: (t - dt.timedelta(int(m.group(1)))).isoformat(), s)
s = re.sub(r"__L(\d+)__", lambda m: (t - dt.timedelta(int(m.group(1)))).strftime("%-d %b"), s)
print(s)'; }
git init -q && git config user.name "Alex Doe" && git config user.email "alex@example.org"
mkdir -p analysis results docs project-log/figures/scripts
echo '"""Batch-effect comparison (demo stand-in)."""' > analysis/compare_batch.py
printf '# PROGRESS\n\nDemo progress notes.\n' > docs/PROGRESS.md
python3 - <<'PY'
import random
random.seed(7)
with open("results/batch_effect.tsv", "w") as f:
    f.write("sample\tbaseline\tv2\n")
    for i in range(1, 13):
        b = round(random.uniform(0.28, 0.42), 3)
        f.write(f"S{i:02d}\t{b}\t{round(b * random.uniform(0.5, 0.75), 3)}\n")
PY
cp "$HERE/batch_effect_figure.py" project-log/figures/scripts/batch_effect.py
git add -A && git commit -qm "Demo data and analysis stub"

python3 "$PL/setup_project.py" --title "Does the new normalisation reduce batch effects?" \
  --lede "A made-up demo project: we test a new normalisation step against the lab's standard pipeline, one change at a time." \
  --owner "Alex Doe" --group "Example Lab, Example University" --progress-file docs/PROGRESS.md \
  --conventions "The baseline is always amber and the variant teal." \
  --thread "setup|Setup and data|main|Pick a dataset with real batches and pin the pipeline." \
  --thread "norm-v2|Normalisation v2|main|Does the new normalisation reduce batch effects without losing signal?" \
  --thread "tool-bug|Upstream tool crash|side|Report a crash in a dependency and work around it." > /dev/null
# setup and the tool crash are finished threads in the demo
python3 - <<'PY2'
p = "project-log/project.yaml"; t = open(p).read()
for tid in ("setup", "tool-bug"):
    t = t.replace(f"  - id: {tid}\n", f"  - id: {tid}\n", 1)
    i = t.index(f"  - id: {tid}\n"); j = t.index("    status: active", i)
    t = t[:j] + "    status: done" + t[j + len("    status: active"):]
open(p, "w").write(t)
PY2
git add -A && git commit -qm "Set up the project log"

dates <<'EOF' | python3 "$PL/new_event.py" --batch - > /dev/null
[{"type":"term","ts":"__D6__T09:00:00+02:00","title":"batch effect","alias":["batch effects"],"body":"Differences between samples caused by how or when they were processed, not by biology. They can hide real signal or create fake signal."},
 {"type":"term","ts":"__D6__T09:00:00+02:00","title":"silhouette score","body":"A number from 0 to 1 for how strongly samples cluster by a label. Measured on batch labels, lower means the batches mix better, which is what we want."},
 {"type":"term","ts":"__D6__T09:00:00+02:00","title":"normalisation","body":"A processing step that makes measurements from different samples comparable, for example by correcting for sequencing depth."},
 {"type":"progress","thread":"setup","ts":"__D6__T10:30:00+02:00","title":"Project set up and pipeline version pinned","why":"Results must be comparable, so only the normalisation may differ between runs.","what":"Created the repo, pinned the pipeline version and wrote a plan with milestones."},
 {"ref":"q-data","type":"question","thread":"setup","ts":"__D6__T15:00:00+02:00","title":"Which public dataset has real batches and enough samples?","why":"A [[batch effect]] test needs data where the batches are known."},
 {"type":"detour","verdict":"archived","thread":"setup","ts":"__D5__T11:00:00+02:00","title":"First dataset dropped: its batches matched the conditions","why":"If every batch is also a different condition, batch and biology cannot be told apart.","what":"Switched to a dataset where each condition appears in every batch."},
 {"type":"decision","thread":"setup","ts":"__D5__T14:00:00+02:00","title":"Dataset chosen: 12 samples in 3 batches","why":"Each condition appears in every batch, so batch effects can be measured on their own.","what":"Sam agreed. Downloaded once and recorded the version.","resolves":"@q-data","data_version":["demo-dataset=v2.1"]},
 {"type":"bug","thread":"tool-bug","ts":"__D4__T16:47:00+02:00","title":"2 of the first 3 batch jobs crashed in a dependency","why":"The overnight run of all 12 samples would have stopped.","what":"The crash comes from an upstream tool when a sample has no reads in one region. Reported it upstream and added a filter step as a workaround, with a test."},
 {"type":"milestone","thread":"norm-v2","ts":"__D3__T08:10:00+02:00","title":"All 12 samples processed with both pipelines","why":"The comparison needs every sample run both ways.","what":"Baseline and v2 runs finished overnight with no failures."},
 {"type":"session","ts":"__D3__T18:00:00+02:00","title":"__L3__: both runs done, upstream crash worked around","body":"Both pipelines finished on all 12 samples after a workaround for an upstream crash. Next: compare batch effects."}]
EOF
git add -A && git commit -qm "Log the first days"
uv run --quiet "$PL/build.py" > /dev/null
git add -A && git commit -qm "Build the project log"

uv run --quiet project-log/figures/scripts/batch_effect.py > /dev/null
git add -A && git commit -qm "Batch-effect comparison figure"
dates <<'EOF' | python3 "$PL/new_event.py" --batch - > /dev/null
[{"ref":"r-v2","type":"result","thread":"norm-v2","ts":"__D2__T11:20:00+02:00","title":"Normalisation v2 cuts the batch effect by about a third","why":"The point of v2 is to make batches mix while keeping biological differences.","what":"Computed the [[silhouette score]] on batch labels for every sample, baseline vs v2.","so-what":"Batches mix clearly better with v2 in every one of the 12 samples; the next question is whether biological signal survives.","figure":"project-log/figures/out/batch_effect_v2.json","static":"project-log/figures/out/batch_effect_v2.svg","fig-script":"project-log/figures/scripts/batch_effect.py","script":["analysis/compare_batch.py"],"data":["results/batch_effect.tsv"],"key":["Median silhouette=0.22 vs 0.35","Samples improved=12 of 12"]},
 {"type":"followup","thread":"norm-v2","ts":"__D2__T11:40:00+02:00","title":"Check that known marker genes still separate the conditions after v2","why":"A [[normalisation]] that removes batch effects can also remove real biology."},
 {"type":"question","thread":"norm-v2","ts":"__D2__T12:00:00+02:00","title":"Make v2 the lab default, or keep it opt-in until the marker check is done?","why":"v2 helps clearly, but its effect on biological signal is untested."},
 {"type":"correction","thread":"tool-bug","ts":"__D2__T15:00:00+02:00","title":"The crash also happens with empty regions in the baseline, not only in v2","why":"The bug entry suggested v2 triggered it.","what":"Reproduced it with the baseline as well; the workaround covers both."},
 {"type":"session","ts":"__D2__T18:00:00+02:00","title":"__L2__: v2 reduces batch effects; marker check next","body":"Normalisation v2 lowered the batch silhouette score in all 12 samples. Before making it the default, we check that biology survives. One question for Sam."}]
EOF
python3 - <<'PY'
import re
p = "project-log/project.yaml"; t = open(p).read()
t = t.replace("overview:\n  summary: []\n  tiles: []", """overview:
  figure: R1
  summary:
    - "We test a new [[normalisation]] step against the lab's standard pipeline on 12 samples in 3 batches. Both pipelines ran on every sample after a workaround for an upstream crash."
    - "Normalisation v2 lowers the batch silhouette score in all 12 samples (median 0.22 vs 0.35), so batches mix clearly better."
    - "Next: check that known marker genes still separate the conditions. Sam needs to decide whether v2 becomes the default now or after that check."
  tiles:
    - value: "12 / 12"
      label: samples where v2 reduces the batch effect
      link: R1
    - value: "0.22"
      label: median batch silhouette with v2 (baseline 0.35)
      link: R1
    - value: "1"
      label: decision waiting for the supervisor
      link: tab:loops""")
open(p, "w").write(t)
PY
git add -A && git commit -qm "Log the v2 result"
uv run --quiet "$PL/build.py" > /dev/null
git add -A && git commit -qm "Rebuild the project log"
echo "demo ready: $DIR/project-log/report/project-log.html"
