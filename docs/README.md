# beam documentation

This directory holds the docs site and the architectural decision records.

## Layout

- tutorials/      Diataxis tutorials.
- how-to/         Task-oriented recipes.
- reference/      Auto-generated API reference. Do not hand-edit.
- explanations/   Conceptual essays.
- adr/            Architecture decision records.

## Build

```
quarto render
```

## Conventions

- Diataxis modes (tutorials, how-to, reference, explanations). Do not mix in one document.
- Number ADRs in order. Status flows Proposed, Accepted, then Deprecated or Superseded. Never delete a superseded ADR; change status and add a forward pointer.
