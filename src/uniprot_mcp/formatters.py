"""Response formatters: JSON and Markdown output for UniProt data.

Pure functions, no I/O. Strict type hints (mypy strict-compatible).
"""

from __future__ import annotations

import json
from typing import Any

Entry = dict[str, Any]
Feature = dict[str, Any]
Xref = dict[str, Any]

__all__ = [
    "fmt_crossrefs",
    "fmt_entry",
    "fmt_features",
    "fmt_go",
    "fmt_idmapping",
    "fmt_search",
    "fmt_taxonomy",
    "fmt_variants",
    "is_swissprot",
]


def is_swissprot(entry: Entry) -> bool:
    """True if the entry is Swiss-Prot (reviewed) rather than TrEMBL."""
    return str(entry.get("entryType", "")).startswith("UniProtKB reviewed")


def _protein_name(entry: Entry) -> str:
    pd: dict[str, Any] = entry.get("proteinDescription", {}) or {}
    rec: dict[str, Any] = pd.get("recommendedName", {}) or {}
    if rec:
        return str(rec.get("fullName", {}).get("value", "Unknown"))
    sub = pd.get("submissionNames", []) or []
    if sub:
        return str(sub[0].get("fullName", {}).get("value", "Unknown"))
    return "Unknown"


def _gene_name(entry: Entry) -> str:
    genes = entry.get("genes", []) or []
    if not genes:
        return ""
    return str(genes[0].get("geneName", {}).get("value", ""))


def _organism(entry: Entry) -> str:
    org = entry.get("organism", {}) or {}
    return str(org.get("scientificName", "Unknown"))


