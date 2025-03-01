# 0000 - Template for findings entries

- Status: Template
- Date: YYYY-MM-DD
- Dataset: -
- Authors: -
- Commit: -
- Manifest: -

## Observation

What did we see? One to three sentences. Quantitative if possible. Cite the exact numbers. Do not paraphrase.

## Method

How did we measure it? Which beam pipeline, which metrics, which weighting, which sensitivity setup. One paragraph. Refer to the notebook or script that ran it.

## Implications

What does this mean for beam, for the case study, or for the field? Two to four sentences. Be precise about scope. Do not overclaim.

## Reproducibility

- Notebook or script: examples/<path>.qmd
- Run manifest: <path or hash>
- Commit: <git sha>
- Software environment: <pinned versions or container image>

## Related

- ADRs that informed the analysis: [link to ADR]
- Findings this builds on or contradicts: [link to other finding]
- External references: [DOI or URL]
