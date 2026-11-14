# Isoform switch analysis of the IsoformSwitchAnalyzeR example data (Salmon, 6 samples), following the vignette.
# Writes tab-separated results to the folder given as the first argument (default: results/).
#   Rscript run_isoform_switch.R results/
# Tested with IsoformSwitchAnalyzeR 2.11.2 on R 4.6.
suppressMessages(library(IsoformSwitchAnalyzeR))
options(warn = -1)  # silence dplyr deprecation warnings raised inside the package
args <- commandArgs(trailingOnly = TRUE)
out <- if (length(args)) args[1] else "results"
dir.create(out, showWarnings = FALSE, recursive = TRUE)
ext <- function(f) system.file("extdata", f, package = "IsoformSwitchAnalyzeR")
w <- function(d, f) write.table(d, file.path(out, f), sep = "\t", quote = FALSE, row.names = FALSE)

# 1. import Salmon quantifications, annotation and isoform sequences
q <- importIsoformExpression(parentDir = system.file("extdata", package = "IsoformSwitchAnalyzeR"), showProgress = FALSE)
design <- data.frame(sampleID = colnames(q$abundance)[-1], condition = sub("_.*", "", colnames(q$abundance)[-1]))
sl <- importRdata(isoformCountMatrix = q$counts, isoformRepExpression = q$abundance, designMatrix = design,
                  isoformExonAnnoation = ext("example.gtf.gz"), isoformNtFasta = ext("example_isoform_nt.fasta.gz"),
                  fixStringTieAnnotationProblem = TRUE, showProgress = FALSE)
w(data.frame(sample = colnames(q$counts)[-1], condition = design$condition,
             reads_assigned = round(colSums(q$counts[, -1])), isoforms_over_1_tpm = colSums(q$abundance[, -1] > 1)),
  "library_sizes.tsv")
n_import <- c(length(unique(sl$isoformFeatures$isoform_id)), length(unique(sl$isoformFeatures$gene_id)))

# 2. filter; check how well replicates agree; test for isoform switches (all three pairwise comparisons)
sl <- preFilter(sl, removeSingleIsoformGenes = TRUE, quiet = TRUE)   # package defaults for count and IF cutoffs
n_filtered <- c(length(unique(sl$isoformFeatures$isoform_id)), length(unique(sl$isoformFeatures$gene_id)))
w(data.frame(step = c("imported", "after filtering"), isoforms = c(n_import[1], n_filtered[1]),
             genes = c(n_import[2], n_filtered[2])), "filtering.tsv")
ifm <- as.matrix(data.frame(sl$isoformRepIF[, -1], row.names = sl$isoformRepIF$isoform_id, check.names = FALSE))
ifm <- ifm[complete.cases(ifm), ]
w(data.frame(isoform_id = rownames(ifm), ifm, check.names = FALSE), "isoform_fraction_per_sample.tsv")
w(do.call(rbind, lapply(unique(design$condition), function(cnd) {
  s <- design$sampleID[design$condition == cnd]
  data.frame(condition = cnd, n_isoforms = nrow(ifm), pearson_r = round(cor(ifm[, s[1]], ifm[, s[2]]), 4),
             median_abs_diff_IF = round(median(abs(ifm[, s[1]] - ifm[, s[2]])), 4))
})), "replicate_agreement.tsv")

saturn <- isoformSwitchTestSatuRn(sl, reduceToSwitchingGenes = FALSE, quiet = TRUE)
sf <- saturn$isoformFeatures
w(data.frame(test = "satuRn", min_q_value = signif(min(sf$isoform_switch_q_value, na.rm = TRUE), 3),
             switching_isoforms = sum(sf$isoform_switch_q_value < 0.05 & abs(sf$dIF) > 0.1, na.rm = TRUE)), "saturn_check.tsv")
sl <- isoformSwitchTestDEXSeq(sl, reduceToSwitchingGenes = FALSE, showProgress = FALSE, quiet = TRUE)
w(extractSwitchSummary(sl, dIFcutoff = 0.1, alpha = 0.05), "switch_summary.tsv")