def fmt_entry(data: Entry, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    acc = data.get("primaryAccession", "?")
    name = _protein_name(data)
    gene = _gene_name(data)
    org = _organism(data)
    reviewed = "Swiss-Prot" if is_swissprot(data) else "TrEMBL"
    seq: dict[str, Any] = data.get("sequence", {}) or {}
    lines: list[str] = [f"## {acc}: {name}", ""]
    if gene:
        lines.append(f"**Gene:** {gene}")
    lines.append(f"**Organism:** {org}")
    lines.append(f"**Reviewed:** {reviewed}")
    if seq:
        lines.append(
            f"**Length:** {seq.get('length', '?')} aa | **Mass:** {seq.get('molWeight', '?')} Da"
        )
    for c in data.get("comments", []) or []:
        ctype = c.get("commentType")
        if ctype == "FUNCTION":
            texts = c.get("texts", []) or []
            if texts:
                lines.extend(["", f"**Function:** {texts[0].get('value', '')}"])
        elif ctype == "SUBCELLULAR LOCATION":
            locs: list[str] = [
                str(loc.get("location", {}).get("value", ""))
                for loc in c.get("subcellularLocations", []) or []
                if loc.get("location")
            ]
            if locs:
                lines.append(f"**Localization:** {', '.join(locs[:5])}")
        elif ctype == "DISEASE":
            disease: dict[str, Any] = c.get("disease", {}) or {}
            if disease:
                did = disease.get("diseaseId", "")
                desc = str(disease.get("description", ""))[:150]
                lines.append(f"**Disease:** {did} - {desc}")
    xrefs: list[Xref] = data.get("uniProtKBCrossReferences", []) or []
    if xrefs:
        dbs: dict[str, int] = {}
        for x in xrefs:
            db = str(x.get("database", "?"))
            dbs[db] = dbs.get(db, 0) + 1
        pdb_ids = [str(x.get("id", "")) for x in xrefs if x.get("database") == "PDB"]
        lines.extend(["", f"**Cross-refs:** {len(xrefs)} across {len(dbs)} databases"])
        if pdb_ids:
            show = pdb_ids[:10]
            extra = f" (+{len(pdb_ids) - 10} more)" if len(pdb_ids) > 10 else ""
            lines.append(f"**PDB:** {', '.join(show)}{extra}")
    return "\n".join(lines)


def fmt_search(data: dict[str, Any], fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    results: list[Entry] = data.get("results", []) or []
    lines: list[str] = [f"**{len(results)} results**", ""]
    for i, e in enumerate(results, 1):
        acc = e.get("primaryAccession", "?")
        name = _protein_name(e)
        gene = _gene_name(e)
        org = _organism(e)
        rev = "SP" if is_swissprot(e) else "TR"
        length = e.get("sequence", {}).get("length", "?")
        g = f" ({gene})" if gene else ""
        lines.append(f"**{i}. [{acc}]** {name}{g}")
        lines.append(f"   {org} | {length} aa | {rev}")
        lines.append("")
    return "\n".join(lines)


def fmt_features(features: list[Feature], accession: str, fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(features, indent=2, ensure_ascii=False, default=str)
    by_type: dict[str, list[Feature]] = {}
    for f in features:
        by_type.setdefault(str(f.get("type", "?")), []).append(f)
    lines: list[str] = [f"## Features: {accession} ({len(features)} total)", ""]
    for ftype, feats in sorted(by_type.items()):
        lines.append(f"### {ftype} ({len(feats)})")
        for feat in feats[:20]:
            loc = feat.get("location", {}) or {}
            start = loc.get("start", {}).get("value", "?")
            end = loc.get("end", {}).get("value", "?")
            desc = feat.get("description", "")
            lines.append(f"  {start}-{end}: {desc}" if desc else f"  {start}-{end}")
        if len(feats) > 20:
            lines.append(f"  ... (+{len(feats) - 20} more)")
        lines.append("")
    return "\n".join(lines)


def fmt_go(
    xrefs: list[Xref],
    accession: str,
    aspect_filter: str | None,
    fmt: str = "markdown",
) -> str:
    go_refs: list[Xref] = [x for x in xrefs if x.get("database") == "GO"]
    if fmt == "json":
        return json.dumps(go_refs, indent=2, ensure_ascii=False, default=str)
    by_aspect: dict[str, list[tuple[str, str, str]]] = {"F": [], "P": [], "C": []}
    for ref in go_refs:
        go_id = str(ref.get("id", ""))
        props: dict[str, str] = {
            str(p["key"]): str(p["value"]) for p in ref.get("properties", []) or []
        }
        term = props.get("GoTerm", "")
        ev = props.get("GoEvidenceType", "")
        for prefix in ("F:", "P:", "C:"):
            if term.startswith(prefix):
                by_aspect[prefix[0]].append((go_id, term[2:], ev))
    if aspect_filter:
        by_aspect = {k: v for k, v in by_aspect.items() if k == aspect_filter}
    names = {"F": "Molecular Function", "P": "Biological Process", "C": "Cellular Component"}
    total = sum(len(v) for v in by_aspect.values())
    lines: list[str] = [f"## GO: {accession} ({total} terms)", ""]
    for asp in ("F", "P", "C"):
        terms = by_aspect.get(asp, [])
        if not terms:
            continue
        lines.append(f"### {names[asp]} ({len(terms)})")
        for go_id, term, ev in terms:
            lines.append(f"  {go_id}: {term} [{ev}]")
        lines.append("")
    return "\n".join(lines)


def fmt_crossrefs(
    xrefs: list[Xref],
    accession: str,
    db_filter: str | None,
    fmt: str = "markdown",
) -> str:
    if db_filter:
        xrefs = [x for x in xrefs if str(x.get("database", "")).lower() == db_filter.lower()]
    if fmt == "json":
        return json.dumps(xrefs, indent=2, ensure_ascii=False, default=str)
    by_db: dict[str, list[str]] = {}
    for x in xrefs:
        by_db.setdefault(str(x.get("database", "?")), []).append(str(x.get("id", "")))
    lines: list[str] = [
        f"## Cross-refs: {accession} ({len(by_db)} databases, {len(xrefs)} entries)",
        "",
    ]
    for db in sorted(by_db):
        ids = by_db[db]
        show = ", ".join(ids[:15])
        extra = f" (+{len(ids) - 15} more)" if len(ids) > 15 else ""
        lines.append(f"**{db}** ({len(ids)}): {show}{extra}")
    return "\n".join(lines)


def fmt_variants(features: list[Feature], accession: str, fmt: str = "markdown") -> str:
    variants: list[Feature] = [f for f in features if f.get("type") == "Natural variant"]
    if fmt == "json":
        return json.dumps(variants, indent=2, ensure_ascii=False, default=str)
    lines: list[str] = [f"## Variants: {accession} ({len(variants)})", ""]
    for v in variants[:50]:
        loc = v.get("location", {}) or {}
        pos = loc.get("start", {}).get("value", "?")
        desc = v.get("description", "")
        alt = v.get("alternativeSequence", {}) or {}
        orig = alt.get("originalSequence", "")
        alts: list[str] = alt.get("alternativeSequences", []) or []
        mut = f"{orig}{pos}{'/'.join(alts)}" if orig else f"pos {pos}"
        lines.append(f"  **{mut}**: {desc}" if desc else f"  **{mut}**")
    if len(variants) > 50:
        lines.append(f"  ... (+{len(variants) - 50} more)")
    return "\n".join(lines)


def fmt_idmapping(data: dict[str, Any], fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    results: list[dict[str, Any]] = data.get("results", []) or []
    failed: list[str] = data.get("failedIds", []) or []
    lines: list[str] = [f"## ID Mapping: {len(results)} mapped, {len(failed)} failed", ""]
    for r in results[:50]:
        src = r.get("from", "?")
        tgt = r.get("to", {})
        if isinstance(tgt, dict):
            to_id = tgt.get("primaryAccession", tgt.get("id", str(tgt)))
        else:
            to_id = str(tgt)
        lines.append(f"  {src} -> {to_id}")
    if len(results) > 50:
        lines.append(f"  ... (+{len(results) - 50} more)")
    if failed:
        lines.extend(["", f"**Failed:** {', '.join(failed[:20])}"])
    return "\n".join(lines)


def fmt_taxonomy(data: dict[str, Any], fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"## Taxonomy ({len(results)} results)", ""]
    for r in results:
        tid = r.get("taxonId", "?")
        sci = r.get("scientificName", "?")
        common = r.get("commonName", "")
        rank = r.get("rank", "")
        c = f" ({common})" if common else ""
        lines.append(f"  **{tid}**: {sci}{c} [{rank}]")
    return "\n".join(lines)
