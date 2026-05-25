# Quickstart

beam ranks the tools in a benchmark from a tool-by-metric table of scores. It reads the metric meaning (polarity, scale, normalization) from metric cards, normalizes the scores, combines them into one composite score per tool, and reports a ranking with a sensitivity analysis.

This tutorial goes from a small CSV to an HTML report, first in Python and then from the command line. Copy each block as you go and run it.

## What you need

Install beam and work in an empty directory. beam is not on PyPI yet, so install it from a checkout of the repository.

```
pip install /path/to/beam
```

## Step 1: write a small scores file

beam reads a wide CSV. The first column holds the tool name. Every other column header is a metric id that must resolve to a metric card. Here we use three cards that ship with beam: ari (adjusted Rand index, higher is better), nmi (normalized mutual information, higher is better) and runtime (seconds, lower is better). beam reads the polarity from the cards, so you do not flip the runtime column yourself.

Save this as scores.csv:

```
tool,ari,nmi,runtime
seurat,0.81,0.78,42.0
sc3,0.74,0.71,310.5
monocle,0.69,0.66,88.0
```

## Step 2: rank and report in five lines

```python
import beam

scores = beam.load_scores("scores.csv")
result = beam.rank(scores)
beam.report(result, "report.html")
```

`beam.load_scores` reads the CSV and checks every metric id against the registry. An unknown id raises `UnknownMetricError`, so a typo in a header fails early rather than ranking on the wrong column. `beam.rank` normalizes each column per its card, applies equal weights and the SAW aggregation by default, runs the default sensitivity analysis, and builds a run manifest. `beam.report` writes one self-contained HTML file with the figures embedded, so report.html opens in a browser with no other files.

## Step 3: read the RunResult

`beam.rank` returns a `RunResult`. The fields you reach for most often:

```python
result.top_tool        # name of the tool ranked first
result.tool_names      # the tools, in input order
result.metric_ids      # the metrics, in input order
result.result.ranks    # 1-based rank per tool, in input order
result.result.composite  # composite score per tool
result.result.normalized # the normalized tool-by-metric matrix
```

`result.result` is the MCDA result: it carries the ranks, the composite scores, the normalized matrix, the weighting vector and the method name. The sensitivity reports live on `result.smaa`, `result.leave_one_out` and `result.perturbation`; they are `None` when you pass `sensitivity=False`. `result.manifest` is a dictionary recording the input, the metrics, the parameters and the normalization. That record is what lets a reader reproduce the run.

You can change the weighting and the aggregation through arguments. For example, entropy weights with the TOPSIS aggregation:

```python
result = beam.rank(scores, weights="entropy", method="topsis")
```

Weights accept equal, entropy, std, critic, merec, or an explicit array. Methods accept saw, topsis, vikor, promethee_ii and comet.

## Step 4: the same run from the command line

The CLI does the same thing without writing Python. This ranks the file, writes the report, and prints a small JSON run record to stdout:

```
beam rank scores.csv --report report.html
```

To save the run record to a file and add the manifest:

```
beam rank scores.csv --report report.html --out result.json --manifest manifest.json
```

The run record on `--out` captures the input path and hash, the parameters and the ranking. You can re-render the report later from that record alone:

```
beam report result.json --out report.html
```

The CLI writes errors to stderr and exits 0 on success or 2 on a usage or validation error, so a script can branch on it. You can also check a file before ranking it:

```
beam validate scores.csv --metrics ari,nmi,runtime
```

## Where to go next

To drive a whole run from one declarative file (so a reviewer reruns it with a single command), see the how-to: [Run a benchmark from a beam.yaml file](../how-to/run-from-beam-yaml.md).

For the concepts behind the steps above, see the explanations: [normalization and scales](../explanations/normalization-and-scales.md), [weighting schemes](../explanations/weighting-schemes.md) and [aggregation methods](../explanations/aggregation-methods.md).
