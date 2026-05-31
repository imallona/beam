"""Command-line interface for beam.

Plain, unix-style: lowercase output, no decoration, errors to stderr, and exit
codes a script can branch on (0 ok, 2 on a usage or validation error). Built on
argparse so the CLI adds no dependency.

Subcommands:

    beam validate scores.csv [--metrics ari,runtime] [--method saw]
    beam rank scores.csv [--weights entropy] [--method topsis] [--out result.json]
                         [--report report.html] [--manifest manifest.json]
    beam report result.json --out report.html
    beam metric show ari
    beam heterogeneity scores.csv --model bradley-terry-tree --features features.csv
    beam run beam.yaml

``beam rank`` writes a small run record (the input path and hash, the
parameters, the ranking, and the manifest). ``beam report`` reads that record,
reloads the scores, re-runs with the recorded parameters (deterministic through
the recorded seed), and renders the HTML report. ``beam heterogeneity`` fits one
of the method-dataset heterogeneity models on a long-format score file and
writes the report as JSON; it needs the R toolchain (see envs/heterogeneity.yml)
and exits with an error naming the missing package when R is absent. ``beam
metric run`` is not yet exposed (the metric-execution command).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .api import rank
from .cards import Registry
from .config import run_config
from .io import load_scores
from .manifest import write_manifest
from .mcda import registry_context
from .reporting import write_report
from .reporting.narrative import recommendation

_EXIT_OK = 0
_EXIT_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return _EXIT_ERROR
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"beam: error: {exc}", file=sys.stderr)
        return _EXIT_ERROR


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="beam", description="metric-aware benchmark ranking")
    parser.add_argument("--version", action="version", version=f"beam {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser("validate", help="check a score file against the metric registry")
    p_validate.add_argument("scores", help="path to a score CSV (wide or long)")
    p_validate.add_argument("--metrics", help="comma-separated metric ids to require")
    p_validate.add_argument("--method", default="saw", help="aggregation to validate for")
    p_validate.set_defaults(func=_cmd_validate)

    p_rank = sub.add_parser("rank", help="rank tools and write a run record")
    p_rank.add_argument("scores", help="path to a score CSV (wide or long)")
    p_rank.add_argument("--weights", default="equal", help="equal, entropy, std, critic, merec")
    p_rank.add_argument("--method", default="saw", help="saw, topsis, vikor, promethee_ii, comet")
    p_rank.add_argument(
        "--on-missing",
        default="error",
        choices=("error", "available", "worst", "impute"),
        help="missing-cell policy: error (default), available (SAW only), worst, impute",
    )
    p_rank.add_argument("--no-sensitivity", action="store_true", help="skip sensitivity analysis")
    p_rank.add_argument("--seed", type=int, default=42, help="SMAA seed")
    p_rank.add_argument("--smaa-samples", type=int, default=1000, help="SMAA sample count")
    p_rank.add_argument("--out", help="write the run record JSON here (default stdout)")
    p_rank.add_argument("--report", help="also write an HTML report here")
    p_rank.add_argument("--manifest", help="also write the run manifest JSON here")
    p_rank.set_defaults(func=_cmd_rank)

    p_report = sub.add_parser("report", help="render an HTML report from a run record")
    p_report.add_argument("result", help="path to a run record JSON from 'beam rank'")
    p_report.add_argument("--out", required=True, help="write the HTML report here")
    p_report.set_defaults(func=_cmd_report)

    p_metric = sub.add_parser("metric", help="inspect the metric registry")
    metric_sub = p_metric.add_subparsers(dest="metric_command")
    p_show = metric_sub.add_parser("show", help="print a metric card summary")
    p_show.add_argument("id", help="metric id, for example ari")
    p_show.set_defaults(func=_cmd_metric_show)

    p_het = sub.add_parser(
        "heterogeneity", help="fit a method-dataset heterogeneity model (needs R)"
    )
    p_het.add_argument("scores", help="path to a long-format score CSV with a dataset column")
    p_het.add_argument(
        "--model",
        default="mixed-effects",
        choices=("mixed-effects", "bradley-terry-tree", "plackett-luce"),
        help="which heterogeneity model to fit (default mixed-effects)",
    )
    p_het.add_argument(
        "--metric",
        help="metric id to analyze; required when the file has more than one metric",
    )
    p_het.add_argument(
        "--features",
        help="dataset features CSV (first column dataset id), required for bradley-terry-tree",
    )
    p_het.add_argument(
        "--minsize", type=int, default=5, help="minimum leaf size for the Bradley-Terry tree"
    )
    p_het.add_argument("--out", help="write the report JSON here (default stdout)")
    p_het.set_defaults(func=_cmd_heterogeneity)

    p_run = sub.add_parser("run", help="run a benchmark from a beam.yaml file")
    p_run.add_argument("config", help="path to a beam.yaml file")
    p_run.set_defaults(func=_cmd_run)

    return parser


def _cmd_validate(args: argparse.Namespace) -> int:
    scores = load_scores(args.scores)
    ids = _split_metrics(args.metrics) if args.metrics else list(scores.metric_ids)
    missing = [mid for mid in ids if mid not in scores.metric_ids]
    if missing:
        raise ValueError(f"{args.scores} has no columns for {missing}")
    registry_context(ids, args.method)
    print(
        f"ok: {scores.n_tools} tools, {len(ids)} metrics ({', '.join(ids)}), layout {scores.layout}"
    )
    return _EXIT_OK


def _cmd_rank(args: argparse.Namespace) -> int:
    result = rank(
        args.scores,
        weights=args.weights,
        method=args.method,
        sensitivity=not args.no_sensitivity,
        missing=args.on_missing,
        seed=args.seed,
        smaa_samples=args.smaa_samples,
    )
    record = _run_record(result, args)
    text = json.dumps(record, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if args.report:
        write_report(result, args.report)
    if args.manifest:
        write_manifest(result.manifest, args.manifest)
    return _EXIT_OK


def _cmd_report(args: argparse.Namespace) -> int:
    record = json.loads(Path(args.result).read_text(encoding="utf-8"))
    params = record.get("params", {})
    input_path = record.get("input", {}).get("path")
    if not input_path:
        raise ValueError(
            f"{args.result} has no input path to re-run from; "
            "rank from a CSV file rather than an array"
        )
    result = rank(
        input_path,
        weights=params.get("weights", "equal"),
        method=params.get("method", "saw"),
        sensitivity=params.get("sensitivity", True),
        missing=params.get("missing", "error"),
        seed=params.get("seed", 42),
        smaa_samples=params.get("smaa_samples", 1000),
    )
    write_report(result, args.out)
    print(f"wrote {args.out}")
    return _EXIT_OK


def _cmd_metric_show(args: argparse.Namespace) -> int:
    card = Registry().get(args.id)
    sem = card.semantics
    rng = sem.get("range", {})
    lines = [
        f"id: {card.id}",
        f"version: {card.version}",
        f"name: {card.name}",
        f"measurand: {card.measurand}",
        f"task: {', '.join(card.task)}",
        f"scale_type: {card.scale_type}",
        f"polarity: {card.polarity}",
        f"range: [{rng.get('lower')}, {rng.get('upper')}]",
        f"recommended_normalization: {card.recommended_normalization}",
        f"recommended_aggregation_across_datasets: {card.recommended_aggregation_across_datasets}",
        f"implementations: {', '.join(impl.get('name', '?') for impl in card.implementations)}",
    ]
    print("\n".join(lines))
    return _EXIT_OK


def _cmd_run(args: argparse.Namespace) -> int:
    result = run_config(args.config)
    print(f"ok: {result.top_tool} ranks first of {len(result.tool_names)} tools")
    return _EXIT_OK


def _cmd_heterogeneity(args: argparse.Namespace) -> int:
    from .cards import properties_for
    from .heterogeneity import (
        RExecutionError,
        bradley_terry_tree,
        bttree_available,
        mixed_effects_from_matrix,
        plackett_luce,
        plackett_luce_available,
        r_available,
    )

    scores = load_scores(args.scores)
    if not scores.is_tensor or scores.dataset_names is None:
        raise ValueError(
            f"{args.scores} has no dataset axis; heterogeneity needs a long-format "
            "score file with tool, dataset, metric and score columns"
        )
    metric = _resolve_metric(scores, args.metric)
    matrix = scores.values[:, :, scores.metric_ids.index(metric)]
    tool_names = list(scores.tool_names)
    dataset_names = list(scores.dataset_names)
    polarity = properties_for([metric])[0].polarity

    probe = {
        "mixed-effects": (r_available, "lme4"),
        "bradley-terry-tree": (bttree_available, "psychotree and partykit"),
        "plackett-luce": (plackett_luce_available, "PlackettLuce and qvcalc"),
    }[args.model]
    if not probe[0]():
        raise ValueError(
            f"the R toolchain for {args.model} is not available ({probe[1]} on the R "
            "library path). Install it with the conda recipe envs/heterogeneity.yml"
        )

    try:
        if args.model == "mixed-effects":
            report = mixed_effects_from_matrix(matrix, tool_names, dataset_names)
            payload, summary = _mixed_effects_report(report, metric)
        elif args.model == "bradley-terry-tree":
            if not args.features:
                raise ValueError("bradley-terry-tree needs --features with a dataset features CSV")
            numeric, categorical = _load_features(args.features, dataset_names)
            report = bradley_terry_tree(
                matrix,
                tool_names,
                dataset_names,
                numeric_features=numeric,
                categorical_features=categorical,
                polarity=polarity,
                minsize=args.minsize,
            )
            payload, summary = _bradley_terry_report(report, metric)
        else:
            report = plackett_luce(matrix, tool_names, polarity=polarity)
            payload, summary = _plackett_luce_report(report, metric)
    except RExecutionError as exc:
        raise ValueError(f"the R fit failed: {exc}") from exc

    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(summary)
    else:
        print(text)
    return _EXIT_OK


def _resolve_metric(scores, requested: str | None) -> str:
    ids = list(scores.metric_ids)
    if requested is not None:
        if requested not in ids:
            raise ValueError(f"{requested!r} is not a metric in this file; have {', '.join(ids)}")
        return requested
    if len(ids) == 1:
        return ids[0]
    raise ValueError(f"this file has metrics {', '.join(ids)}; pass --metric to choose one")


def _load_features(
    path: str,
    dataset_names: list[str],
) -> tuple[dict[str, list[float]], dict[str, list[str]]]:
    """Read a dataset features CSV, aligned to ``dataset_names``.

    The first column is the dataset id; the remaining columns are features. A
    column whose values all parse as floats becomes a numeric feature, otherwise
    a categorical one. Every dataset in ``dataset_names`` must appear in the file.
    """
    import csv

    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        raise ValueError(f"{path} has no feature rows")
    header = rows[0]
    feature_names = header[1:]
    by_dataset = {row[0]: row[1:] for row in rows[1:]}
    missing = [d for d in dataset_names if d not in by_dataset]
    if missing:
        raise ValueError(f"{path} has no feature row for datasets {missing}")

    numeric: dict[str, list[float]] = {}
    categorical: dict[str, list[str]] = {}
    for col, name in enumerate(feature_names):
        values = [by_dataset[d][col] for d in dataset_names]
        try:
            numeric[name] = [float(v) for v in values]
        except ValueError:
            categorical[name] = values
    return numeric, categorical


def _mixed_effects_report(report, metric: str) -> tuple[dict[str, Any], str]:
    effects = [
        {"method": m, "effect": float(e), "se": float(s)}
        for m, e, s in zip(
            report.method_names, report.method_effects, report.method_effect_se, strict=True
        )
    ]
    payload = {
        "model": "mixed-effects",
        "metric": metric,
        "formula": report.formula,
        "n_methods": report.n_methods,
        "n_datasets": report.n_datasets,
        "n_obs": report.n_obs,
        "variance_components": {k: float(v) for k, v in report.variance_components.items()},
        "icc_dataset": float(report.icc_dataset),
        "interaction_share": (
            None if report.interaction_share is None else float(report.interaction_share)
        ),
        "residual_share": float(report.residual_share),
        "method_effects": effects,
        "singular": bool(report.singular),
        "warnings": list(report.warnings),
    }
    summary = (
        f"ok: mixed-effects on {metric}, the between-dataset shift is "
        f"{report.icc_dataset:.2f} of the variance"
    )
    return payload, summary


def _bradley_terry_report(report, metric: str) -> tuple[dict[str, Any], str]:
    global_order = np.argsort(-report.global_worth)
    global_ranking = [
        {
            "method": report.method_names[i],
            "worth": float(report.global_worth[i]),
            "worth_se": float(report.global_worth_se[i]),
        }
        for i in global_order
    ]
    nodes = [
        {
            "id": node.id,
            "terminal": node.terminal,
            "n": node.n,
            "split_variable": node.split_variable,
            "split_breakpoint": (
                None if node.split_breakpoint is None else float(node.split_breakpoint)
            ),
            "p_values": (
                None if node.p_values is None else {k: float(v) for k, v in node.p_values.items()}
            ),
            "worth": None if node.worth is None else [float(w) for w in node.worth],
        }
        for node in report.nodes
    ]
    leaf_assignment = {
        d: int(leaf) for d, leaf in zip(report.dataset_names, report.leaf_assignment, strict=True)
    }
    payload = {
        "model": "bradley-terry-tree",
        "metric": metric,
        "did_split": report.did_split,
        "feature_names": list(report.feature_names),
        "global_ranking": global_ranking,
        "nodes": nodes,
        "leaf_assignment": leaf_assignment,
        "reversed_leaves": report.reversed_leaves(),
        "summary": report.summary(),
        "warnings": list(report.warnings),
    }
    state = "split on dataset features" if report.did_split else "no stable split, flat ranking"
    summary = f"ok: bradley-terry tree on {metric}, {state}"
    return payload, summary


def _plackett_luce_report(report, metric: str) -> tuple[dict[str, Any], str]:
    order = np.argsort(-report.worth)
    ranking = [
        {
            "method": report.method_names[i],
            "worth": float(report.worth[i]),
            "quasi_se": float(report.quasi_se[i]),
            "log_worth": float(report.log_worth[i]),
        }
        for i in order
    ]
    payload = {
        "model": "plackett-luce",
        "metric": metric,
        "ranking": ranking,
        "n_rankings": report.n_rankings,
        "connected": report.connected,
        "loglik": float(report.loglik),
        "df": report.df,
        "aic": float(report.aic),
        "warnings": list(report.warnings),
    }
    top = report.method_names[int(order[0])]
    summary = f"ok: plackett-luce on {metric}, {top} has the highest worth"
    return payload, summary


def _run_record(result, args: argparse.Namespace) -> dict[str, Any]:
    res = result.result
    order = np.argsort(res.ranks)
    return {
        "beam_version": __version__,
        "input": result.manifest["input"],
        "params": {
            "weights": args.weights,
            "method": args.method,
            "sensitivity": not args.no_sensitivity,
            "missing": args.on_missing,
            "seed": args.seed,
            "smaa_samples": args.smaa_samples,
        },
        "metrics": list(result.metric_ids),
        "ranking": [
            {
                "rank": int(res.ranks[i]),
                "tool": result.tool_names[i],
                "composite": float(res.composite[i]),
            }
            for i in order
        ],
        "recommendation": recommendation(result),
        "manifest": result.manifest,
    }


def _split_metrics(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
