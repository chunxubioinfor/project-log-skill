# Figures

Every figure is made by a script that can be rerun. The script writes two outputs: interactive Plotly JSON for the page, and a static SVG for slides and papers.

## Choosing the chart

Propose the chart in one sentence before writing code, e.g. "A dumbbell per sample, because the point is the gap between the old and new method in each sample." Then wait for the user's OK.

| The question | Chart |
|---|---|
| Is A bigger than B, across a few groups? | dot plot or bar chart, with intervals if available |
| How big is the gap between two paired values per item? | dumbbell (two dots joined by a line) |
| How do values spread, per group? | box plot or violin plot with the points shown (n < 200) |
| How does something change over runs or time? | line chart |
| How do two measures relate? | scatter plot, with an identity line if the two use the same scale |
| Which items overlap between sets? | bars of set sizes (UpSet-style); avoid Venn diagrams for more than 3 sets |
| Effect versus significance (omics) | volcano plot with thresholds drawn and n per side labelled |
| Many features by many samples | heatmap with a diverging scale for centred data |

Always show n. Label the axes with units. Use percentages only where the denominator is clear.

## Script template

```python
# /// script
# requires-python = ">=3.9"
# dependencies = ["plotly>=5", "kaleido>=1"]
# ///
"""<R-number>: <what the figure shows>. Reads <input>, writes project-log/figures/out/<name>.{json,svg}.
Run from the repo root:  uv run project-log/figures/scripts/<name>.py
"""
from pathlib import Path
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[3]          # repo root
OUT = ROOT / "project-log" / "figures" / "out"
A, B = "#0E8C78", "#C58A12"                          # palette below

# ... read data from ROOT / "results" / ...; build fig ...
fig.update_layout(height=520, margin=dict(l=80, r=20, t=20, b=70),
                  xaxis=dict(title="..."), yaxis=dict(title="..."),
                  legend=dict(orientation="h", y=-0.15))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "<name>.json").write_text(fig.to_json())      # interactive version (page restyles it)
fig.update_layout(width=900, template="plotly_white")   # static copy: white background, visible grid
fig.write_image(OUT / "<name>.svg")                  # static version (needs Chrome; run on the Mac)
```

Rules:
- **A logged figure never changes.** `new_event.py` stores a checksum of the figure files, and the build refuses to run if they change. When the data changes (a rerun, a bug fix), write the new figure to a **new output name** (include the run id or a version, e.g. `stage2_ptm_core_20261021.json`). Log it as a new result, and add a `correction` entry that points at the old result. Scripts that serve several results should build their output names from the run id, so a rerun never overwrites an older figure.
- Read the data from files in the repo. Never paste numbers into the script.
- Don't set a fixed `width` before writing the JSON; the page makes the chart responsive. The page also restyles fonts, grid lines and background for light and dark mode. Set marker colours explicitly.
- `write_image` needs Chrome through Kaleido. If it fails (e.g. on a cluster without Chrome), write only the JSON and make the SVG on the Mac later.

## Palette

Mid-tone colours that read on both light and dark backgrounds:

| Use | Colour |
|---|---|
| main series / "ours" / gained | `#0E8C78` (teal) |
| comparison / control / baseline | `#C58A12` (amber) |
| third series | `#7A5FB5` (violet) |
| fourth series | `#3B6FC4` (blue) |
| problem / failure | `#C4473A` (red) |
| neutral / connectors | `#9AA8B5` (grey) |

Keep one meaning per colour across the project. For example, if baseline is amber in one figure, it is amber everywhere. Record such conventions in `project.yaml` under `figures.conventions`.
