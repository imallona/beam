# beam manuscript source

Manuscript in `manuscript.qmd`. Figures and tables come from the vignettes in `../../examples/`. Findings come from `../findings/`.

## Build

```
quarto render manuscript.qmd
```

## Conventions

- Do not paste figures here. Vignettes generate them; the manuscript pulls them in. `figures/` is .gitignored.
- Cite findings by slug, ADRs by number. Do not restate.
- Bibliography in `_bibliography.bib`.
- One commit per coherent edit.
