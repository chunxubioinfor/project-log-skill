#!/usr/bin/env bash
# Build the demo: an isoform-switch pilot on IsoformSwitchAnalyzeR's example data, with three weeks of project log.
# Usage: examples/demo/make_demo.sh <empty-dir>   (needs python3, git, uv; Chrome for the SVG copies)
# The results in data/ are real output of analysis/run_isoform_switch.R on the package's example data
# (IsoformSwitchAnalyzeR 2.11.2). The people, and the annotation and licence mishaps, are made up.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PL="${PL:-$HERE/../../skills/project-log/scripts}"
DIR="${1:?usage: make_demo.sh <empty-dir>}"
[ -z "$(ls -A "$DIR" 2>/dev/null)" ] || { echo "error: $DIR is not empty" >&2; exit 1; }
mkdir -p "$DIR" && cd "$DIR"
# dates(): replace __D<n>__ (n days ago) and __L<n>__ (its "23 Oct" label) in stdin
dates() { python3 -c '
import re, sys, datetime as dt
t = dt.date.today()
s = sys.stdin.read()
s = re.sub(r"__D(\d+)__", lambda m: (t - dt.timedelta(int(m.group(1)))).isoformat(), s)
s = re.sub(r"__L(\d+)__", lambda m: (t - dt.timedelta(int(m.group(1)))).strftime("%-d %b"), s)
print(s)'; }
log() { dates | sed -e "s/__FIX1__/$FIX1/g" -e "s/__FIX2__/$FIX2/g" -e "s/__FIX3__/$FIX3/g" | python3 "$PL/new_event.py" --batch - > /dev/null; }
build() { uv run --quiet "$PL/build.py" > /dev/null; git add -A && git commit -qm "Rebuild the project log"; }
FIX1=none FIX2=none FIX3=none

git init -q && git config user.name "Jonas Berg" && git config user.email "jonas@example.org"
mkdir -p analysis results docs project-log/figures/scripts
cat > README.md <<'EOF'
# Isoform switches in reprogramming (pilot)
Isoform switch analysis of the example data that ships with IsoformSwitchAnalyzeR: Salmon quantifications of
fibroblasts, iPS cells and human embryonic stem cells, 2 replicates each. Run: Rscript analysis/run_isoform_switch.R results/
EOF
printf '# Progress\n\nHand-written session notes (demo).\n' > docs/PROGRESS.md
# the script as first written (for version 1 of the package, and the wrong annotation); fixed in later commits
sed -e 's|isoformExonAnnoation = ext("example.gtf.gz")|isoformExonAnnoation = "annotation/gencode.v44.annotation.gtf.gz"|' \
    -e 's|sl <- preFilter(sl, removeSingleIsoformGenes = TRUE, quiet = TRUE)   # package defaults for count and IF cutoffs|sl <- preFilter(sl, geneExpressionCutoff = 1, isoformExpressionCutoff = 0, removeSingleIsoformGenes = TRUE, quiet = TRUE)|' \
    -e '/extractSequence(sl/d' "$HERE/analysis/run_isoform_switch.R" > analysis/run_isoform_switch.R
cp "$HERE"/figures/*.py "$HERE"/figures/*.R project-log/figures/scripts/
git add -A && git commit -qm "Isoform switch workflow, first version"

python3 "$PL/setup_project.py" --title "Isoform switches in reprogramming" \
  --lede "Do iPS cells use the same isoforms as embryonic stem cells? A project-log demo (github.com/chunxubioinfor/project-log-skill) on real IsoformSwitchAnalyzeR example data; people and some mishaps are made up." \
  --owner "Jonas Berg" --group "RNA Biology Lab, Example University" --progress-file docs/PROGRESS.md --plotly link \
  --conventions "Fibroblasts are always amber, hESC teal and iPS violet. Not significant is grey." \
  --thread "data|Data and QC|main|Get the example data in, and check it before trusting it.|done" \
  --thread "switch|Isoform switches|main|Which genes switch isoforms between fibroblasts, iPS cells and embryonic stem cells?|done" \
  --thread "conseq|Functional consequences|main|What do the switches do to the proteins?" \
  --thread "pipeline|Pipeline for our samples|side|Turn the workflow into a pipeline for the lab's own RNA-seq.|paused" > /dev/null
git add -A && git commit -qm "Set up the project log"

# ---------------------------------------------------------------- week 1: getting the data in
sed -i.bak 's|isoformExonAnnoation = "annotation/gencode.v44.annotation.gtf.gz"|isoformExonAnnoation = ext("example.gtf.gz")|' analysis/run_isoform_switch.R
git add analysis && git commit -qm "Use the annotation the quantification was made with" && FIX1=$(git rev-parse --short HEAD)
sed -i.bak 's|sl <- preFilter(sl, geneExpressionCutoff = 1, isoformExpressionCutoff = 0, removeSingleIsoformGenes = TRUE, quiet = TRUE)|sl <- preFilter(sl, removeSingleIsoformGenes = TRUE, quiet = TRUE)   # package defaults for count and IF cutoffs|' analysis/run_isoform_switch.R
rm analysis/run_isoform_switch.R.bak
git add analysis && git commit -qm "preFilter: arguments of IsoformSwitchAnalyzeR 2.x" && FIX2=$(git rev-parse --short HEAD)
cp "$HERE"/data/library_sizes.tsv "$HERE"/data/filtering.tsv results/
git add -A && git commit -qm "Import and filtering results"
log <<'EOF'
[{"type":"term","ts":"__D20__T09:00:00+01:00","title":"isoform","alias":["isoforms"],"body":"One of several versions of a gene's RNA, made by joining different pieces (exons) of the gene. Different isoforms can make different proteins."},
 {"type":"term","ts":"__D20__T09:00:00+01:00","title":"iPS cell","alias":["iPS cells","iPS","induced pluripotent stem cell"],"body":"Induced pluripotent stem cell: an adult cell, here a fibroblast, reprogrammed in the lab to behave like an embryonic stem cell."},
 {"type":"term","ts":"__D20__T09:00:00+01:00","title":"hESC","alias":["human embryonic stem cell","embryonic stem cells"],"body":"Human embryonic stem cell: the natural stem cell that iPS cells try to copy."},
 {"type":"progress","thread":"data","ts":"__D20__T10:00:00+01:00","title":"Project log started: an isoform-switch pilot on IsoformSwitchAnalyzeR's example data","why":"We want to learn the workflow on public data before our own samples are sequenced.","what":"The package ships Salmon quantifications of 6 samples: fibroblasts, [[iPS cell|iPS cells]] and human embryonic stem cells ([[hESC]]), 2 replicates each, with the matching annotation, [[isoform]] sequences and precomputed protein annotations.","data-version":["IsoformSwitchAnalyzeR=2.11.2","annotation=example.gtf.gz (shipped with the data)"]},
 {"type":"bug","thread":"data","ts":"__D19__T11:30:00+01:00","title":"The import matched 0 isoforms: we had used a different annotation from the quantification","why":"importRdata() stopped because none of the isoform IDs in the Salmon files appeared in the annotation.","what":"The Salmon files use the IDs of the annotation they were made with (TCONS_…); our script pointed at GENCODE (ENST…). Switched to the annotation shipped with the data, and all 1,092 isoforms matched.","commit":["__FIX1__"]},
 {"type":"bug","thread":"data","ts":"__D19__T15:10:00+01:00","title":"Our script, written for version 1 of the package, failed on version 2.11","why":"preFilter() stopped with \"unused arguments (geneExpressionCutoff = 1, isoformExpressionCutoff = 0)\".","what":"Those filter arguments were removed in version 2. We now use the package defaults and record the package version with every result.","commit":["__FIX2__"]},
 {"type":"milestone","thread":"data","ts":"__D18__T16:00:00+01:00","title":"All 6 samples imported: 249 isoforms in 103 genes pass the filter","why":"Every later step reads this filtered set.","what":"1,092 isoforms in 368 genes imported; 249 in 103 genes remain after removing lowly used isoforms and genes with a single isoform. The example covers only a small set of genes, so read counts are far below a full library.","body":"| Sample | Cell type | Reads assigned | Isoforms above 1 TPM |\n|---|---|---:|---:|\n| Fibroblasts_0 | fibroblast | 882,734 | 745 |\n| Fibroblasts_1 | fibroblast | 983,467 | 736 |\n| hESC_0 | hESC | 549,924 | 864 |\n| hESC_1 | hESC | 552,242 | 859 |\n| iPS_0 | iPS | 336,789 | 723 |\n| iPS_1 | iPS | 310,502 | 696 |","script":["analysis/run_isoform_switch.R"],"data":["results/library_sizes.tsv","results/filtering.tsv"]},
 {"ref":"f-depth","type":"followup","thread":"data","ts":"__D18__T16:30:00+01:00","title":"The iPS samples have a third of the fibroblast reads: check whether that limits the iPS comparisons","why":"Fewer reads means less precise isoform fractions."},
 {"type":"session","ts":"__D18__T18:00:00+01:00","title":"__L18__: data in, after two false starts","body":"Imported the example data after fixing a wrong annotation and a script written for an older version of the package. 249 isoforms in 103 genes pass the filter. The iPS samples have notably fewer reads. Next: the switch test."}]
EOF
build

# ---------------------------------------------------------------- week 2: switches, and a problem with the replicates
cp "$HERE"/data/*.tsv "$HERE"/data/switchList.rds results/
uv run --quiet project-log/figures/scripts/switch_overview.py > /dev/null
uv run --quiet project-log/figures/scripts/replicate_agreement.py > /dev/null
git add -A && git commit -qm "Switch test, replicate check, satuRn cross-check"
log <<'EOF'
[{"type":"term","ts":"__D17__T09:00:00+01:00","title":"isoform fraction","alias":["IF"],"body":"The share of a gene's expression that comes from one isoform, from 0 to 1."},
 {"type":"term","ts":"__D17__T09:00:00+01:00","title":"dIF","alias":["change in isoform fraction"],"body":"Difference in isoform fraction between two conditions. A dIF of 0.7 means the isoform's share of the gene rose by 70 percentage points."},
 {"type":"term","ts":"__D17__T09:00:00+01:00","title":"isoform switch","alias":["isoform switches","switch","switches","switching"],"body":"A gene that changes which isoform it mainly uses between conditions. Counted here when an isoform's share changes by more than 0.1 (|dIF| > 0.1) at q < 0.05."},
 {"ref":"pap-isar","type":"paper","thread":"switch","ts":"__D17__T10:00:00+01:00","title":"IsoformSwitchAnalyzeR finds isoform switches and predicts what they do to the protein","citation":"Vitting-Seerup K, Sandelin A. IsoformSwitchAnalyzeR: analysis of changes in genome-wide patterns of alternative splicing and its functional consequences. Bioinformatics 2019;35(21):4469–4471.","doi":"10.1093/bioinformatics/btz247","finding":"An R package that tests for isoform switches between conditions and annotates the isoforms involved (open reading frame, protein domains, signal peptides, coding potential, NMD sensitivity) to predict the consequences of each switch.","why-it-matters":"Our whole workflow."},
 {"ref":"pap-dexseq","type":"paper","thread":"switch","ts":"__D17__T10:30:00+01:00","title":"Differential exon usage can be tested with a model that learns the variation between replicates","citation":"Anders S, Reyes A, Huber W. Detecting differential usage of exons from RNA-seq data. Genome Research 2012;22(10):2008–2017.","doi":"10.1101/gr.133744.111","finding":"Tests whether the share of a gene's reads on each exon differs between conditions, with a generalised linear model that estimates the variation between biological replicates.","why-it-matters":"IsoformSwitchAnalyzeR applies this test to isoforms. It relies on the replicates to tell real differences from noise."},
 {"ref":"first-count","type":"progress","thread":"switch","ts":"__D16__T10:00:00+01:00","title":"First look at the switch test: 4 genes switch","paper":"@pap-isar","why":"A quick count from the top-switch list before looking closer.","what":"extractTopSwitches() lists ARHGEF19, LYPLA2, SRM and MEGF6."},
 {"type":"correction","thread":"switch","ts":"__D16__T14:00:00+01:00","title":"5 genes switch, not 4: the top-switch list hides switches without a predicted consequence","corrects":"@first-count","why":"The switch summary reports 5 genes.","what":"extractTopSwitches() was run with filterForConsequences = TRUE, which drops SPSB1: it switches, but no consequence is predicted for it."},
 {"type":"result","thread":"switch","ts":"__D16__T16:00:00+01:00","title":"5 genes switch isoforms, and every switch involves the iPS cells","paper":"@pap-dexseq","why":"The main question: where do iPS cells differ from fibroblasts and from embryonic stem cells?","what":"DEXSeq test in IsoformSwitchAnalyzeR, all three pairs of cell types, on 249 isoforms in 103 genes. No switch between fibroblasts and hESC at all.","body":"| Gene | Comparison | Main isoform's share | q-value |\n|---|---|---:|---:|\n| ARHGEF19 | hESC → iPS | 0.80 → 0.10 | 0.0001 |\n| LYPLA2 | hESC → iPS | 0.74 → 0.16 | 0.004 |\n| SRM | hESC → iPS | 0.92 → 0.47 | 0.010 |\n| MEGF6 | fibroblasts → iPS | 0.92 → 0.19 | 0.018 |\n| SPSB1 | fibroblasts → iPS | 0.91 → 0.13 | 0.018 |","so-what":"If real, iPS cells use different isoforms from both other cell types in these genes. But finding nothing between fibroblasts and stem cells, while every hit involves iPS, is suspicious.","figure":"project-log/figures/out/switch_overview.json","static":"project-log/figures/out/switch_overview.svg","fig-script":"project-log/figures/scripts/switch_overview.py","script":["analysis/run_isoform_switch.R"],"data":["results/isoform_switches.tsv","results/switch_summary.tsv"],"key":["Genes switching=5 (10 isoforms)","Involving iPS=5 of 5","Fibroblasts vs hESC=0 switches"]},
 {"type":"result","thread":"data","ts":"__D15__T11:00:00+01:00","title":"The two iPS replicates are near-identical: r = 1.00, against 0.89 and 0.87 for the other cell types","why":"Every switch involves iPS, so we checked how well the replicates of each cell type agree.","what":"Compared replicate 1 with replicate 2 for the 249 filtered isoforms.","body":"| Cell type | Pearson r | Median difference in isoform fraction |\n|---|---:|---:|\n| Fibroblasts | 0.89 | 0.065 |\n| hESC | 0.87 | 0.042 |\n| iPS | 1.00 | 0.0008 |","so-what":"Separate cultures never agree this closely; iPS_0 and iPS_1 look like one library counted twice. The test would then see almost no variation in iPS cells, which could explain why all 5 switches involve iPS. Leading explanation, not confirmed.","figure":"project-log/figures/out/replicate_agreement.json","static":"project-log/figures/out/replicate_agreement.svg","fig-script":"project-log/figures/scripts/replicate_agreement.py","script":["analysis/run_isoform_switch.R"],"data":["results/replicate_agreement.tsv","results/isoform_fraction_per_sample.tsv"],"key":["iPS replicates, r=1.00","Fibroblasts, r=0.89","hESC, r=0.87"]},
 {"type":"detour","verdict":"kept-after-review","thread":"switch","ts":"__D14__T15:00:00+01:00","title":"A second test (satuRn) finds no switches at all","why":"If the iPS switches depend on the replicates' low variation, another method should disagree.","what":"isoformSwitchTestSatuRn() on the same filtered data: no isoform passes, and the smallest q-value is 0.08. We keep the DEXSeq results as the main test, with the replicate caveat attached.","data":["results/saturn_check.tsv"]},
 {"ref":"q-ips","type":"question","thread":"switch","ts":"__D14__T16:00:00+01:00","title":"Treat iPS_0 and iPS_1 as a single sample, and drop the iPS switches from the conclusions?","why":"If they are one library counted twice, the iPS comparisons have no real replicates.","body":"Option A: report the iPS switches only as leads. Option B: first find out how the example data were made. Needs Sam's call."},
 {"type":"progress","thread":"data","ts":"__D13__T11:00:00+01:00","title":"Lower depth does not explain the iPS problem","resolves":"@f-depth","why":"The fewer reads in iPS samples were the first suspect.","what":"iPS samples still detect 696–723 isoforms above 1 TPM, close to the fibroblasts (736–745). Low depth makes estimates noisier, not more alike, so it cannot explain replicates that agree perfectly."},
 {"type":"session","ts":"__D13__T18:00:00+01:00","title":"__L13__: 5 switches, but the iPS replicates look duplicated","body":"The switch test finds 5 genes, all involving iPS cells, and none between fibroblasts and stem cells. The iPS replicates agree perfectly, and satuRn finds no switches, so the iPS hits are doubtful. Question for Sam on how to treat them."}]
EOF
build

# ---------------------------------------------------------------- week 3: consequences, and a pipeline for our own data
sed -i.bak 's|^sl <- analyzeCPC2(|sl <- extractSequence(sl, writeToFile = FALSE, quiet = TRUE)   # needed before the consequence analysis\nsl <- analyzeCPC2(|' analysis/run_isoform_switch.R && rm analysis/run_isoform_switch.R.bak
git add analysis && git commit -qm "Extract ORF sequences before the consequence analysis" && FIX3=$(git rev-parse --short HEAD)
uv run --quiet project-log/figures/scripts/isoform_usage.py > /dev/null
# switchPlot() output, made by figures/scripts/arhgef19_switchplot.R; copied prebuilt so the demo builds without R
mkdir -p project-log/figures/out && cp "$HERE"/figures/prebuilt/arhgef19_switchplot.* project-log/figures/out/
git add -A && git commit -qm "Figures: ARHGEF19 isoform usage and switchPlot"
log <<'EOF'
[{"ref":"b-signalp","type":"blocker","thread":"conseq","ts":"__D12__T10:00:00+01:00","title":"SignalP 6 needs an academic licence before we can annotate isoforms ourselves","why":"The consequence analysis compares protein features (domains, signal peptides, coding potential, disorder) between the isoforms of each switch."},
 {"type":"decision","thread":"conseq","ts":"__D11__T14:00:00+01:00","title":"For the pilot, use the protein annotations that ship with the example data","resolves":"@b-signalp","why":"The package includes precomputed Pfam, SignalP, CPC2 and IUPred2A results for exactly these isoforms.","what":"Sam agreed. We run the tools ourselves once the licence arrives, for the lab's own samples."},
 {"type":"bug","thread":"conseq","ts":"__D11__T16:30:00+01:00","title":"The consequence analysis stopped: amino-acid sequences have to be extracted first","why":"analyzeSwitchConsequences() stopped with \"The transcrip ORF amino acid sequences must be added … by using the 'extractSequence()' function\".","what":"Added extractSequence() before the protein annotations; the script now runs from start to end.","commit":["__FIX3__"]},
 {"type":"term","ts":"__D10__T09:00:00+01:00","title":"ORF","alias":["open reading frame","ORFs"],"body":"Open reading frame: the part of an RNA that is read to make the protein. A longer ORF usually means a longer protein."},
 {"type":"result","thread":"conseq","ts":"__D10__T15:00:00+01:00","title":"In 4 of the 5 switching genes, the isoform used in iPS cells makes a different protein","paper":"@pap-isar","why":"A switch matters most if it changes the protein.","what":"ARHGEF19 moves from TCONS_00004208 (80% of the gene in hESC) to TCONS_00004210 (90% in iPS). The iPS isoform has a longer [[ORF]] and gains a protein domain and a disordered region. MEGF6's iPS isoform also gains a domain; LYPLA2's ORF gets longer and SRM's shorter. No consequence is predicted for SPSB1.","so-what":"If the iPS switches are real, iPS cells make other versions of these proteins than stem cells do. Until the replicate question is settled, this is a lead, not a finding.","figure":"project-log/figures/out/arhgef19_isoform_usage.json","static":"project-log/figures/out/arhgef19_isoform_usage.svg","fig-script":"project-log/figures/scripts/isoform_usage.py","script":["analysis/run_isoform_switch.R"],"data":["results/switch_consequences.tsv","results/isoform_fraction_per_sample.tsv"],"key":["Genes with a protein change=4 of 5","ARHGEF19, main isoform's share=0.80 → 0.10","Domains gained=2 genes"]},
 {"ref":"r-arhgef19","type":"result","thread":"conseq","ts":"__D9__T11:00:00+01:00","title":"ARHGEF19's main isoform in hESC lacks the RhoGEF domain; the one in iPS cells has it","result-ref":"R3","why":"ARHGEF19 is the strongest switch, and which domain is gained decides what the protein can do.","what":"The isoform used in hESC (TCONS_00004208, 80% of the gene) starts later in the gene and encodes about 280 amino acids with only an SH3 domain. The isoform used in iPS cells (TCONS_00004210, 90%) encodes about 800 amino acids with the RhoGEF domain, the part that switches on Rho GTPases, plus the SH3 domain and two disordered regions.","so-what":"In hESC most ARHGEF19 protein would lack its catalytic domain, while in iPS cells it is complete: a clear, testable difference, if the iPS switch survives the replicate question.","figure":"project-log/figures/out/arhgef19_switchplot.png","static":"project-log/figures/out/arhgef19_switchplot.pdf","fig-script":"project-log/figures/scripts/arhgef19_switchplot.R","script":["analysis/run_isoform_switch.R"],"data":["results/switchList.rds","results/isoform_structures.tsv"],"key":["Protein length=about 280 → 800 amino acids","Domain gained=RhoGEF (aa 380–559)","Disordered regions gained=2"]},
 {"type":"correction","thread":"conseq","ts":"__D8__T16:00:00+01:00","title":"iPS cells barely express ARHGEF19, so \"iPS cells make the complete protein\" was too strong","corrects":"@r-arhgef19","why":"The expression panels of the switchPlot in R4 show it; we had read only the isoform structures.","what":"ARHGEF19 expression is about 11,600 in hESC but about 61 in iPS cells, 190 times lower (normalised expression). The 90% share of the full-length isoform in iPS cells rests on very few reads. The difference between the two isoforms stands; how much of either protein iPS cells make is unclear.","data":["results/isoform_switches.tsv"]},
 {"type":"progress","thread":"pipeline","ts":"__D8__T11:00:00+01:00","title":"Side project started: the workflow as a pipeline for the lab's own samples","why":"Our own RNA-seq (4 replicates per group) is due next month.","what":"Wrapped the R script so it takes a sample sheet and a folder of Salmon results. On the example data it reproduces the same 5 genes."},
 {"type":"plan","thread":"pipeline","ts":"__D7__T10:00:00+01:00","title":"Add a replicate check to the pipeline: warn when two replicates agree with r > 0.99","why":"Lesson from the iPS samples: catch duplicated libraries before the switch test, not after."},
 {"type":"followup","thread":"switch","ts":"__D5__T15:00:00+01:00","title":"Find out how the example iPS samples were made: separate cultures, or one library split in two?","related":"@q-ips","why":"Settles whether the iPS switches can be trusted."},
 {"type":"plan","thread":"switch","ts":"__D4__T11:00:00+01:00","title":"Rerun the workflow on the lab's own samples when sequencing is back","why":"Four replicates per group will give the test real power, and real replicates."},
 {"type":"session","ts":"__D3__T18:00:00+01:00","title":"__L3__: consequences done; pipeline started","body":"Protein annotations came from the example data while the SignalP licence is pending. In 4 of 5 switching genes the iPS isoform changes the protein; in ARHGEF19 only the iPS isoform has the RhoGEF domain, but iPS cells barely express the gene. A pipeline for our own samples is started, with a replicate check as the first addition. Open: Sam's call on the iPS switches."}]
EOF
python3 - <<'PY'
p = "project-log/project.yaml"; t = open(p).read()
t = t.replace("overview:\n  summary: []\n  tiles: []", """overview:
  figure: R2
  summary:
    - - Isoform-switch pilot on IsoformSwitchAnalyzeR's example data
      - "6 samples: fibroblasts, [[iPS cell|iPS cells]] and [[hESC]]"
      - Switch test and protein consequences done
    - - 5 genes switch, all involving iPS cells
      - "iPS replicates are near-identical (r = 1.00)"
      - A second test (satuRn) finds no switches
    - - "Needs Sam: treat the iPS switches as leads only?"
      - Pipeline for our own samples, with a replicate check
  tiles:
    - value: "5"
      label: genes switch isoforms, all involving iPS cells
      link: R1
    - value: "r = 1.00"
      label: agreement of the two iPS replicates (others 0.87–0.89)
      link: R2
    - value: "4 / 5"
      label: switching genes where the iPS isoform changes the protein
      link: R3
    - value: "1"
      label: decision waiting for Sam
      link: tab:loops""")
open(p, "w").write(t)
PY
git add -A && git commit -qm "Log week 3 and refresh the overview"
build
echo "demo ready: $DIR/project-log/report/project-log.html"
