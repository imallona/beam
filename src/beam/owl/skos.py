"""Generate docs/beam.skos.ttl, a SKOS scheme over beam's controlled vocabulary.

The metric cards draw four fields from closed enumerations: the polarity, the
measurement scale type, the allowed transformations, and the recommended
normalization strategy. This module publishes those enumerations as SKOS
concept schemes so the controlled vocabulary is dereferenceable and citable,
one skos:Concept per allowed value with a prefLabel and a definition, and
skos:broader edges where a value specializes another (the Stevens scale ladder,
and the normalizations that are special cases of an affine transform).

The enum values are read from the JSON Schema, so a value that no card uses yet
still gets a concept. The definitions are hand-written here from
docs/explanations/measurement-theory.md and normalization-and-scales.md; the
generator refuses to run if the schema gains an enum value with no definition.

Run from the repo root with the dev extras installed:

    python -m beam.owl.skos
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from rdflib import RDF, RDFS, Graph, Literal
from rdflib.namespace import SKOS

from beam.owl.generate import BEAM

# The four card fields whose values form a controlled vocabulary, each with the
# JSON Schema path to its enum. allowed_transformations is a list, so its enum
# sits under "items".
FIELDS = {
    "polarity": {
        "title": "metric polarity",
        "schema_path": ["properties", "semantics", "properties", "polarity"],
    },
    "scale_type": {
        "title": "measurement scale type",
        "schema_path": ["properties", "semantics", "properties", "scale_type"],
    },
    "allowed_transformations": {
        "title": "allowed transformation",
        "schema_path": [
            "properties",
            "semantics",
            "properties",
            "allowed_transformations",
            "items",
        ],
    },
    "recommended_normalization": {
        "title": "recommended normalization strategy",
        "schema_path": [
            "properties",
            "comparability",
            "properties",
            "recommended_normalization",
        ],
    },
}

# prefLabel and definition per (field, value). Definitions are grounded in the
# measurement-theory and normalization-and-scales explanation essays.
DEFINITIONS = {
    "polarity": {
        "higher_is_better": (
            "higher is better",
            "A larger value indicates better performance; normalization and "
            "ranking orient so the maximum is best.",
        ),
        "lower_is_better": (
            "lower is better",
            "A smaller value indicates better performance, so the orientation "
            "is flipped (for example runtime or an error rate).",
        ),
        "target_value": (
            "target value",
            "An ideal fixed value exists and a deviation in either direction "
            "is worse; requires a declared target and pairs only with the "
            "target_relative normalization.",
        ),
    },
    "scale_type": {
        "nominal": (
            "nominal scale",
            "Labels without order; only equality is meaningful.",
        ),
        "ordinal": (
            "ordinal scale",
            "Ordered labels; comparison is meaningful but the differences between values are not.",
        ),
        "interval": (
            "interval scale",
            "Numeric with a meaningful unit but no meaningful zero; "
            "differences are meaningful, ratios are not.",
        ),
        "ratio": (
            "ratio scale",
            "Numeric with a meaningful unit and a true zero; all four "
            "arithmetic operations are meaningful.",
        ),
    },
    "allowed_transformations": {
        "affine": (
            "affine transformation",
            "A transform a*x + b; meaning-preserving on an interval scale.",
        ),
        "log": (
            "logarithm",
            "The logarithm; preserves the multiplicative structure of a "
            "strictly positive ratio metric.",
        ),
        "rank": (
            "rank transformation",
            "Replace each value by its within-column position; scale-free and "
            "outlier-resistant, valid on any orderable scale.",
        ),
        "arcsin": (
            "arcsine transformation",
            "The arcsine transform, used to stabilize the variance of a proportion.",
        ),
        "sqrt": (
            "square-root transformation",
            "The square-root transform, a variance-stabilizing transform for count-like data.",
        ),
        "negate": (
            "negation",
            "A sign flip -x, used to reorient polarity.",
        ),
        "min_max": (
            "min-max rescaling",
            "An affine rescale to the unit interval using the observed extremes.",
        ),
        "z_score": (
            "z-score standardization",
            "Standardization (x - mean) / sd.",
        ),
    },
    "recommended_normalization": {
        "min_max": (
            "min-max normalization",
            "Rescale to the unit interval against the declared bounded range; "
            "the default strategy.",
        ),
        "log_min_max": (
            "log then min-max normalization",
            "Take the logarithm then min-max rescale, so one outlier on a "
            "ratio metric does not compress the rest; needs strictly positive "
            "values.",
        ),
        "rank": (
            "rank normalization",
            "Map each within-column position to the unit interval; "
            "outlier-immune and free of a scale assumption.",
        ),
        "zscore": (
            "z-score normalization",
            "Standardize then squash through the logistic so the result stays "
            "in the open unit interval and the mean method maps to 0.5.",
        ),
        "baseline_relative": (
            "baseline-relative normalization",
            "Rescale against a declared chance score so a chance-level method "
            "maps to zero rather than to the column midpoint.",
        ),
        "target_relative": (
            "target-relative normalization",
            "For a target-value metric, min-max rescale the absolute deviation "
            "from the target with flipped polarity, so the method nearest the "
            "target maps to one.",
        ),
    },
}

# skos:broader edges (child, parent) per field. scale_type is the Stevens
# (1946) containment ladder; the two transformations and the one normalization
# below specialize an affine or min-max parent.
BROADER = {
    "scale_type": [("ordinal", "nominal"), ("interval", "ordinal"), ("ratio", "interval")],
    "allowed_transformations": [("min_max", "affine"), ("z_score", "affine")],
    "recommended_normalization": [("log_min_max", "min_max")],
}


def _schema() -> dict:
    text = resources.files("beam").joinpath("schema/metric_card.schema.json").read_text()
    return json.loads(text)


def _output_path() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "beam.skos.ttl"


def _enum_for(schema: dict, schema_path: list[str]) -> list[str]:
    node = schema
    for key in schema_path:
        node = node[key]
    return node["enum"]


def build_graph(schema: dict) -> Graph:
    g = Graph()
    g.bind("beam", BEAM)
    g.bind("skos", SKOS)
    g.bind("rdfs", RDFS)

    for field, spec in FIELDS.items():
        scheme = BEAM[f"scheme/{field}"]
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, RDFS.label, Literal(spec["title"], lang="en")))

        values = _enum_for(schema, spec["schema_path"])
        defs = DEFINITIONS[field]
        children = {child for child, _ in BROADER.get(field, [])}
        for value in values:
            if value not in defs:
                raise ValueError(f"no SKOS definition for {field} value {value!r}")
            concept = BEAM[f"{field}/{value}"]
            label, definition = defs[value]
            g.add((concept, RDF.type, SKOS.Concept))
            g.add((concept, SKOS.inScheme, scheme))
            g.add((concept, SKOS.prefLabel, Literal(label, lang="en")))
            g.add((concept, SKOS.definition, Literal(definition, lang="en")))
            if value not in children:
                g.add((scheme, SKOS.hasTopConcept, concept))

        for child, parent in BROADER.get(field, []):
            g.add((BEAM[f"{field}/{child}"], SKOS.broader, BEAM[f"{field}/{parent}"]))
            g.add((BEAM[f"{field}/{parent}"], SKOS.narrower, BEAM[f"{field}/{child}"]))

    return g


def main() -> None:
    g = build_graph(_schema())
    out = _output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(out), format="turtle")
    print(f"wrote {out} ({len(g)} triples over {len(FIELDS)} schemes)")


if __name__ == "__main__":
    main()
