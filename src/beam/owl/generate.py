"""Generate docs/beam.owl.ttl from the bundled metric cards.

Each card becomes an instance of beam:Metric. If the card declares
mappings.stato (or .uo, .obi), the instance is asserted as an instance of the
external class via owl:sameAs and a typed annotation, so a downstream reasoner
can follow the link. The artefact is regenerated on every release; the
content is fully determined by the cards plus the schema.

Run from the repo root with the dev extras installed:

    python -m beam.owl.generate
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef

BEAM = Namespace("https://github.com/imallona/beam/owl/")
OBO = Namespace("http://purl.obolibrary.org/obo/")


def _cards_dir() -> Path:
    return Path(str(resources.files("beam").joinpath("metrics")))


def _output_path() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "beam.owl.ttl"


def _load_cards() -> list[dict]:
    cards: list[dict] = []
    for path in sorted(_cards_dir().glob("*/v*.yaml")):
        with path.open() as f:
            cards.append(yaml.safe_load(f))
    return cards


def build_graph(cards: list[dict]) -> Graph:
    g = Graph()
    g.bind("beam", BEAM)
    g.bind("obo", OBO)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)

    metric_cls = BEAM["Metric"]
    g.add((metric_cls, RDF.type, OWL.Class))
    g.add((metric_cls, RDFS.label, Literal("beam metric")))

    for card in cards:
        instance = BEAM[card["id"]]
        g.add((instance, RDF.type, metric_cls))
        g.add((instance, RDF.type, OWL.NamedIndividual))
        g.add((instance, RDFS.label, Literal(card.get("name", card["id"]))))
        if "description" in card:
            g.add((instance, RDFS.comment, Literal(card["description"].strip())))
        for key, value in (card.get("mappings") or {}).items():
            if not isinstance(value, str):
                continue
            target = URIRef(value)
            if key == "stato":
                g.add((instance, RDF.type, target))
                g.add((instance, OWL.sameAs, target))
            elif key in {"uo", "obi", "qudt", "om2", "huggingface_evaluate"}:
                g.add((instance, RDFS.seeAlso, target))
    return g


def main() -> None:
    cards = _load_cards()
    g = build_graph(cards)
    out = _output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(out), format="turtle")
    print(f"wrote {out} ({len(g)} triples over {len(cards)} cards)")


if __name__ == "__main__":
    main()
