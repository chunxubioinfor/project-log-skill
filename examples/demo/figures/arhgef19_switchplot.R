# R4: IsoformSwitchAnalyzeR's own switchPlot() of ARHGEF19, hESC vs iPS: isoform structures with protein
# domains, gene and isoform expression, and isoform usage.
# Reads results/switchList.rds, writes project-log/figures/out/arhgef19_switchplot.{png,pdf}.
# Run from the repo root:  Rscript project-log/figures/scripts/arhgef19_switchplot.R
suppressMessages(library(IsoformSwitchAnalyzeR))
options(warn = -1)
out <- file.path("project-log", "figures", "out")
name <- "arhgef19_switchplot"
if (file.exists(file.path(out, paste0(name, ".png")))) stop("exists; a logged figure never changes (write a new output name)")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
sl <- readRDS(file.path("results", "switchList.rds"))
draw <- function() switchPlot(sl, gene = "ARHGEF19", condition1 = "hESC", condition2 = "iPS", plotTopology = FALSE)
png(file.path(out, paste0(name, ".png")), width = 1500, height = 900, res = 150); draw(); invisible(dev.off())
pdf(file.path(out, paste0(name, ".pdf")), width = 10, height = 6); draw(); invisible(dev.off())
cat("wrote", file.path(out, paste0(name, ".png")), "\n")
