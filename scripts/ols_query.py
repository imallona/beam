"""Query OLS for STATO, UO, OBI terms matching beam metric names.

One-off helper used during the ontology lift sweep. Not part of the runtime.
Outputs JSON to stdout; consume with the per-metric mapping decision step.
"""

import json
import urllib.parse
import urllib.request

QUERIES = {
    "ari": ["adjusted rand index", "Hubert-Arabie"],
    "nmi": ["normalized mutual information", "mutual information"],
    "f1_score": ["F1 score", "F-measure"],
    "accuracy": ["accuracy", "classification accuracy"],
    "silhouette": ["silhouette coefficient", "silhouette"],
    "asw_batch": ["average silhouette width", "silhouette"],
    "asw_label": ["average silhouette width", "silhouette"],
    "isolated_label_asw": ["isolated label silhouette", "silhouette"],
    "isolated_label_f1": ["isolated label F1", "F1 score"],
    "kbet": ["kBET", "batch effect test"],
    "clisi": ["LISI", "local inverse Simpson"],
    "ilisi": ["LISI", "integration local inverse Simpson"],
    "graph_connectivity": ["graph connectivity"],
    "hvg_overlap": ["highly variable gene overlap"],
    "cell_cycle_conservation": ["cell cycle conservation"],
    "pcr": ["principal component regression"],
    "shannon_entropy_diff": ["Shannon entropy", "entropy"],
    "nclust_deviation": ["cluster number"],
    "smape": ["symmetric mean absolute percentage error", "SMAPE"],
    "mase": ["mean absolute scaled error", "MASE"],
    "calibration_slope": ["calibration slope", "calibration"],
    "correlation": ["Pearson correlation", "correlation coefficient"],
    "runtime": ["runtime", "execution time"],
    "peak_memory": ["peak memory", "memory usage"],
    "speed": ["speed", "velocity"],
    "cost": ["cost", "monetary cost"],
    "co2": ["carbon dioxide", "CO2 emission"],
}


def search(q, ontology):
    url = (
        "https://www.ebi.ac.uk/ols4/api/search?q="
        + urllib.parse.quote(q)
        + f"&ontology={ontology}&rows=5"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            d = json.loads(r.read())
        return [(x.get("iri"), x.get("label")) for x in d["response"]["docs"]]
    except Exception as e:
        return [("ERROR", str(e))]


def main():
    out = {}
    for metric, qs in QUERIES.items():
        out[metric] = {"stato": [], "uo": [], "obi": []}
        for q in qs:
            for ont in ["stato", "uo", "obi"]:
                hits = search(q, ont)
                for iri, lab in hits:
                    if iri and iri != "ERROR" and (iri, lab) not in out[metric][ont]:
                        out[metric][ont].append((iri, lab))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
