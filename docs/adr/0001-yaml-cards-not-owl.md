# 0001 - YAML metric cards with JSON Schema, defer OWL

- Status: Accepted
- Date: 2025-03-01
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

beam needs a machine-readable description per metric: polarity, scale type, range, allowed transformations, ground-truth dependence, implementations, examples.

Two options. A formal OWL or SKOS ontology aligned with BFO, OBI, STATO. Or JSON Schema plus one YAML file per metric.

## Decision

JSON Schema plus YAML cards. Cards under metrics/. Schema in schema/metric_card.schema.json. An OWL or SKOS export can come in Phase 7 if downstream tools ask for one.

## Consequences

- Authoring takes minutes in a text editor.
- Validation runs anywhere JSON Schema runs (Python, R, JS).
- No reasoner, no SPARQL, no subsumption inference.
- Cross-ontology alignment goes in a per-card `mappings:` block when we need it.

## Alternatives considered

- Full OWL-first: too heavy a toolchain for the audience, and we would over-model categories before any real cards exist.
- Bioschemas profile only: does not cover MCDA-relevant fields like polarity or allowed transformations.
- A custom DSL: no reason to reinvent JSON Schema.

## References

- https://github.com/huggingface/evaluate
- https://arxiv.org/abs/2204.01075
- https://arxiv.org/abs/1810.03993
