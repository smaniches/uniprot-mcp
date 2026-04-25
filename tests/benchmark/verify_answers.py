"""Programmatically re-derive every benchmark answer from live UniProt REST.

This is the operational complement to the AUDIT.md rationale strings.
A third party can run this script with no input but the repository
itself (and network access) and confirm — without trusting the author —
that the sealed ``expected.jsonl`` (held locally) matches the canonical
primary-source answer for every Tier A and Tier B prompt, and that the
structured-answer components for every Tier C prompt independently
verify against live UniProt.

Usage::

    python tests/benchmark/verify_answers.py [expected.jsonl]

If ``expected.jsonl`` is supplied, the script also compares the
verified answer for each prompt against the recorded answer; the exit
code is 0 only if every prompt's recorded answer equals the
freshly-derived canonical answer (with set-inclusion semantics for
Tier C 28 and 29 — see AUDIT.md for the snapshot-dependence policy).

If ``expected.jsonl`` is absent, the script prints the derived
canonical answers as a draft for human review before sealing.

The script is **not** wired into CI: CI is offline and billing-blocked
through the v1.0.1 timeline. Use this to (a) seal a fresh benchmark,
(b) sanity-check before any publication run, (c) demonstrate
reproducibility in compliance audits.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

import httpx

BASE = "https://rest.uniprot.org"
TIMEOUT = 30.0
UA = "uniprot-mcp-benchmark-verifier/1.0 (+https://github.com/smaniches/uniprot-mcp)"


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE,
        timeout=httpx.Timeout(TIMEOUT),
        headers={"User-Agent": UA, "Accept": "application/json"},
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Per-fact derivation helpers
# ---------------------------------------------------------------------------


def gene_to_accession(client: httpx.Client, gene: str) -> str:
    """Return the canonical reviewed UniProt accession for a human gene."""
    r = client.get(
        "/uniprotkb/search",
        params={
            "query": f"gene_exact:{gene} AND organism_id:9606 AND reviewed:true",
            "fields": "accession",
            "size": 1,
            "format": "json",
        },
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    if not results:
        raise RuntimeError(f"no reviewed accession for human gene {gene!r}")
    return str(results[0]["primaryAccession"])


def entry_field(client: httpx.Client, accession: str, path: list[str]) -> Any:
    """Walk a JSON path inside a UniProt entry."""
    r = client.get(f"/uniprotkb/{accession}.json")
    r.raise_for_status()
    obj: Any = r.json()
    for step in path:
        obj = obj[int(step)] if isinstance(obj, list) else obj[step]
    return obj


def fasta_first_residues(client: httpx.Client, accession: str, n: int) -> str:
    r = client.get(f"/uniprotkb/{accession}.fasta")
    r.raise_for_status()
    seq = "".join(line for line in r.text.splitlines()[1:] if not line.startswith(";")).replace(
        " ", ""
    )
    return seq[:n]


def keyword_id(client: httpx.Client, name: str) -> str:
    r = client.get(
        "/keywords/search",
        params={"query": f'name:"{name}"', "size": 3, "format": "json"},
    )
    r.raise_for_status()
    for hit in r.json().get("results", []):
        kw = hit.get("keyword") or {}
        if isinstance(kw, dict) and kw.get("name") == name:
            return str(kw.get("id", ""))
    raise RuntimeError(f"no keyword found for {name!r}")


def location_id(client: httpx.Client, name: str) -> str:
    r = client.get(
        "/locations/search",
        params={"query": f'name:"{name}"', "size": 3, "format": "json"},
    )
    r.raise_for_status()
    for hit in r.json().get("results", []):
        if hit.get("name") == name:
            return str(hit.get("id", ""))
    raise RuntimeError(f"no subcellular-location found for {name!r}")


def uniref_id(client: httpx.Client, tier: str, accession: str) -> str:
    candidate = f"UniRef{tier}_{accession}"
    r = client.get(f"/uniref/{candidate}")
    r.raise_for_status()
    return str(r.json()["id"])


def feature_types(client: httpx.Client, accession: str) -> list[str]:
    r = client.get(f"/uniprotkb/{accession}.json")
    r.raise_for_status()
    return sorted({f["type"] for f in r.json().get("features", []) if f.get("type")})


def crossref_databases(client: httpx.Client, accession: str) -> list[str]:
    r = client.get(f"/uniprotkb/{accession}.json")
    r.raise_for_status()
    return sorted(
        {x["database"] for x in r.json().get("uniProtKBCrossReferences", []) if x.get("database")}
    )


# ---------------------------------------------------------------------------
# Per-prompt derivation
# ---------------------------------------------------------------------------


def derive_all(client: httpx.Client) -> dict[int, Any]:
    out: dict[int, Any] = {}

    # Tier A — single-fact lookups
    out[1] = gene_to_accession(client, "TP53")
    out[2] = gene_to_accession(client, "BRCA1")
    out[3] = entry_field(client, "P38398", ["sequence", "length"])
    out[4] = entry_field(client, "P04637", ["genes", "0", "geneName", "value"])
    out[5] = entry_field(client, "P0DTC2", ["organism", "scientificName"])
    out[6] = gene_to_accession(client, "INS")
    out[7] = gene_to_accession(client, "HBB")
    out[8] = gene_to_accession(client, "KRAS")
    out[9] = gene_to_accession(client, "EGFR")
    out[10] = gene_to_accession(client, "DMD")

    # Tier B — structured single-entry
    out[11] = keyword_id(client, "Acetylation")
    out[12] = keyword_id(client, "Glycoprotein")
    out[13] = location_id(client, "Cell membrane")
    out[14] = location_id(client, "Nucleus")
    out[15] = location_id(client, "Mitochondrion")
    out[16] = fasta_first_residues(client, "P04637", 10)
    out[17] = uniref_id(client, "100", "P04637")
    out[18] = uniref_id(client, "50", "P04637")
    out[19] = gene_to_accession(client, "TP63")
    out[20] = gene_to_accession(client, "TP73")

    # Tier C — structured checklists
    out[21] = {
        sym: gene_to_accession(client, sym) for sym in ["TP53", "BRCA1", "BRCA2", "EGFR", "KRAS"]
    }
    out[22] = {
        name: location_id(client, name)
        for name in [
            "Cell membrane",
            "Cytoplasm",
            "Nucleus",
            "Mitochondrion",
            "Endoplasmic reticulum",
        ]
    }
    out[23] = {
        name: keyword_id(client, name)
        for name in [
            "Acetylation",
            "Phosphoprotein",
            "Glycoprotein",
            "Methylation",
            "Disulfide bond",
        ]
    }
    out[24] = {tier: uniref_id(client, tier, "P04637") for tier in ["50", "90", "100"]}
    out[25] = {sym: gene_to_accession(client, sym) for sym in ["KRAS", "NRAS", "HRAS"]}
    out[26] = {sym: gene_to_accession(client, sym) for sym in ["TP53", "TP63", "TP73"]}
    out[27] = {sym: gene_to_accession(client, sym) for sym in ["CYP3A4", "CYP2D6", "CYP1A2"]}
    out[28] = feature_types(client, "P04637")
    out[29] = crossref_databases(client, "P04637")
    out[30] = {sym: gene_to_accession(client, sym) for sym in ["HOXA1", "HOXA9", "HOXA13"]}

    return out


# ---------------------------------------------------------------------------
# Comparison + driver
# ---------------------------------------------------------------------------

# Prompts whose canonical answer is snapshot-dependent. Comparison uses
# set-inclusion: the recorded answer must be a *subset* of the live
# answer; live items not in the seal are credited but not required (per
# AUDIT.md snapshot-dependence policy).
_SNAPSHOT_SET_INCLUSION_PROMPTS = {28, 29}


def compare(prompt_id: int, recorded: Any, derived: Any) -> tuple[bool, str]:
    if prompt_id in _SNAPSHOT_SET_INCLUSION_PROMPTS:
        if not (isinstance(recorded, list) and isinstance(derived, list)):
            return (
                False,
                f"both must be lists; got {type(recorded).__name__} / {type(derived).__name__}",
            )
        missing = set(recorded) - set(derived)
        if missing:
            return False, f"recorded items missing from live answer: {sorted(missing)}"
        new_items = set(derived) - set(recorded)
        note = (
            f" (live has {len(new_items)} new item(s) since seal: {sorted(new_items)})"
            if new_items
            else ""
        )
        return True, f"set-inclusion verified{note}"
    return (
        recorded == derived,
        "exact match" if recorded == derived else f"recorded={recorded!r} live={derived!r}",
    )


def main(argv: list[str]) -> int:
    expected_path = pathlib.Path(argv[1]) if len(argv) > 1 else None
    recorded: dict[int, Any] = {}
    if expected_path is not None:
        if not expected_path.exists():
            print(f"ERROR: {expected_path} does not exist", file=sys.stderr)
            return 2
        for line in expected_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            recorded[int(obj["prompt_id"])] = obj["answer"]

    print(f"Re-deriving 30 answers from {BASE} ...", file=sys.stderr)
    with _client() as client:
        derived = derive_all(client)

    if not recorded:
        # Draft mode — print what we got.
        for pid in sorted(derived):
            print(f"prompt {pid:>2}: {derived[pid]!r}")
        return 0

    # Compare mode
    failures = 0
    for pid in sorted(set(recorded) | set(derived)):
        if pid not in recorded:
            print(f"  prompt {pid:>2}: NO RECORDED ANSWER")
            failures += 1
            continue
        if pid not in derived:
            print(f"  prompt {pid:>2}: NO DERIVED ANSWER")
            failures += 1
            continue
        ok, detail = compare(pid, recorded[pid], derived[pid])
        marker = "OK" if ok else "FAIL"
        print(f"  prompt {pid:>2}: {marker} — {detail}")
        if not ok:
            failures += 1

    if failures:
        print(f"\nFAILED: {failures} prompt(s) did not verify", file=sys.stderr)
        return 1
    print(f"\nOK: all 30 prompts verified against {BASE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
