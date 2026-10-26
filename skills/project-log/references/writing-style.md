# Writing style for log entries

Readers: the supervisor (two minutes, on the Overview tab) and the user later (detail, months from now). Both should understand an entry without having been in the session.

## The entry pattern

- **Title:** what happened, as a plain statement with the key fact in it. "2 of the first 3 batch jobs failed", not "Batch issue". For results, the finding itself: "The new normalisation cuts the batch effect by a third".
- **Why:** one or two sentences on why this step was taken or why it mattered.
- **What we did:** one short paragraph covering what was done, the number that matters, and what changed as a result.
- **So what** (results only): one sentence on what the reader should take from it, with a comparison the reader can feel ("1 in 5", "far above the 1% reported").

## Plain language

- Short sentences in the active voice: "We kept it but reviewed it", not "It was decided that it would be retained".
- Wrap a technical term in `[[ ]]` the first time it appears in an entry (not every time), and make sure a `term` entry exists. Define it in one or two sentences a new lab member would understand, with no other undefined jargon inside.
- To show a different word form, use `[[term|shown text]]`, e.g. `[[decoy|decoys]]`, `[[PSM|PSMs]]`. Add common inflections and spellings to the term entry as `--alias` ("decoys", "false discovery rate") so `[[decoys]]` also works.
- Spell out abbreviations the first time they appear in an entry, even when a term entry exists.
- Use real numbers with their units and what they are relative to: "+1,663 genes detected per sample", not "a big gain".
- Say what is uncertain. "Leading explanation, not confirmed" is better than a confident guess. Never present a guess as a finding.
- Name people the way the project does (e.g. "Sam agreed").
- No hype words (significant, robust, novel, crucial) unless a test backs them.

## Detours and dead ends are first-class

Record approaches that were tried and dropped, wrong assumptions, and redone work. Each detour gets a verdict:

| Verdict | Use when |
|---|---|
| archived | dropped, and not coming back |
| pivoted | dropped in favour of a different approach (say which) |
| iterate | partly worked; trying again with a change |
| kept / kept-after-review | an unplanned path turned out fine (after checking) |
| corrected | an earlier claim was wrong and has been fixed |
| abandoned | stopped without a replacement (e.g. blocked upstream, no longer needed) |
| open | not resolved yet |

## Corrections

- If the wrong claim has an entry, point to it with `--corrects`. The page puts a "Corrected later" banner on it.
- If the wrong claim never got an entry (it only lived in old notes) but the corrected fact did, write the correction with `--related` to that entry, and say in the body what the old claim was.
- Wording-only fixes (the number was right, but the description was misleading) are still corrections. Say "wording" in the title.

## Paper titles

Use the paper's main finding as the title ("Mixing in known-negative controls exposes over-optimistic error rates"). If the project only cites the paper and never says what it found, use what the project used it for ("Source of the reference dataset"). Never summarise a paper from memory.

## Overview summary (project.yaml)

Three short paragraphs, rewritten before each build. The page shows them side by side under the headings "Where we are", "What we learned" and "What's next", so each one must make sense on its own (about 40–60 words):
1. What the project does and where it stands, with the most important result so far.
2. What was learned recently, with one or two key numbers.
3. What is open or next, and anything that needs a decision.

To use other headings, write an item as `{label: ..., text: ...}` instead of a plain string.

## Session digest

A title like "16 Oct: v2 approved, first blocker", plus one paragraph of 3–5 sentences: what got done, what was found, what is blocked, and what comes next.