# 3. what the switches do: ORFs, coding potential, protein domains, signal peptides, disordered regions
sl <- extractSequence(sl, writeToFile = FALSE, quiet = TRUE)   # needed before the consequence analysis
sl <- analyzeCPC2(sl, pathToCPC2resultFile = ext("cpc2_result.txt"), removeNoncodinORFs = TRUE, quiet = TRUE)
sl <- analyzePFAM(sl, pathToPFAMresultFile = ext("pfam_results.txt"), showProgress = FALSE, quiet = TRUE)
sl <- analyzeSignalP(sl, pathToSignalPresultFile = ext("signalP_results.txt"), quiet = TRUE)
sl <- analyzeIUPred2A(sl, pathToIUPred2AresultFile = ext("iupred2a_result.txt.gz"), showProgress = FALSE, quiet = TRUE)
sl <- analyzeAlternativeSplicing(sl, quiet = TRUE)
sl <- analyzeSwitchConsequences(sl, consequencesToAnalyze = c("intron_retention", "coding_potential", "ORF_seq_similarity",
                                "NMD_status", "domains_identified", "IDR_identified", "signal_peptide_identified"),
                                dIFcutoff = 0.1, showProgress = FALSE, quiet = TRUE)

f <- sl$isoformFeatures
keep <- c("isoform_id", "gene_id", "gene_name", "condition_1", "condition_2", "gene_value_1", "gene_value_2",
          "IF1", "IF2", "dIF", "isoform_switch_q_value", "codingPotential")
w(f[, keep], "isoform_switches.tsv")
sc <- sl$switchConsequence
w(unique(sc[!is.na(sc$isoformsDifferent) & sc$isoformsDifferent,
            c("gene_name", "condition_1", "condition_2", "featureCompared", "switchConsequence")]), "switch_consequences.tsv")
w(extractTopSwitches(sl, filterForConsequences = TRUE, n = 20, sortByQvals = TRUE), "top_switches.tsv")

# 4. structures of the switching isoforms: exons, ORF, protein domains and disordered regions (genome and protein coordinates)
sw <- unique(f$isoform_id[!is.na(f$isoform_switch_q_value) & f$isoform_switch_q_value < 0.05 & abs(f$dIF) > 0.1])
gene <- setNames(f$gene_name, f$isoform_id)
ex <- as.data.frame(sl$exons); ex <- ex[ex$isoform_id %in% sw, ]
o <- sl$orfAnalysis; o <- o[o$isoform_id %in% sw & !is.na(o$orfStartGenomic), ]
aa_len <- setNames(Biostrings::width(sl$aaSequence), names(sl$aaSequence))
d <- sl$domainAnalysis; d <- d[d$isoform_id %in% sw, ]
idr <- sl$idrAnalysis; idr <- idr[idr$isoform_id %in% sw, ]
feat <- function(iso, type, name, a, b, aa1, aa2, strand = NA)
  data.frame(isoform_id = iso, gene_name = gene[iso], feature = type, name = name, start = pmin(a, b), end = pmax(a, b),
             strand = strand, aa_start = aa1, aa_end = aa2)
w(rbind(feat(ex$isoform_id, "exon", "", ex$start, ex$end, NA, NA, as.character(ex$strand)),
        feat(o$isoform_id, "orf", "", o$orfStartGenomic, o$orfEndGenomic, 1, aa_len[o$isoform_id]),
        feat(d$isoform_id, "domain", d$hmm_name, d$pfamStartGenomic, d$pfamEndGenomic, d$orf_aa_start, d$orf_aa_end),
        feat(idr$isoform_id, "idr", idr$idr_type, idr$idrStartGenomic, idr$idrEndGenomic, idr$orf_aa_start, idr$orf_aa_end)),
  "isoform_structures.tsv")
saveRDS(sl, file.path(out, "switchList.rds"))   # the full analysis, for plots such as switchPlot()
cat("done:", out, "\n")
