# Contributing to beam

This file covers what a pull request needs, how to add a metric card, the licenses, and the conduct expected.

## Quick start

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

If you change a metric card or the schema, validate from R too (or rely on CI to do it for you):

```
Rscript tests/validate_cards.R
```

The R validation needs the CRAN packages `jsonvalidate`, `yaml` and `jsonlite`. The schema is JSON Schema (draft 2020-12), so any language with a validator can read it; open an issue if yours cannot.

## Pull requests

A pull request that changes behaviour has:

- the code change, with type hints (Python) or roxygen2 documentation (R)
- a unit test
- an updated docstring on every public function it touches
- a CHANGELOG entry (Keep a Changelog format)

One commit per change; unrelated edits go in separate commits.

## Adding a metric card

Cards live under `src/beam/metrics/<id>/v<version>.yaml`. The directory name must equal the `id` field and the file name stem the `version` field; CI checks both. The cards are part of the package, so an installed wheel includes them.

The schema is at `src/beam/schema/metric_card.schema.json`. Every required field must be present. A minimum-effort card needs `id`, `version`, `name`, `description`, `metric_kind`, `measurand`, `task`, `requires_ground_truth`, `output`, `semantics`, `comparability`, `implementations`, `examples`, and `provenance`.

`src/beam/metrics/ari/v1.yaml` is an example of a derived metric and `src/beam/metrics/runtime/v1.yaml` of a measured one.

## Licensing

- Code (everything outside `src/beam/metrics/`): GPL-3.0-or-later. See `LICENSE`.
- Metric cards (`src/beam/metrics/`): CC-BY-4.0. See `src/beam/metrics/LICENSE.md`. By contributing a card you agree to this licensing.

## Conventions

- Documentation uses Quarto. Vignettes live in `examples/` and are rendered as part of CI.
- `docs/` follows the Diataxis split: tutorials, how-to, reference, explanations. One mode per document.
- Plain English; define a term before using it.

## Community

Contributors and users are welcome regardless of sex, gender identity, age, ethnicity, nationality, religion, disability, sexual orientation, career stage, native language, or any other attribute. Be respectful.
