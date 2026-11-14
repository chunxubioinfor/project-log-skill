# /// script
# requires-python = ">=3.9"
# dependencies = ["plotly>=5", "kaleido>=1.4,<1.5"]
# ///
"""R3: isoform usage of ARHGEF19 in each sample (stacked isoform fractions).
Reads results/isoform_fraction_per_sample.tsv, writes project-log/figures/out/arhgef19_isoform_usage.{json,svg}.
Run from the repo root:  uv run project-log/figures/scripts/isoform_usage.py
"""
import csv
from pathlib import Path

import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "project-log" / "figures" / "out"
NAME = "arhgef19_isoform_usage"
ISOFORMS = {"TCONS_00004208": ("#0E8C78", "TCONS_00004208 (main isoform in hESC)"),
            "TCONS_00004210": ("#7A5FB5", "TCONS_00004210 (main isoform in iPS)")}

rows = {r["isoform_id"]: r for r in csv.DictReader(open(ROOT / "results" / "isoform_fraction_per_sample.tsv"), delimiter="\t")}
samples = [k for k in next(iter(rows.values())) if k != "isoform_id"]
fig = go.Figure()
for iso, (color, label) in ISOFORMS.items():
    fig.add_trace(go.Bar(x=samples, y=[float(rows[iso][s]) for s in samples], name=label, marker_color=color,
                         hovertemplate="%{x}<br>" + iso + ": %{y:.2f}<extra></extra>"))
other = [1 - sum(float(rows[i][s]) for i in ISOFORMS) for s in samples]
fig.add_trace(go.Bar(x=samples, y=other, name="other isoforms", marker_color="#9AA8B5", opacity=0.5,
                     hovertemplate="%{x}<br>other isoforms: %{y:.2f}<extra></extra>"))
fig.update_layout(barmode="stack", height=420, margin=dict(l=70, r=20, t=20, b=70),
                  yaxis=dict(title="Isoform fraction of ARHGEF19", range=[0, 1]),
                  xaxis=dict(title="Sample (2 replicates per cell type)"), legend=dict(orientation="h", y=-0.22))
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
