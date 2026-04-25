"""Response formatters: JSON and Markdown output for UniProt data.

Pure functions, no I/O. Strict type hints (mypy strict-compatible).

Every formatter optionally accepts a :class:`Provenance` keyword
argument. When supplied, JSON output is wrapped in a
``{"data": ..., "provenance": ...}`` envelope and Markdown output
gains a trailing ``---``-delimited provenance footer. A dedicated
:func:`fmt_fasta` helper handles the sequence tool, emitting a
PIR-style ``;``-prefixed comment block above the FASTA records so
downstream parsers (BLAST+, biopython, emboss) skip the provenance
cleanly.
"""

from __future__ import annotations

import json
from typing import Any

from uniprot_mcp.client import SOURCE_NAME, Provenance

Entry = dict[str, Any]
Feature = dict[str, Any]
Xref = dict[str, Any]

__all__ = [
    "fmt_crossrefs",
    "fmt_entry",
    "fmt_fasta",
    "fmt_features",
    "fmt_go",
    "fmt_idmapping",
    "fmt_keyword",
    "fmt_keyword_search",
    "fmt_search",
    "fmt_subcellular_location",
    "fmt_subcellular_location_search",
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


def _provenance_md_footer(provenance: Provenance) -> list[str]:
    """Render provenance as trailing Markdown lines.

    Shape:

        ``<blank>``
        ``---``
        ``_Source: UniProt release 2026_02 (2026-03-05) • Retrieved …_``
        ``_Query: https://rest.uniprot.org/…_``

    The emitted block is ≤ 4 lines and uses only plain Markdown so it
    renders identically in every client (Claude Desktop, Cline, raw).
    """
    release = provenance.get("release")
    release_date = provenance.get("release_date")
    retrieved_at = provenance["retrieved_at"]
    url = provenance["url"]

    release_text: str
    if release and release_date:
        release_text = f"{SOURCE_NAME} release {release} ({release_date})"
    elif release:
        release_text = f"{SOURCE_NAME} release {release}"
    else:
        release_text = SOURCE_NAME

    return [
        "",
        "---",
        f"_Source: {release_text} • Retrieved {retrieved_at}_",
        f"_Query: {url}_",
    ]


def _provenance_fasta_header(provenance: Provenance) -> list[str]:
    """Render provenance as PIR-style ``;``-prefixed comment lines.

    Safe for BLAST+, biopython ``SeqIO``, emboss ``seqret``, and any
    parser that follows the NBRF/PIR convention of ignoring lines that
    start with ``;`` before the first ``>`` record.
    """
    release = provenance.get("release")
    release_date = provenance.get("release_date")
    lines: list[str] = [f";Source: {SOURCE_NAME}"]
    if release and release_date:
        lines.append(f";Release: {release} ({release_date})")
    elif release:
        lines.append(f";Release: {release}")
    lines.append(f";Retrieved: {provenance['retrieved_at']}")
    lines.append(f";URL: {provenance['url']}")
    return lines


def _json_envelope(data: Any, provenance: Provenance | None) -> str:
    """Serialize ``data`` as JSON, wrapping in a provenance envelope
    when ``provenance`` is supplied."""
    if provenance is None:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    payload = {"data": data, "provenance": dict(provenance)}
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def fmt_entry(data: Entry, fmt: str = "markdown", *, provenance: Provenance | None = None) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
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
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_search(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
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
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_features(
    features: list[Feature],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    if fmt == "json":
        return _json_envelope(features, provenance)
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
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_go(
    xrefs: list[Xref],
    accession: str,
    aspect_filter: str | None,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    go_refs: list[Xref] = [x for x in xrefs if x.get("database") == "GO"]
    if fmt == "json":
        return _json_envelope(go_refs, provenance)
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
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_crossrefs(
    xrefs: list[Xref],
    accession: str,
    db_filter: str | None,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    if db_filter:
        xrefs = [x for x in xrefs if str(x.get("database", "")).lower() == db_filter.lower()]
    if fmt == "json":
        return _json_envelope(xrefs, provenance)
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
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_variants(
    features: list[Feature],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    variants: list[Feature] = [f for f in features if f.get("type") == "Natural variant"]
    if fmt == "json":
        return _json_envelope(variants, provenance)
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
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_idmapping(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
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
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_taxonomy(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"## Taxonomy ({len(results)} results)", ""]
    for r in results:
        tid = r.get("taxonId", "?")
        sci = r.get("scientificName", "?")
        common = r.get("commonName", "")
        rank = r.get("rank", "")
        c = f" ({common})" if common else ""
        lines.append(f"  **{tid}**: {sci}{c} [{rank}]")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def _kw_id(record: dict[str, Any]) -> str:
    """Pull the canonical keyword id out of either the wrapping object
    or a flat field. Different UniProt endpoints serialize this both
    ways, so handle both shapes defensively."""
    kw = record.get("keyword")
    if isinstance(kw, dict):
        return str(kw.get("id", "?"))
    if isinstance(kw, str) and kw:
        return kw
    return str(record.get("id", "?"))


def _kw_name(record: dict[str, Any]) -> str:
    kw = record.get("keyword")
    if isinstance(kw, dict):
        return str(kw.get("name", record.get("name", "?")))
    return str(record.get("name", "?"))


def fmt_keyword(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    """Format a single UniProt keyword (e.g. KW-0007 Acetylation)."""
    if fmt == "json":
        return _json_envelope(data, provenance)
    kid = _kw_id(data)
    name = _kw_name(data)
    category = str(data.get("category", "") or "")
    definition = str(data.get("definition", "") or "")
    synonyms = [str(s) for s in (data.get("synonyms") or []) if s]
    parents = data.get("parents") or []
    children = data.get("children") or []
    go_refs = data.get("geneOntologies") or []
    stats = data.get("statistics") or {}
    lines: list[str] = [f"## {kid}: {name}", ""]
    if category:
        lines.append(f"**Category:** {category}")
    if definition:
        lines.append(f"**Definition:** {definition}")
    if synonyms:
        show = ", ".join(synonyms[:8])
        extra = f" (+{len(synonyms) - 8} more)" if len(synonyms) > 8 else ""
        lines.append(f"**Synonyms:** {show}{extra}")
    if parents:
        names = [_kw_name(p) for p in parents[:5]]
        lines.append(f"**Parents:** {', '.join(n for n in names if n != '?')}")
    if children:
        lines.append(f"**Children:** {len(children)} narrower keyword(s)")
    if go_refs:
        ids = [str(g.get("id", "")) for g in go_refs if g.get("id")]
        if ids:
            lines.append(f"**GO:** {', '.join(ids[:5])}")
    if stats:
        rev = stats.get("reviewedProteinCount")
        unrev = stats.get("unreviewedProteinCount")
        if rev is not None or unrev is not None:
            lines.append(f"**Proteins annotated:** {rev or 0} reviewed, {unrev or 0} unreviewed")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_keyword_search(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"**{len(results)} keywords**", ""]
    for r in results[:50]:
        kid = _kw_id(r)
        name = _kw_name(r)
        cat = str(r.get("category", "") or "")
        suffix = f" [{cat}]" if cat else ""
        lines.append(f"- **{kid}**: {name}{suffix}")
    if len(results) > 50:
        lines.append(f"... (+{len(results) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_subcellular_location(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    """Format a single UniProt subcellular location (e.g. SL-0086 Cell membrane)."""
    if fmt == "json":
        return _json_envelope(data, provenance)
    sid = str(data.get("id", "?") or "?")
    name = str(data.get("name", "?") or "?")
    category = str(data.get("category", "") or "")
    definition = str(data.get("definition", "") or "")
    synonyms = [str(s) for s in (data.get("synonyms") or []) if s]
    keyword = data.get("keyword") or {}
    is_a = data.get("isA") or []
    is_part_of = data.get("isPartOf") or []
    parts = data.get("parts") or []
    go_refs = data.get("geneOntologies") or []
    stats = data.get("statistics") or {}
    lines: list[str] = [f"## {sid}: {name}", ""]
    if category:
        lines.append(f"**Category:** {category}")
    if definition:
        lines.append(f"**Definition:** {definition}")
    if synonyms:
        show = ", ".join(synonyms[:8])
        extra = f" (+{len(synonyms) - 8} more)" if len(synonyms) > 8 else ""
        lines.append(f"**Synonyms:** {show}{extra}")
    if isinstance(keyword, dict) and keyword.get("id"):
        lines.append(f"**Keyword:** {keyword['id']} ({keyword.get('name', '')})")
    if is_a:
        names = [str(p.get("name", "")) for p in is_a[:5] if p.get("name")]
        if names:
            lines.append(f"**Is-a:** {', '.join(names)}")
    if is_part_of:
        names = [str(p.get("name", "")) for p in is_part_of[:5] if p.get("name")]
        if names:
            lines.append(f"**Part of:** {', '.join(names)}")
    if parts:
        lines.append(f"**Has parts:** {len(parts)}")
    if go_refs:
        ids = [str(g.get("id", "")) for g in go_refs if g.get("id")]
        if ids:
            lines.append(f"**GO:** {', '.join(ids[:5])}")
    if stats:
        rev = stats.get("reviewedProteinCount")
        unrev = stats.get("unreviewedProteinCount")
        if rev is not None or unrev is not None:
            lines.append(f"**Proteins annotated:** {rev or 0} reviewed, {unrev or 0} unreviewed")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_subcellular_location_search(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"**{len(results)} subcellular locations**", ""]
    for r in results[:50]:
        sid = str(r.get("id", "?") or "?")
        name = str(r.get("name", "?") or "?")
        cat = str(r.get("category", "") or "")
        suffix = f" [{cat}]" if cat else ""
        lines.append(f"- **{sid}**: {name}{suffix}")
    if len(results) > 50:
        lines.append(f"... (+{len(results) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_fasta(fasta_text: str, *, provenance: Provenance | None = None) -> str:
    """Return a FASTA string with an optional PIR-style provenance block.

    The provenance block is placed *before* the first ``>`` record so
    strict parsers that only tokenize records starting with ``>`` (BLAST+,
    UniProt-style pipelines) ignore it. Permissive parsers that honour
    the PIR convention (biopython, emboss) explicitly skip ``;``-prefixed
    lines.
    """
    if provenance is None:
        return fasta_text
    header = "\n".join(_provenance_fasta_header(provenance))
    # Guarantee exactly one separating newline so the concatenation is
    # well-formed regardless of whether `fasta_text` already ended in \n.
    sep = "" if fasta_text.startswith("\n") else "\n"
    return header + sep + fasta_text
