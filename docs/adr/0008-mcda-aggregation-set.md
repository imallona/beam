# 0008 - Delegate SAW, TOPSIS, VIKOR, PROMETHEE II and COMET to pymcdm at runtime

- Status: Accepted
- Date: 2026-05-24
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

The decision module (PLAN Section 3, step 4) commits to a set of aggregation methods. The proposal lists weighted sum, TOPSIS and PROMETHEE; the existing notebook adds VIKOR and COMET. beam needs these as packaged functions with one uniform contract so the pipeline and the sensitivity analysis can call any of them through the same interface. beam first implemented these methods natively and regression-tested them against pymcdm as a test-only oracle. That parity has been validated: on the real Duo data, native beam and pymcdm produce identical rankings across all 16 weighting-by-method configurations. Maintaining a second implementation of well-known algorithms is avoidable cost, so the question is whether to keep the native code or to delegate to the maintained library.

## Decision

Delegate SAW, TOPSIS, VIKOR, PROMETHEE II and COMET to pymcdm at runtime. pymcdm becomes a core runtime dependency. beam keeps the public function names and the shared contract: input is a normalized matrix in [0, 1] oriented higher is better plus a non-negative weight vector, output is a per-tool preference score where higher is better. Each beam function calls pymcdm with an identity normalization so pymcdm runs on beam's already normalized matrix, and with all criteria typed as profit because the matrix is oriented higher is better.

beam keeps its own objective weights (equal, entropy, standard deviation, CRITIC, MEREC) and AHP. pymcdm's weight functions sum-normalize internally and reject zeros, but beam's min-max normalization routinely maps the worst tool to zero, and AHP is not in pymcdm. beam also keeps its normalization, validation, SMAA, perturbation, sensitivity and cross-dataset layers.

## Consequences

- beam depends on pymcdm at runtime. It is a core dependency, imported by src/beam, not just by tests. See the update on ADR 0002.
- The five methods keep one contract, so the pipeline, SMAA, and the weight-perturbation analysis treat them interchangeably. The facade dispatches by function name, so it needs no change.
- VIKOR is canonically lower is better. beam returns -Q to meet the higher-is-better contract; the convention is documented in the function and in docs/explanations/aggregation-methods.md.
- PROMETHEE II uses the Type I (usual) preference function as the default, since it needs no thresholds. The other five preference functions are a documented extension point, deferred because they need per-metric indifference and preference thresholds the pipeline does not yet carry.
- COMET is supplied with the same characteristic values beam used before (the endpoints 0 and 1 per metric by default) and a weighted-sum expert, passed to pymcdm through a FunctionExpert. The automated weighted-sum expert is documented in docs/explanations/comet.md.
- pymcdm returns a not-a-number on degenerate inputs, for example a single tool, rows identical on every metric, or a characteristic-object set that collapses to one preference group. beam intercepts those cases and returns its previous convention (0.5 for TOPSIS and COMET, a constant tie for VIKOR), so the public behavior is unchanged. VIKOR also drops constant columns before the call because pymcdm rejects them.
- beam no longer carries a second implementation of these algorithms, which removes a maintenance burden and the risk of drift from the reference behavior.

## Alternatives considered

- Keep the native implementations: rejected because they duplicate a maintained library and must be kept correct by hand. The pymcdm regression tests already showed the two agree, so the native code added cost without added value.
- Delegate the weight functions too: rejected because pymcdm's weight functions sum-normalize and reject zeros, which beam's normalization produces, and AHP is absent from pymcdm.
- Drop a method to reduce surface: rejected because the pipeline and sensitivity analysis rely on the full set.

## References

- docs/explanations/aggregation-methods.md
- docs/explanations/comet.md
- Hwang and Yoon, Multiple Attribute Decision Making (1981), TOPSIS.
- Opricovic and Tzeng, European Journal of Operational Research (2004), VIKOR.
- Brans and Vincke, Management Science (1985), PROMETHEE.
- Salabun, Journal of Multi-Criteria Decision Analysis (2015), COMET.
- pymcdm: https://github.com/kotbaton/pymcdm
