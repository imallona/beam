# 0006 - Diataxis layout for the docs site

- Status: Accepted
- Date: 2025-03-01
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

Without a structure, docs drift: tutorials pick up reference cruft, reference pages turn into how-tos.

## Decision

Use Diataxis. Four top-level folders: tutorials, how-to, reference, explanations. Each document declares its mode in the header and does not mix modes.

## Consequences

- Readers find what they need faster.
- Contributors have a template to follow.
- Some content sits between modes; conventions needed for those edges.

## Alternatives considered

- Flat docs/: outgrown quickly.
- Single-narrative book: audiences are too varied.
- Wiki: no quality bar.

## References

- https://diataxis.fr
