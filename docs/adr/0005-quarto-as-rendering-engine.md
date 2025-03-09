# 0005 - Use Quarto

- Status: Accepted
- Date: 2025-03-01
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

beam needs one rendering toolchain for the docs site, vignettes, API reference, and manuscript.

## Decision

Use Quarto. quartodoc for the Python API reference, pkgdown for the R one.

## Consequences

- One toolchain, not four.
- Build machine needs Pandoc and LaTeX.

## Alternatives considered

- Sphinx, mkdocs, rmarkdown, LaTeX: four toolchains.
- Jupyter Book: weaker R support.
- rmarkdown plus pkgdown: R-first, contradicts ADR 0002.

## References

- https://quarto.org
- https://machow.github.io/quartodoc/
- https://pkgdown.r-lib.org
