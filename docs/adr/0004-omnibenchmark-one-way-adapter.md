# 0004 - omnibenchmark integration is a one-way adapter

- Status: Accepted
- Date: 2025-03-01
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

beam grew out of omnibenchmark work. Coupling beam tightly to omnibenchmark would shrink the audience.

## Decision

beam accepts any tool x metric matrix as input (CSV, parquet, FunkyHeatmap, omnibenchmark output, raw pandas DataFrame). omnibenchmark integration is a one-way adapter in beam.io. omnibenchmark is not a runtime dependency.

## Consequences

- beam works on any benchmark output, not just omnibenchmark's.
- We give up the automatic provenance threading that omnibenchmark would have provided; the beam manifest reintroduces it.
- We have to maintain adapters for several input formats.

## Alternatives considered

- omnibenchmark as a hard dependency: too restrictive for the audience.
- Shared types library across the two projects: possible later if both want it.

## References

- https://github.com/omnibenchmark/omnibenchmark
