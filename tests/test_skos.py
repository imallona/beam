"""Tests for the SKOS controlled-vocabulary generator."""

from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import SKOS

from beam.owl.skos import BEAM, FIELDS, _enum_for, _schema, build_graph


def test_every_enum_value_has_one_concept():
    schema = _schema()
    g = build_graph(schema)
    for field, spec in FIELDS.items():
        for value in _enum_for(schema, spec["schema_path"]):
            concept = BEAM[f"{field}/{value}"]
            assert (concept, RDF.type, SKOS.Concept) in g
            assert (concept, SKOS.inScheme, BEAM[f"scheme/{field}"]) in g


def test_every_concept_has_preflabel_and_definition():
    g = build_graph(_schema())
    for concept in g.subjects(RDF.type, SKOS.Concept):
        assert g.value(concept, SKOS.prefLabel) is not None
        assert g.value(concept, SKOS.definition) is not None


def test_one_scheme_per_field():
    g = build_graph(_schema())
    schemes = set(g.subjects(RDF.type, SKOS.ConceptScheme))
    assert schemes == {BEAM[f"scheme/{field}"] for field in FIELDS}


def test_stevens_ladder_is_a_broader_chain():
    g = build_graph(_schema())
    st = "scale_type"
    assert (BEAM[f"{st}/ratio"], SKOS.broader, BEAM[f"{st}/interval"]) in g
    assert (BEAM[f"{st}/interval"], SKOS.broader, BEAM[f"{st}/ordinal"]) in g
    assert (BEAM[f"{st}/ordinal"], SKOS.broader, BEAM[f"{st}/nominal"]) in g
    # nominal is the root of the ladder, so it is a top concept of the scheme.
    assert (BEAM[f"scheme/{st}"], SKOS.hasTopConcept, BEAM[f"{st}/nominal"]) in g
    assert (BEAM[f"scheme/{st}"], SKOS.hasTopConcept, BEAM[f"{st}/ratio"]) not in g


def test_normalization_specializations_point_at_affine_min_max():
    g = build_graph(_schema())
    assert (
        BEAM["recommended_normalization/log_min_max"],
        SKOS.broader,
        BEAM["recommended_normalization/min_max"],
    ) in g
    assert (
        BEAM["allowed_transformations/min_max"],
        SKOS.broader,
        BEAM["allowed_transformations/affine"],
    ) in g


def test_artefact_round_trips_through_turtle():
    g = build_graph(_schema())
    turtle = g.serialize(format="turtle")
    reparsed = Graph().parse(data=turtle, format="turtle")
    assert len(reparsed) == len(g)
