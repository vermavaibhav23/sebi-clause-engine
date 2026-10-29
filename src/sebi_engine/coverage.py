"""Inventory leads for a human corpus audit, never a completeness certificate."""
import re
from .extract import normalized

# Modern SEBI/HO identifiers; older CIR/MIRSD formats need separate manual discovery.
IDENTIFIER = re.compile(r"SEBI\s*/\s*HO(?:\s*/\s*[A-Z0-9_-]+)+\s*/\s*20\d{2}\s*/\s*\d+", re.I)


def coverage_report(store):
    docs = store.documents()
    imported = {normalized(d.id) for d in docs}
    leads = {}
    for clause in store.clauses():
        for match in IDENTIFIER.finditer(clause.text):
            circular_id = re.sub(r"\s+", "", match[0])
            if normalized(circular_id) not in imported:
                leads.setdefault(circular_id, []).append(clause.id)
    return {"documents": len(docs), "clauses_and_table_rows": len(store.clauses()),
            "unreviewed_events": [e.id for e in store.amendments() if e.status == "proposed"],
            "missing_reference_candidates": [{"circular_id": k, "source_clause_ids": sorted(set(v))}
                                             for k, v in sorted(leads.items())],
            "limitations": ["References may be ordinary context, not amendments",
                            "Only modern SEBI/HO identifier syntax is scanned",
                            "Forward amendments, old identifiers and complete chains need an independent official-source audit",
                            "A zero count is not proof of completeness"]}
