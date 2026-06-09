## Submission

New submission. rbeam 0.2.0 is the R interface to the beam Python package.

## R CMD check results

0 errors | 0 warnings | 1 note

The note is the standard new-submission note:

```
* checking CRAN incoming feasibility ... NOTE
  Maintainer: 'Izaskun Mallona <izaskun.mallona.work@gmail.com>'
  New submission
```

## Test environments

- Local: Ubuntu, R 4.5.3, `R CMD check --as-cran`.
- CI (`.github/workflows/r-ci.yml`): Ubuntu, macOS and Windows, R release and devel.

## Python dependency

rbeam is a thin interface to the beam Python package, declared in
`SystemRequirements: Python (>= 3.12)` and called through reticulate. The package
degrades gracefully when Python or beam is absent: examples, tests and vignettes
check `reticulate::py_module_available()` and skip when it is not available, so
`R CMD check` passes with no Python on the build machine. The helper
`install_beam_python()` runs only when the user calls it; nothing installs
software or writes outside the session on load or during checks.
