# /// script
# requires-python = ">=3.9"
# dependencies = ["plotly>=5", "kaleido>=1.4,<1.5"]
# ///
"""R2: isoform switch test (DEXSeq) for all three comparisons: change in isoform fraction vs q-value.
Reads results/isoform_switches.tsv, writes project-log/figures/out/switch_overview.{json,svg}.
Run from the repo root:  uv run project-log/figures/scripts/switch_overview.py
"""
import csv
import math
from pathlib import Path

import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "project-log" / "figures" / "out"
NAME = "switch_overview"
COLOR = {"Fibroblasts vs hESC": "#0E8C78", "Fibroblasts vs iPS": "#C58A12", "hESC vs iPS": "#7A5FB5"}
NS = "#9AA8B5"
DIF, FDR = 0.1, 0.05

rows = [r for r in csv.DictReader(open(ROOT / "results" / "isoform_switches.tsv"), delimiter="\t")
        if r["isoform_switch_q_value"] not in ("", "NA")]
for r in rows:
    r["cmp"] = f"{r['condition_1']} vs {r['condition_2']}"
    r["x"], r["y"] = float(r["dIF"]), -math.log10(float(r["isoform_switch_q_value"]))
    r["sig"] = abs(r["x"]) > DIF and float(r["isoform_switch_q_value"]) < FDR

fig = go.Figure()
ns = [r for r in rows if not r["sig"]]
fig.add_trace(go.Scatter(x=[r["x"] for r in ns], y=[r["y"] for r in ns], mode="markers", name=f"Not significant ({len(ns)})",
                         marker=dict(color=NS, size=6, opacity=0.45), text=[f"{r['gene_name']} · {r['cmp']}" for r in ns],
                         hovertemplate="%{text}<br>dIF %{x:.2f}, −log10 q %{y:.1f}<extra></extra>"))
for cmp, color in COLOR.items():
    sel = [r for r in rows if r["sig"] and r["cmp"] == cmp]
    fig.add_trace(go.Scatter(
        x=[r["x"] for r in sel], y=[r["y"] for r in sel], mode="markers+text", name=f"{cmp} ({len(sel)} isoforms)",
        text=[r["gene_name"] if r["x"] > 0 else "" for r in sel],
        textposition=["top center" if i % 2 else "bottom center" for i in range(len(sel))],   # alternate, so close labels don't overlap
        marker=dict(color=color, size=11, line=dict(width=1, color="#ffffff")),
        customdata=[r["isoform_id"] for r in sel],
        hovertemplate="%{customdata}<br>dIF %{x:.2f}, −log10 q %{y:.1f}<extra>" + cmp + "</extra>"))
for x in (-DIF, DIF):
    fig.add_vline(x=x, line=dict(color=NS, dash="dash", width=1))
fig.add_hline(y=-math.log10(FDR), line=dict(color=NS, dash="dash", width=1))
fig.update_layout(height=480, margin=dict(l=70, r=30, t=20, b=70),
                  xaxis=dict(title="Change in isoform fraction (dIF), second vs first condition", range=[-1, 1], zeroline=False),
                  yaxis=dict(title="−log10 q-value (DEXSeq)", rangemode="tozero"),
                  legend=dict(orientation="h", y=-0.18))
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
