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
    beam run beam.yaml

``beam rank`` writes a small run record (the input path and hash, the
parameters, the ranking, and the manifest). ``beam report`` reads that record,
reloads the scores, re-runs with the recorded parameters (deterministic through
the recorded seed), and renders the HTML report. ``beam heterogeneity`` and
``beam metric run`` are not yet exposed (the heterogeneity and metric-execution commands).
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
