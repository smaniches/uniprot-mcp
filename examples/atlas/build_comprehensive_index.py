"""Build a comprehensive disease-protein index from live UniProt.

Queries UniProt's REST API for every Swiss-Prot (reviewed) human
entry that carries at least one DISEASE-type comment, plus a curated
set of pathogen organisms commonly studied in infectious-disease
research. Emits a TSV (one row per accession x disease pair) with
the canonical UniProt fields and the MIM / disease-id cross-refs.

This is the *exhaustive* counterpart to the 25 hand-curated atlas
entries. The hand-written entries demonstrate what a single research
question looks like; this index lets a downstream agent (or a
researcher with grep) find every protein UniProt itself associates
with a disease.

Reproducibility:

  - The script is fully deterministic given a UniProt release. Each
    output row carries the UniProt accession; subsequent calls to
    `uniprot-mcp` against that accession return the live state plus
    a SHA-256 provenance receipt.
  - Pagination via UniProt's cursor. Polite rate-limiting between
    batches.
  - Re-running this script on a future UniProt release will produce
    a different TSV (more entries as curation grows). Diffs between
    runs document what UniProt added or revised.

Usage:

    python examples/atlas/build_comprehensive_index.py [--out PATH] [--scope SCOPE]

  --out:    output TSV path (default: examples/atlas/comprehensive_index.tsv)
  --scope:  one of {human, pathogens, all} (default: all)

Run from the repo root with network access to rest.uniprot.org.

License: Apache-2.0.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from typing import Any

import httpx

UNIPROT_BASE = "https://rest.uniprot.org"
UA = "uniprot-mcp-atlas-builder/1.0 (+https://github.com/smaniches/uniprot-mcp)"
PAGE_SIZE = 500
INTER_BATCH_SLEEP = 0.5  # polite rate-limit; UniProt is forgiving but we are too

# Pathogen organisms with significant infectious-disease research footprint.
# Curated, not exhaustive — adding more is one PR away.
PATHOGEN_ORGANISMS = [
    ("Mycobacterium tuberculosis", 83332),  # H37Rv reference strain
    ("Plasmodium falciparum", 36329),  # malaria 3D7 strain
    ("Trypanosoma brucei", 5691),  # sleeping sickness
    ("Leishmania donovani", 5661),  # leishmaniasis
    ("Severe acute respiratory syndrome coronavirus 2", 2697049),  # SARS-CoV-2
    ("Human immunodeficiency virus 1", 11676),  # HIV-1
    ("Hepatitis C virus", 11103),  # HCV
    ("Influenza A virus", 11320),  # IAV
    ("Escherichia coli", 562),  # general E. coli (incl. resistance enzymes like TEM)
    ("Staphylococcus aureus", 1280),
    ("Streptococcus pneumoniae", 1313),
    ("Pseudomonas aeruginosa", 287),
    ("Klebsiella pneumoniae", 573),
    ("Acinetobacter baumannii", 470),  # critical-priority WHO pathogen
    ("Candida albicans", 5476),
    ("Aspergillus fumigatus", 746128),
]


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=UNIPROT_BASE,
        timeout=httpx.Timeout(60.0),
        headers={"User-Agent": UA, "Accept": "application/json"},
        follow_redirects=True,
    )


def _paginate(client: httpx.Client, query: str, fields: str) -> list[dict[str, Any]]:
    """Walk UniProt search results via cursor pagination.

    UniProt sends a ``Link: <URL>; rel="next"`` header on each response;
    the URL contains a ``cursor`` query-string parameter. We extract the
    cursor with an explicit regex (more robust than parsing the full
    Link header) and re-issue the same query with that cursor until
    UniProt stops sending one.
    """
    import re

    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {
            "query": query,
            "fields": fields,
            "size": PAGE_SIZE,
            "format": "json",
        }
        if cursor is not None:
            params["cursor"] = cursor
        r = httpx.get(
            f"{UNIPROT_BASE}/uniprotkb/search",
            params=params,
            timeout=httpx.Timeout(120.0),
            headers={"User-Agent": UA, "Accept": "application/json"},
            follow_redirects=True,
        )
        r.raise_for_status()
        body = r.json()
        page_rows = body.get("results", []) or []
        rows.extend(page_rows)
        pages += 1
        if pages == 1:
            total = r.headers.get("X-Total-Results", "?")
            print(f"    page 1: {len(page_rows)} entries; X-Total-Results={total}", file=sys.stderr)
        # Extract cursor from Link header.
        link = r.headers.get("Link", "")
        m = re.search(r'cursor=([^&>"]+)', link) if 'rel="next"' in link else None
        if not m:
            break
        cursor = m.group(1)
        if pages % 5 == 0:
            print(f"    page {pages}: total accumulated {len(rows)} entries", file=sys.stderr)
        time.sleep(INTER_BATCH_SLEEP)
    print(f"    paginated {pages} page(s); {len(rows)} entries total", file=sys.stderr)
    return rows


def _expand_diseases(entry: dict[str, Any]) -> list[dict[str, str]]:
    """Pull DISEASE-type comments from a UniProt entry; emit one row per
    disease. Each row carries the entry-level fields (accession, gene,
    protein name, length, organism) plus per-disease fields (acronym,
    UniProt disease ID, MIM ID, MIM name)."""
    rows: list[dict[str, str]] = []
    accession = str(entry.get("primaryAccession", ""))
    gene = ""
    genes = entry.get("genes", []) or []
    if genes:
        gene = str(genes[0].get("geneName", {}).get("value", ""))
    protein_name = ""
    pd = entry.get("proteinDescription", {}) or {}
    rec = pd.get("recommendedName", {}) or {}
    if rec:
        protein_name = str(rec.get("fullName", {}).get("value", ""))
    organism = entry.get("organism", {}) or {}
    org_name = str(organism.get("scientificName", ""))
    org_taxon = str(organism.get("taxonId", ""))
    seq = entry.get("sequence", {}) or {}
    length = str(seq.get("length", ""))

    comments = entry.get("comments", []) or []
    for c in comments:
        if c.get("commentType") != "DISEASE":
            continue
        disease = c.get("disease") or {}
        if not disease:
            continue
        # UniProt's `diseaseId` field is the human-readable name.
        # `diseaseAccession` is the DI-NNNNN code.
        disease_name = str(disease.get("diseaseId", "") or "")
        disease_acc = str(disease.get("diseaseAccession", "") or "")
        acronym = str(disease.get("acronym", "") or "")
        mim_id = ""
        # The disease's own crossReferences carry MIM:NNNNNN
        for x in disease.get("crossReferences") or disease.get("xrefs") or []:
            db = (x.get("database") or "").upper()
            if db == "MIM":
                mim_id = str(x.get("id", ""))
                break
        if not mim_id:
            # Some payloads store the MIM at disease.crossReference (singular)
            xref = disease.get("crossReference") or {}
            if xref.get("database", "").upper() == "MIM":
                mim_id = str(xref.get("id", ""))
        rows.append(
            {
                "accession": accession,
                "gene": gene,
                "protein_name": protein_name,
                "length": length,
                "organism": org_name,
                "organism_taxon_id": org_taxon,
                "disease_uniprot_name": disease_name,
                "disease_uniprot_id": disease_acc,
                "disease_acronym": acronym,
                "mim_id": mim_id,
                "uniprot_url": f"{UNIPROT_BASE}/uniprotkb/{accession}",
            }
        )
    return rows


def harvest_human(client: httpx.Client) -> list[dict[str, str]]:
    """Every reviewed human entry that carries a DISEASE comment."""
    print("Harvesting human disease entries from UniProt ...", file=sys.stderr)
    fields = (
        "accession,gene_names,protein_name,length,organism_name,organism_id,cc_disease,xref_mim"
    )
    query = "(organism_id:9606) AND (reviewed:true) AND (cc_disease:*)"
    entries = _paginate(client, query, fields)
    rows: list[dict[str, str]] = []
    for e in entries:
        rows.extend(_expand_diseases(e))
    print(f"  human disease rows: {len(rows)} from {len(entries)} entries", file=sys.stderr)
    return rows


def harvest_pathogens(client: httpx.Client) -> list[dict[str, str]]:
    """All Swiss-Prot reviewed entries from the curated pathogen list."""
    print("Harvesting pathogen entries from UniProt ...", file=sys.stderr)
    fields = (
        "accession,gene_names,protein_name,length,organism_name,organism_id,cc_disease,xref_mim"
    )
    rows: list[dict[str, str]] = []
    for org_name, taxon_id in PATHOGEN_ORGANISMS:
        print(f"  {org_name} (taxon {taxon_id}) ...", file=sys.stderr)
        query = f"(organism_id:{taxon_id}) AND (reviewed:true)"
        entries = _paginate(client, query, fields)
        for e in entries:
            # Pathogen entries don't always have DISEASE comments per UniProt's
            # human-disease policy. Emit one row per entry with an empty
            # disease block; the row's *organism* is itself the disease
            # context. Add a sentinel disease record so the TSV shape
            # stays consistent.
            disease_rows = _expand_diseases(e)
            if disease_rows:
                rows.extend(disease_rows)
            else:
                accession = str(e.get("primaryAccession", ""))
                gene = ""
                genes = e.get("genes", []) or []
                if genes:
                    gene = str(genes[0].get("geneName", {}).get("value", ""))
                protein_name = ""
                pd = e.get("proteinDescription", {}) or {}
                rec = pd.get("recommendedName", {}) or {}
                if rec:
                    protein_name = str(rec.get("fullName", {}).get("value", ""))
                length = str((e.get("sequence", {}) or {}).get("length", ""))
                rows.append(
                    {
                        "accession": accession,
                        "gene": gene,
                        "protein_name": protein_name,
                        "length": length,
                        "organism": org_name,
                        "organism_taxon_id": str(taxon_id),
                        "disease_uniprot_name": "",
                        "disease_uniprot_id": "",
                        "disease_acronym": "",
                        "mim_id": "",
                        "uniprot_url": f"{UNIPROT_BASE}/uniprotkb/{accession}",
                    }
                )
        print(f"    {len(entries)} entries", file=sys.stderr)
        time.sleep(INTER_BATCH_SLEEP)
    print(f"  pathogen rows: {len(rows)}", file=sys.stderr)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="examples/atlas/comprehensive_index.tsv",
        help="output TSV path",
    )
    parser.add_argument(
        "--scope",
        choices=["human", "pathogens", "all"],
        default="all",
        help="which universe to harvest",
    )
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    with _client() as client:
        if args.scope in {"human", "all"}:
            rows.extend(harvest_human(client))
        if args.scope in {"pathogens", "all"}:
            rows.extend(harvest_pathogens(client))

    if not rows:
        print("No rows harvested; check network + query.", file=sys.stderr)
        return 1

    fieldnames = [
        "accession",
        "gene",
        "protein_name",
        "length",
        "organism",
        "organism_taxon_id",
        "disease_uniprot_name",
        "disease_uniprot_id",
        "disease_acronym",
        "mim_id",
        "uniprot_url",
    ]
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"Wrote {len(rows)} rows to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
