# beam documentation

This directory holds the docs site, the architectural decision records, the findings log, and the manuscript.

## Layout

- tutorials/      Diataxis tutorials.
- how-to/         Task-oriented recipes.
- reference/      Auto-generated API reference. Do not hand-edit.
- explanations/   Conceptual essays.
- adr/            Architecture decision records.
- findings/       Findings log.
- paper/          Manuscript source.

## Build

```
quarto render
```

Manuscript on its own:

```
quarto render docs/paper/manuscript.qmd
```

## Conventions

- Diataxis modes (tutorials, how-to, reference, explanations). Do not mix in one document.
- Number ADRs in order. Status flows Proposed, Accepted, then Deprecated or Superseded. Never delete a superseded ADR; change status and add a forward pointer.
- Number findings in order. Each one cites a commit hash and a run manifest.
- The manuscript cites ADRs by number and findings by slug. It does not restate empirical claims.
