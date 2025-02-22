# Contributing to beam

Thanks for considering a contribution. This file is the short version of the
PR contract; the long version lives in PLAN.md Section 8.

## Quick start

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

If you change a metric card or the schema, validate from R too (or rely on
CI to do it for you):

```
Rscript tests/validate_cards.R
```

R-side validation needs the CRAN packages `jsonvalidate`, `yaml`, and
`jsonlite`. The schema is plain JSON Schema (draft 2020-12) and is meant to
be readable from any language; if your language is not covered, please open
an issue.

## PR contract

Every non-trivial PR ships:

- code change with type hints (Python) or roxygen2 docstrings (R)
- a unit test
- updated docstring on every public function the PR touches
- an ADR in `docs/adr/` if the change reflects a design decision
- a findings entry in `docs/findings/` if the change produces a new
  empirical claim (e.g. "method X is consistently ranked first under
  weighting Y on dataset Z")
- a CHANGELOG entry (Keep a Changelog format)

Commits do not bundle unrelated edits. One commit = one coherent change.

## Adding a metric card

Cards live under `metrics/<id>/v<version>.yaml`. The directory name must
match the `id` field; the filename stem must match the `version` field.
This is enforced in CI.

The schema is at `schema/metric_card.schema.json`. Every required field
must be present. A minimum-effort card needs `id`, `version`, `name`,
`description`, `metric_kind`, `measurand`, `task`,
`requires_ground_truth`, `output`, `semantics`, `comparability`,
`implementations`, `examples`, and `provenance`.

See `metrics/ari/v1.yaml` and `metrics/runtime/v1.yaml` for two worked
examples covering the derived and the measured `metric_kind` respectively.

## Licensing

- Code (everything outside `metrics/`): GPL-3.0-or-later. See `LICENSE`.
- Metric cards (`metrics/`): CC-BY-4.0. See `metrics/LICENSE.md`. By
  contributing a card you agree to this licensing.

## ADR template

See `docs/adr/0000-template.md`. Number sequentially. Start in status
"Proposed"; move to "Accepted" after review. Never edit an accepted ADR
silently; if it changes, supersede it with a new one.

## Findings template

See `docs/findings/0000-template.md`. Include a commit hash and a run
manifest path so the result is reproducible.

## Conventions

- Documentation uses Quarto. Vignettes live in `examples/` and are
  rendered as part of CI.
- Diataxis split for `docs/`: tutorials, how-to, reference, explanations.
  Do not mix modes within one document.
- Plain English in prose; no jargon without an explicit definition.
