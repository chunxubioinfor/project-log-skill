# /// script
# requires-python = ">=3.9"
# dependencies = ["plotly>=5", "kaleido>=1.4,<1.5"]
# ///
"""R1: how well the two replicates of each cell type agree, isoform by isoform (isoform fraction, replicate 1 vs 2).
Reads results/isoform_fraction_per_sample.tsv and results/replicate_agreement.tsv,
writes project-log/figures/out/replicate_agreement.{json,svg}.
Run from the repo root:  uv run project-log/figures/scripts/replicate_agreement.py
"""
import csv
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "project-log" / "figures" / "out"
NAME = "replicate_agreement"
COLOR = {"Fibroblasts": "#C58A12", "hESC": "#0E8C78", "iPS": "#7A5FB5"}   # conventions: one colour per cell type

rows = list(csv.DictReader(open(ROOT / "results" / "isoform_fraction_per_sample.tsv"), delimiter="\t"))
agree = {r["condition"]: r for r in csv.DictReader(open(ROOT / "results" / "replicate_agreement.tsv"), delimiter="\t")}
fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.05,
                    subplot_titles=[f"{c}: r = {float(agree[c]['pearson_r']):.2f}" for c in COLOR])
for i, c in enumerate(COLOR, 1):
    fig.add_trace(go.Scatter(x=[float(r[f"{c}_0"]) for r in rows], y=[float(r[f"{c}_1"]) for r in rows], mode="markers",
                             name=c, showlegend=False, marker=dict(color=COLOR[c], size=6, opacity=0.7),
                             text=[r["isoform_id"] for r in rows],
                             hovertemplate="%{text}<br>replicate 1: %{x:.2f}<br>replicate 2: %{y:.2f}<extra></extra>"), row=1, col=i)
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color="#9AA8B5", dash="dash", width=1),
                             hoverinfo="skip", showlegend=False), row=1, col=i)
    fig.update_xaxes(title_text="IF, replicate 1", range=[-0.02, 1.02], row=1, col=i)
fig.update_yaxes(title_text="IF, replicate 2", range=[-0.02, 1.02], row=1, col=1)
fig.update_layout(height=380, margin=dict(l=70, r=20, t=40, b=60))
out = OUT / f"{NAME}.json"
if out.exists():
    raise SystemExit(f"{out} exists; a logged figure never changes (write a new output name)")
OUT.mkdir(parents=True, exist_ok=True)
out.write_text(fig.to_json())
fig.update_layout(width=900, template="plotly_white")
try:
    fig.write_image(OUT / f"{NAME}.svg")
except Exception as e:  # no Chrome: the page only needs the JSON
    print(f"SVG skipped ({type(e).__name__})")
print("wrote", out)
