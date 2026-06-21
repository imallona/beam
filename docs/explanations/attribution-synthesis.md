# Attribution synthesis

A benchmark ranking moves for three reasons. The analyst's choices move it: the weighting and the aggregation rule. The dataset moves it: a method that ranks first on one dataset trails on another. The benchmarker moves it: two benchmarks of the same task, each with its own pipeline, rank shared methods differently. beam already measures these one at a time. `rank_sensitivity` splits a ranking between the choices and the dataset. `source_variance_decomposition` splits a method's standing between the benchmark and the method. The two use different scales, so they cannot be compared directly.

`attribution_synthesis` puts them on one scale. For each setting it gives three shares, for analyst choice, dataset and benchmarker, that sum to one. Compared across settings, from one benchmark to a contrast where the datasets are held fixed, the shares show how the source of the movement changes as the dataset contribution is removed.

## The budget

No single decomposition covers all three sources, so each setting uses the decomposition available to it. The rules are fixed.

Within one benchmark, from a `RankSensitivityReport` over a tool by dataset by metric tensor: analyst choice is the weighting plus aggregation share, the dataset share is the dataset main effect, and benchmarker is zero because one benchmark does the scoring. The interaction share is split between analyst choice and dataset in proportion to the main effect each already carries.

Across pooled benchmarks, from a `SourceVarianceReport`: benchmarker is the method-by-benchmark component, the part of a method's standing that changes between benchmarks. The dataset share is every other component (the between-benchmark and within-benchmark-dataset terms and the residual). The pooled scores are mean ranks with no metric axis, so analyst choice cannot be measured here and is set to zero unless supplied; when supplied, the rest of the budget is split between benchmarker and dataset in the ratio the model gives.

On a same-data contrast, where two or more pipelines score the methods on the same datasets: the dataset share is zero by construction. Each method's rank is centred on its mean across the pipelines, removing the part they agree on. What remains is split into a pipeline offset (benchmarker) and the method-by-pipeline reordering (analyst choice). When the pipelines give the same order there is nothing to attribute and the shares are undefined.

## The three settings

The settings run from one where the dataset drives the ranking to one where the datasets are held fixed. Within one benchmark the dataset carries most of the budget, because a method's rank changes with the dataset more than with the weighting or the aggregation. Pooling benchmarks adds the benchmarker, the method-by-benchmark term. A same-data contrast holds the datasets fixed, so what is left between two pipelines on the same studies is the analysts' choices. Across the three, the dataset share falls and the analyst-choice and benchmarker shares rise.

## Limitations

The shares describe the input; they are not estimates with confidence intervals. The pooled setting spans only a few methods and benchmarks, so its shares are coarse. The same-data contrast assigns the cross-pipeline reordering to analyst choice but cannot say which choice (weighting, aggregation, normalization) caused it, because it has only the final per-method ranks. A small benchmark gives a coarse result.
