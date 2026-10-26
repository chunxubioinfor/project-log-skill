# /// script
# requires-python = ">=3.9"
# dependencies = ["plotly>=5", "kaleido>=1"]
# ///
"""Demo figure: batch-effect score per sample, baseline vs normalisation v2 (made-up data).

Reads results/batch_effect.tsv, writes project-log/figures/out/batch_effect_v2.{json,svg}.
Run from the demo repo root:  uv run project-log/figures/scripts/batch_effect.py
"""
import csv
from pathlib import Path

import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "project-log" / "figures" / "out"
BASE, NEW, LINE = "#C58A12", "#0E8C78", "#9AA8B5"   # figures.md palette: baseline amber, variant teal

rows = list(csv.DictReader(open(ROOT / "results" / "batch_effect.tsv"), delimiter="\t"))
samples = [r["sample"] for r in rows]
base = [float(r["baseline"]) for r in rows]
new = [float(r["v2"]) for r in rows]

fig = go.Figure()
for s, a, b in zip(samples, base, new):
    fig.add_trace(go.Scatter(x=[a, b], y=[s, s], mode="lines", line=dict(color=LINE, width=2),
                             hoverinfo="skip", showlegend=False))
fig.add_trace(go.Scatter(x=base, y=samples, mode="markers", name="Baseline", marker=dict(color=BASE, size=10),
                         hovertemplate="%{y}<br>baseline: %{x:.2f}<extra></extra>"))
fig.add_trace(go.Scatter(x=new, y=samples, mode="markers", name="Normalisation v2", marker=dict(color=NEW, size=10),
                         hovertemplate="%{y}<br>v2: %{x:.2f}<extra></extra>"))
fig.update_layout(height=520, margin=dict(l=90, r=20, t=20, b=70),
                  xaxis=dict(title="Batch silhouette score (lower = less batch effect)", range=[0, 0.5]),
                  yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=-0.15))
out = OUT / "batch_effect_v2.json"
if out.exists():
    raise SystemExit(f"{out} exists; a logged figure never changes (write a new output name)")
OUT.mkdir(parents=True, exist_ok=True)
out.write_text(fig.to_json())
fig.update_layout(width=900, template="plotly_white")
fig.write_image(OUT / "batch_effect_v2.svg")
print("wrote", out)
