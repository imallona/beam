"""Verify each candidate IRI by fetching it directly from OLS.

Prints label and obsolescence so we can pick the right term.
"""

import json
import sys
import urllib.parse
import urllib.request

CANDIDATES = [
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000593"),
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000628"),
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000415"),
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000416"),
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000687"),
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000280"),
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000201"),
    ("stato", "http://purl.obolibrary.org/obo/STATO_0000142"),
    ("uo", "http://purl.obolibrary.org/obo/UO_0000010"),
    ("uo", "http://purl.obolibrary.org/obo/UO_0000233"),
    ("uo", "http://purl.obolibrary.org/obo/UO_0010008"),
    ("uo", "http://purl.obolibrary.org/obo/UO_0000021"),
    ("uo", "http://purl.obolibrary.org/obo/UO_0000060"),
    ("uo", "http://purl.obolibrary.org/obo/UO_0000003"),
    ("uo", "http://purl.obolibrary.org/obo/UO_0000094"),
]


def fetch(ont, iri):
    encoded = urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")
    url = f"https://www.ebi.ac.uk/ols4/api/ontologies/{ont}/terms/{encoded}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def main():
    for ont, iri in CANDIDATES:
        d = fetch(ont, iri)
        if "error" in d:
            print(f"{iri}: ERROR {d['error']}", file=sys.stderr)
            continue
        print(f"{iri}: label={d.get('label')} obsolete={d.get('is_obsolete')}")


if __name__ == "__main__":
    main()
