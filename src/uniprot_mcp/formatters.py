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
    "fmt_alphafold",
    "fmt_alphafold_confidence",
    "fmt_chembl",
    "fmt_citation",
    "fmt_citation_search",
    "fmt_crossrefs",
    "fmt_disease_associations",
    "fmt_entry",
    "fmt_fasta",
    "fmt_features",
    "fmt_features_at_position",
    "fmt_go",
    "fmt_idmapping",
    "fmt_interpro",
    "fmt_keyword",
    "fmt_keyword_search",
    "fmt_orthology",
    "fmt_pdb",
    "fmt_properties",
    "fmt_proteome",
    "fmt_proteome_search",
    "fmt_publications",
    "fmt_search",
    "fmt_subcellular_location",
    "fmt_subcellular_location_search",
    "fmt_target_dossier",
    "fmt_taxonomy",
    "fmt_uniparc",
    "fmt_uniparc_search",
    "fmt_uniref",
    "fmt_uniref_search",
    "fmt_variant_lookup",
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
        ``_SHA-256: <64 hex chars>_``

    The emitted block uses only plain Markdown so it renders identically
    in every client (Claude Desktop, Cline, raw). The SHA-256 line is
    the input to ``uniprot_provenance_verify`` for byte-level audit.
    """
    release = provenance.get("release")
    release_date = provenance.get("release_date")
    retrieved_at = provenance["retrieved_at"]
    url = provenance["url"]
    response_sha256 = provenance.get("response_sha256", "")

    release_text: str
    if release and release_date:
        release_text = f"{SOURCE_NAME} release {release} ({release_date})"
    elif release:
        release_text = f"{SOURCE_NAME} release {release}"
    else:
        release_text = SOURCE_NAME

    lines = [
        "",
        "---",
        f"_Source: {release_text} • Retrieved {retrieved_at}_",
        f"_Query: {url}_",
    ]
    if response_sha256:
        lines.append(f"_SHA-256: {response_sha256}_")
    return lines


def _provenance_fasta_header(provenance: Provenance) -> list[str]:
    """Render provenance as PIR-style ``;``-prefixed comment lines.

    Safe for BLAST+, biopython ``SeqIO``, emboss ``seqret``, and any
    parser that follows the NBRF/PIR convention of ignoring lines that
    start with ``;`` before the first ``>`` record.
    """
    release = provenance.get("release")
    release_date = provenance.get("release_date")
    response_sha256 = provenance.get("response_sha256", "")
    lines: list[str] = [f";Source: {SOURCE_NAME}"]
    if release and release_date:
        lines.append(f";Release: {release} ({release_date})")
    elif release:
        lines.append(f";Release: {release}")
    lines.append(f";Retrieved: {provenance['retrieved_at']}")
    lines.append(f";URL: {provenance['url']}")
    if response_sha256:
        lines.append(f";SHA-256: {response_sha256}")
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
    """Format a single UniProt subcellular location (e.g. SL-0039 Cell membrane,
    SL-0086 Cytoplasm, SL-0191 Nucleus)."""
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


def _uniref_tier(record: dict[str, Any]) -> str:
    """Extract the identity tier (50 / 90 / 100) from a UniRef record.

    UniRef encodes the tier in two places: the cluster ID prefix and
    the ``entryType`` field. Prefer the field, fall back to the prefix,
    return ``"?"`` if neither is available.
    """
    entry_type = str(record.get("entryType", "") or "")
    for tier in ("100", "90", "50"):
        if tier in entry_type:
            return tier
    cluster_id = str(record.get("id", "") or "")
    for tier in ("100", "90", "50"):
        if cluster_id.startswith(f"UniRef{tier}_"):
            return tier
    return "?"


def _uniref_representative(record: dict[str, Any]) -> str:
    """Return a short label for the cluster's representative member,
    e.g. ``"P04637 (TP53_HUMAN)"`` or just the accession if the
    Swiss-Prot mnemonic is absent."""
    rep = record.get("representativeMember") or {}
    if not isinstance(rep, dict):
        return ""
    acc = str(rep.get("memberId", "") or rep.get("accession", "") or "")
    name = str(rep.get("uniprotKBId", "") or rep.get("uniProtKBId", "") or "")
    if acc and name:
        return f"{acc} ({name})"
    return acc or name or ""


def fmt_uniref(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    """Format a single UniRef cluster (e.g. UniRef50_P04637)."""
    if fmt == "json":
        return _json_envelope(data, provenance)
    cid = str(data.get("id", "?") or "?")
    name = str(data.get("name", "") or "").strip()
    tier = _uniref_tier(data)
    rep = _uniref_representative(data)
    member_count = data.get("memberCount", data.get("memberCounts", {}).get("total"))
    common_taxon = data.get("commonTaxon") or {}
    last_updated = str(data.get("updated", "") or data.get("lastUpdated", "") or "")
    members = data.get("members") or []

    title = f"## {cid}" if not name else f"## {cid}: {name}"
    lines: list[str] = [title, ""]
    if tier != "?":
        lines.append(f"**Identity tier:** {tier}%")
    if rep:
        lines.append(f"**Representative:** {rep}")
    if member_count is not None:
        lines.append(f"**Member count:** {member_count}")
    if isinstance(common_taxon, dict) and common_taxon.get("scientificName"):
        tid = common_taxon.get("taxonId")
        suffix = f" (taxId {tid})" if tid is not None else ""
        lines.append(f"**Common taxon:** {common_taxon['scientificName']}{suffix}")
    if last_updated:
        lines.append(f"**Last updated:** {last_updated}")
    if members:
        sample = []
        for m in members[:20]:
            acc = m.get("memberId") or m.get("accession") or "" if isinstance(m, dict) else str(m)
            if acc:
                sample.append(str(acc))
        if sample:
            shown = ", ".join(sample)
            extra = f" (+{len(members) - 20} more)" if len(members) > 20 else ""
            lines.append(f"**Members:** {shown}{extra}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_uniref_search(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"**{len(results)} UniRef clusters**", ""]
    for r in results[:50]:
        cid = str(r.get("id", "?") or "?")
        name = str(r.get("name", "") or "").strip()
        tier = _uniref_tier(r)
        member_count = r.get("memberCount", "?")
        rep = _uniref_representative(r)
        bits: list[str] = []
        if tier != "?":
            bits.append(f"{tier}%")
        bits.append(f"{member_count} members")
        if rep:
            bits.append(f"rep {rep}")
        suffix = " | ".join(bits)
        head = f"**{cid}**"
        if name:
            head = f"{head}: {name}"
        lines.append(f"- {head}  —  {suffix}")
    if len(results) > 50:
        lines.append(f"... (+{len(results) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_uniparc(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    """Format a single UniParc record (e.g. UPI000002ED67)."""
    if fmt == "json":
        return _json_envelope(data, provenance)
    upi = str(data.get("uniParcId", "?") or "?")
    seq = data.get("sequence", {}) or {}
    length = seq.get("length", "?")
    mw = seq.get("molWeight", "?")
    md5 = seq.get("md5", "")
    crc64 = seq.get("crc64", "")
    xref_count = data.get("crossReferenceCount", "?")
    oldest = data.get("oldestCrossRefCreated", "")
    latest = data.get("mostRecentCrossRefUpdated", "")
    accessions = data.get("uniProtKBAccessions") or []
    common_taxons = data.get("commonTaxons") or []

    lines: list[str] = [f"## {upi}", ""]
    lines.append(f"**Length:** {length} aa | **Mass:** {mw} Da")
    if md5 or crc64:
        bits = []
        if md5:
            bits.append(f"md5 `{md5}`")
        if crc64:
            bits.append(f"crc64 `{crc64}`")
        lines.append("**Checksums:** " + ", ".join(bits))
    lines.append(f"**Cross-reference records:** {xref_count}")
    if oldest:
        lines.append(f"**Oldest cross-ref:** {oldest}")
    if latest:
        lines.append(f"**Most recent cross-ref:** {latest}")
    if accessions:
        show = ", ".join(str(a) for a in accessions[:10])
        extra = f" (+{len(accessions) - 10} more)" if len(accessions) > 10 else ""
        lines.append(f"**Linked UniProtKB accessions:** {show}{extra}")
    if common_taxons:
        names = [
            str(t.get("scientificName", "")) for t in common_taxons[:5] if t.get("scientificName")
        ]
        if names:
            lines.append(f"**Common taxa:** {', '.join(names)}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_uniparc_search(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"**{len(results)} UniParc records**", ""]
    for r in results[:50]:
        upi = str(r.get("uniParcId", "?") or "?")
        length = (r.get("sequence") or {}).get("length", "?")
        xref_count = r.get("crossReferenceCount", "?")
        lines.append(f"- **{upi}**  —  {length} aa | {xref_count} cross-refs")
    if len(results) > 50:
        lines.append(f"... (+{len(results) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_proteome(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    """Format a single UniProt proteome (e.g. UP000005640 = human)."""
    if fmt == "json":
        return _json_envelope(data, provenance)
    upid = str(data.get("id", "?") or "?")
    description = str(data.get("description", "") or "").strip()
    proteome_type = str(data.get("proteomeType", "") or "")
    superkingdom = str(data.get("superkingdom", "") or "")
    tax = data.get("taxonomy") or {}
    organism = str(tax.get("scientificName", "")) if isinstance(tax, dict) else ""
    taxon_id = tax.get("taxonId") if isinstance(tax, dict) else None
    protein_count = data.get("proteinCount", "?")
    gene_count = data.get("geneCount", "?")
    components = data.get("components") or []
    modified = str(data.get("modified", "") or "")
    annotation_score = data.get("annotationScore")
    completeness = data.get("proteomeCompletenessReport") or {}
    busco = (completeness.get("buscoReport") or {}) if isinstance(completeness, dict) else {}

    title = f"## {upid}: {organism}" if organism else f"## {upid}"
    lines: list[str] = [title, ""]
    if description:
        lines.append(f"**Description:** {description[:300]}")
    if proteome_type:
        lines.append(f"**Type:** {proteome_type}")
    if organism:
        suffix = f" (taxId {taxon_id})" if taxon_id is not None else ""
        lines.append(f"**Organism:** {organism}{suffix}")
    if superkingdom:
        lines.append(f"**Superkingdom:** {superkingdom}")
    lines.append(f"**Protein count:** {protein_count}")
    if gene_count not in ("?", None):
        lines.append(f"**Gene count:** {gene_count}")
    if annotation_score is not None:
        lines.append(f"**Annotation score:** {annotation_score} / 5")
    if isinstance(busco, dict) and busco.get("score") is not None:
        lines.append(f"**BUSCO completeness:** {busco['score']} %")
    if components:
        lines.append(f"**Components:** {len(components)}")
        names = [str(c.get("name", "")) for c in components[:10] if c.get("name")]
        if names:
            extra = f" (+{len(components) - 10} more)" if len(components) > 10 else ""
            lines.append("  " + ", ".join(names) + extra)
    if modified:
        lines.append(f"**Last modified:** {modified}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_proteome_search(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"**{len(results)} proteomes**", ""]
    for r in results[:50]:
        upid = str(r.get("id", "?") or "?")
        tax = r.get("taxonomy") or {}
        organism = str(tax.get("scientificName", "")) if isinstance(tax, dict) else ""
        protein_count = r.get("proteinCount", "?")
        proteome_type = str(r.get("proteomeType", "") or "")
        bits = []
        if protein_count != "?":
            bits.append(f"{protein_count} proteins")
        if proteome_type:
            bits.append(proteome_type)
        suffix = f"  —  {' | '.join(bits)}" if bits else ""
        head = f"**{upid}**"
        if organism:
            head = f"{head}: {organism}"
        lines.append(f"- {head}{suffix}")
    if len(results) > 50:
        lines.append(f"... (+{len(results) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_citation(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    """Format a single UniProt citation record."""
    if fmt == "json":
        return _json_envelope(data, provenance)
    citation = data.get("citation") or data
    cid = str(
        citation.get("id", citation.get("citationCrossReferences", [{}])[0].get("id", "?")) or "?"
    )
    title = str(citation.get("title", "") or "").strip()
    authors = citation.get("authors") or []
    journal = str(citation.get("journal", "") or "")
    year = citation.get("publicationDate") or citation.get("year") or ""
    volume = citation.get("volume") or ""
    pages = (citation.get("firstPage") or "") + (
        f"-{citation.get('lastPage', '')}" if citation.get("lastPage") else ""
    )
    cross_refs = citation.get("citationCrossReferences") or []

    lines: list[str] = [f"## Citation {cid}", ""]
    if title:
        lines.append(f"**Title:** {title}")
    if authors:
        sample = ", ".join(str(a) for a in authors[:6])
        more = f" (+{len(authors) - 6} more)" if len(authors) > 6 else ""
        lines.append(f"**Authors:** {sample}{more}")
    if journal:
        bits: list[str] = [journal]
        if year:
            bits.append(str(year))
        if volume:
            bits.append(f"vol. {volume}")
        if pages.strip("-"):
            bits.append(pages)
        lines.append(f"**Source:** {', '.join(bits)}")
    if cross_refs:
        names = [f"{x.get('database', '?')}:{x.get('id', '?')}" for x in cross_refs[:5]]
        lines.append(f"**Cross-refs:** {', '.join(names)}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_citation_search(
    data: dict[str, Any], fmt: str = "markdown", *, provenance: Provenance | None = None
) -> str:
    if fmt == "json":
        return _json_envelope(data, provenance)
    results: list[dict[str, Any]] = data.get("results", []) or []
    lines: list[str] = [f"**{len(results)} citations**", ""]
    for r in results[:50]:
        c = r.get("citation") or r
        cid = str(
            c.get("id") or (c.get("citationCrossReferences", [{}]) or [{}])[0].get("id", "?") or "?"
        )
        title = str(c.get("title", "") or "").strip()
        year = c.get("publicationDate") or c.get("year") or ""
        head = f"**{cid}**"
        if year:
            head = f"{head} ({year})"
        if title:
            head = f"{head}: {title[:140]}"
        lines.append(f"- {head}")
    if len(results) > 50:
        lines.append(f"... (+{len(results) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def _xrefs_for_db(data: dict[str, Any], database: str) -> list[Xref]:
    return [
        x for x in (data.get("uniProtKBCrossReferences") or []) if x.get("database") == database
    ]


def _xref_props(xref: Xref) -> dict[str, str]:
    return {str(p.get("key", "")): str(p.get("value", "")) for p in (xref.get("properties") or [])}


def fmt_pdb(
    data: dict[str, Any],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Resolve every PDB cross-reference recorded on a UniProt entry into
    structured fields (PDB ID, method, resolution, chain coverage)."""
    pdbs = _xrefs_for_db(data, "PDB")
    if fmt == "json":
        structured = [
            {
                "pdb_id": x.get("id"),
                "method": _xref_props(x).get("Method"),
                "resolution": _xref_props(x).get("Resolution"),
                "chains": _xref_props(x).get("Chains"),
            }
            for x in pdbs
        ]
        return _json_envelope({"accession": accession, "pdb": structured}, provenance)
    lines: list[str] = [f"## PDB structures for {accession} ({len(pdbs)})", ""]
    for x in pdbs[:50]:
        props = _xref_props(x)
        method = props.get("Method", "?")
        resolution = props.get("Resolution", "")
        chains = props.get("Chains", "")
        bits: list[str] = [method]
        if resolution:
            bits.append(resolution)
        if chains:
            bits.append(f"chains {chains}")
        lines.append(f"- **{x.get('id', '?')}**  —  {' | '.join(bits)}")
    if len(pdbs) > 50:
        lines.append(f"... (+{len(pdbs) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_alphafold(
    data: dict[str, Any],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Resolve the AlphaFoldDB cross-reference. UniProt typically carries
    one AlphaFold entry per accession (the canonical model)."""
    afs = _xrefs_for_db(data, "AlphaFoldDB")
    if fmt == "json":
        structured = [{"alphafold_id": x.get("id"), **_xref_props(x)} for x in afs]
        return _json_envelope({"accession": accession, "alphafold": structured}, provenance)
    lines: list[str] = [f"## AlphaFold models for {accession} ({len(afs)})", ""]
    for x in afs:
        af_id = x.get("id", "?")
        lines.append(f"- **{af_id}**  —  https://alphafold.ebi.ac.uk/entry/{af_id}")
    if not afs:
        lines.append("_No AlphaFold cross-reference on this entry._")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_interpro(
    data: dict[str, Any],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Resolve InterPro cross-references into structured signatures with
    descriptions when present."""
    iprs = _xrefs_for_db(data, "InterPro")
    if fmt == "json":
        structured = [
            {
                "interpro_id": x.get("id"),
                "name": _xref_props(x).get("EntryName"),
            }
            for x in iprs
        ]
        return _json_envelope({"accession": accession, "interpro": structured}, provenance)
    lines: list[str] = [f"## InterPro signatures for {accession} ({len(iprs)})", ""]
    for x in iprs[:50]:
        ipr_id = x.get("id", "?")
        name = _xref_props(x).get("EntryName", "")
        lines.append(f"- **{ipr_id}**  —  {name}" if name else f"- **{ipr_id}**")
    if len(iprs) > 50:
        lines.append(f"... (+{len(iprs) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_chembl(
    data: dict[str, Any],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Resolve ChEMBL cross-references (drug-target identifiers)."""
    chembls = _xrefs_for_db(data, "ChEMBL")
    if fmt == "json":
        structured = [{"chembl_id": x.get("id"), **_xref_props(x)} for x in chembls]
        return _json_envelope({"accession": accession, "chembl": structured}, provenance)
    lines: list[str] = [f"## ChEMBL targets for {accession} ({len(chembls)})", ""]
    for x in chembls[:50]:
        chembl_id = x.get("id", "?")
        lines.append(
            f"- **{chembl_id}**  —  https://www.ebi.ac.uk/chembl/target_report_card/{chembl_id}/"
        )
    if not chembls:
        lines.append(
            "_No ChEMBL cross-reference on this entry — protein may not be a documented drug target._"
        )
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


_ORTHOLOGY_DB_LABELS: dict[str, str] = {
    "KEGG": "KEGG Orthology",
    "OMA": "OMA Browser (orthologs only)",
    "OrthoDB": "OrthoDB hierarchical clusters",
    "eggNOG": "eggNOG orthologous groups",
    "HOGENOM": "HOGENOM (Bact/Arch ortholog families)",
    "PhylomeDB": "PhylomeDB phylogeny-based orthologs",
    "InParanoid": "InParanoid pairwise orthologs",
    "TreeFam": "TreeFam (curated tree families)",
    "GeneTree": "Ensembl Compara GeneTree",
    "PAN-GO": "Phylogenetic Annotation of GO terms",
    "PANTHER": "PANTHER family / subfamily classification",
    "OrthoInspector": "OrthoInspector-derived orthologs",
}


def fmt_orthology(
    grouped: dict[str, list[str]],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Render orthology cross-references grouped by database.

    Different orthology databases use different inference methods;
    surfacing them side-by-side lets the agent reason about consensus
    (e.g. KEGG and OrthoDB agreeing). The label dict above carries a
    short description of each method so the user can interpret the
    grouping rather than just see opaque IDs.
    """
    if fmt == "json":
        return _json_envelope({"accession": accession, "orthology": grouped}, provenance)
    total = sum(len(ids) for ids in grouped.values())
    lines: list[str] = [
        f"## Orthology: {accession} ({len(grouped)} database(s), {total} cross-ref(s))",
        "",
    ]
    if not grouped:
        lines.append(
            "_No orthology cross-references on this entry. "
            "If a closely-related species ortholog is needed, try OMA / OrthoDB / "
            "Ensembl Compara directly._"
        )
    else:
        for db in sorted(grouped):
            ids = grouped[db]
            label = _ORTHOLOGY_DB_LABELS.get(db, db)
            shown = ", ".join(ids[:8])
            extra = f" (+{len(ids) - 8} more)" if len(ids) > 8 else ""
            lines.append(f"### {db} — {label}")
            lines.append(f"{shown}{extra}")
            lines.append("")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_target_dossier(
    dossier: dict[str, Any],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """One-call comprehensive target characterisation. Built by composing
    seven lookups against the same UniProt entry plus one FASTA fetch
    for derived chemistry. Section headings:

      Identity / Function / Sequence chemistry / Structural evidence /
      Drug-target context / Disease associations / Variants /
      Functional annotations / Cross-references summary
    """
    if fmt == "json":
        return _json_envelope({"accession": accession, "dossier": dossier}, provenance)
    lines: list[str] = [
        f"# Target dossier: {accession}",
        "",
        "_Comprehensive single-call characterisation. "
        "Each section is a structured view of the UniProt entry.  Provenance "
        "footer carries the underlying entry's release tag and SHA-256._",
        "",
    ]

    # === Identity ===
    identity = dossier.get("identity") or {}
    lines.append("## Identity")
    if identity.get("name"):
        lines.append(f"**Protein:** {identity['name']}")
    if identity.get("gene"):
        lines.append(f"**Gene:** {identity['gene']}")
    if identity.get("organism"):
        lines.append(f"**Organism:** {identity['organism']}")
    if identity.get("length") is not None:
        lines.append(f"**Length:** {identity['length']} aa")
    if identity.get("reviewed"):
        lines.append(f"**Curation:** {identity['reviewed']}")
    if identity.get("entry_id"):
        lines.append(f"**Entry ID:** {identity['entry_id']}")
    lines.append("")

    # === Function ===
    function = dossier.get("function") or ""
    if function:
        lines.append("## Function")
        lines.append(str(function)[:600])
        lines.append("")

    # === Sequence chemistry ===
    chem = dossier.get("chemistry") or {}
    if chem:
        lines.append("## Sequence chemistry (derived)")
        if chem.get("molecular_weight") is not None:
            lines.append(f"- Molecular weight: {chem['molecular_weight']:.1f} Da")
        if chem.get("theoretical_pi") is not None:
            lines.append(f"- Theoretical pI: {chem['theoretical_pi']:.2f}")
        if chem.get("gravy") is not None:
            lines.append(f"- GRAVY: {chem['gravy']:+.3f}")
        if chem.get("aromaticity") is not None:
            lines.append(f"- Aromaticity (F+W+Y): {chem['aromaticity'] * 100:.1f}%")
        if chem.get("net_charge_pH7") is not None:
            lines.append(f"- Net charge at pH 7: {chem['net_charge_pH7']:+.1f}")
        if chem.get("extinction_coefficient_280nm") is not None:
            lines.append(
                f"- Extinction coefficient (280 nm): "
                f"{chem['extinction_coefficient_280nm']} M⁻¹·cm⁻¹"
            )
        lines.append("")

    # === Structural evidence ===
    structure = dossier.get("structure") or {}
    if structure:
        lines.append("## Structural evidence")
        n_pdb = structure.get("pdb_count") or 0
        if n_pdb:
            best = structure.get("best_pdb") or {}
            tail = ""
            if best.get("id"):
                tail = (
                    f" (best: {best['id']}"
                    f"{', ' + best['method'] if best.get('method') else ''}"
                    f"{', ' + best['resolution'] if best.get('resolution') else ''}"
                    ")"
                )
            lines.append(f"- PDB structures: {n_pdb}{tail}")
        else:
            lines.append("- PDB structures: 0 (no experimental structure on file)")
        af_id = structure.get("alphafold_model_id")
        if af_id:
            lines.append(
                f"- AlphaFold model: `{af_id}` "
                f"(call `uniprot_get_alphafold_confidence` for pLDDT bands)"
            )
        else:
            lines.append("- AlphaFold model: not cross-referenced from UniProt")
        n_interpro = structure.get("interpro_count") or 0
        if n_interpro:
            lines.append(f"- InterPro signatures: {n_interpro}")
        lines.append("")

    # === Drug-target context ===
    drug = dossier.get("drug_target") or {}
    if drug:
        lines.append("## Drug-target context")
        chembls = drug.get("chembl_ids") or []
        if chembls:
            shown = ", ".join(chembls[:5])
            extra = f" (+{len(chembls) - 5} more)" if len(chembls) > 5 else ""
            lines.append(f"- ChEMBL targets: {shown}{extra}")
        else:
            lines.append("- ChEMBL targets: none — no documented bioactivity data on this protein")
        if drug.get("drugbank_count") is not None:
            lines.append(f"- DrugBank cross-references: {drug['drugbank_count']}")
        lines.append("")

    # === Disease associations ===
    diseases = dossier.get("diseases") or []
    if diseases:
        lines.append(f"## Disease associations ({len(diseases)})")
        for d in diseases[:10]:
            name = d.get("name", "?")
            mim = d.get("mim_id")
            tail = f" (MIM:{mim})" if mim else ""
            lines.append(f"- **{name}**{tail}")
        if len(diseases) > 10:
            lines.append(f"- ... (+{len(diseases) - 10} more)")
        lines.append("")

    # === Variants ===
    variants = dossier.get("variants") or {}
    if variants:
        lines.append("## Variants")
        n = variants.get("count") or 0
        lines.append(f"- Natural variants annotated: {n}")
        lines.append("")

    # === Functional annotations ===
    func = dossier.get("functional_annotations") or {}
    if func:
        lines.append("## Functional annotations")
        if func.get("go_molecular_function"):
            lines.append("**GO Molecular Function:**")
            for term in func["go_molecular_function"][:5]:
                lines.append(f"- {term}")
        if func.get("subcellular_locations"):
            lines.append("**Subcellular locations:**")
            for loc in func["subcellular_locations"][:5]:
                lines.append(f"- {loc}")
        if func.get("evidence_distinct_codes") is not None:
            lines.append(
                f"**Evidence codes:** {func['evidence_distinct_codes']} distinct ECO codes "
                f"(call `uniprot_get_evidence_summary` for the full breakdown)"
            )
        lines.append("")

    # === Cross-references summary ===
    xref = dossier.get("cross_reference_summary") or {}
    if xref:
        lines.append("## Cross-references")
        lines.append(
            f"- {xref.get('total', 0)} cross-references across "
            f"{xref.get('database_count', 0)} databases"
        )
        if xref.get("top_databases"):
            lines.append(f"- Top databases: {', '.join(xref['top_databases'][:8])}")
        lines.append("")

    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_alphafold_confidence(
    record: dict[str, Any],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Format the AlphaFold pLDDT-confidence summary.

    The AlphaFold prediction-metadata endpoint already aggregates pLDDT
    into four bands (``fractionPlddtVeryHigh``, ``fractionPlddtConfident``,
    ``fractionPlddtLow``, ``fractionPlddtVeryLow``) plus the global mean
    in ``globalMetricValue``. We surface these directly so the agent can
    answer 'can I trust this model?' without parsing the structure file.

    pLDDT band semantics (per the AlphaFold-DB FAQ):
      pLDDT ≥ 90    very high   (model very likely correct)
      70 ≤ pLDDT < 90  confident   (well-modelled core)
      50 ≤ pLDDT < 70  low         (low confidence; surface or flexible)
      pLDDT < 50    very low    (treat as disordered)
    """
    if fmt == "json":
        return _json_envelope({"accession": accession, "alphafold": record}, provenance)
    if not record:
        lines: list[str] = [f"## AlphaFold confidence: {accession}", ""]
        lines.append("_No AlphaFold model found for this accession._")
        if provenance is not None:
            lines.extend(_provenance_md_footer(provenance))
        return "\n".join(lines)

    entry_id = str(record.get("entryId", "?") or "?")
    organism = str(record.get("organismScientificName", "") or "")
    gene = str(record.get("gene", "") or "")
    version = record.get("latestVersion")
    seq_end = record.get("uniprotEnd") or record.get("sequenceEnd")
    global_mean = record.get("globalMetricValue")
    f_very_high = record.get("fractionPlddtVeryHigh")
    f_confident = record.get("fractionPlddtConfident")
    f_low = record.get("fractionPlddtLow")
    f_very_low = record.get("fractionPlddtVeryLow")
    cif_url = str(record.get("cifUrl", "") or "")
    pdb_url = str(record.get("pdbUrl", "") or "")
    pae_image_url = str(record.get("paeImageUrl", "") or "")

    title_extra = f": {organism}" if organism else ""
    lines = [f"## AlphaFold confidence — {entry_id}{title_extra}", ""]
    if gene:
        lines.append(f"**Gene:** {gene}")
    if seq_end is not None:
        lines.append(f"**Residues modelled:** 1-{seq_end}")
    if version is not None:
        lines.append(f"**Model version:** v{version}")

    if global_mean is not None:
        try:
            band_label = _plddt_band(float(global_mean))
        except (TypeError, ValueError):
            band_label = "?"
        lines.append(
            f"**Global pLDDT (mean):** {global_mean:.1f}  ({band_label})"
            if isinstance(global_mean, (int, float))
            else f"**Global pLDDT (mean):** {global_mean}"
        )

    bands_present = any(f is not None for f in (f_very_high, f_confident, f_low, f_very_low))
    if bands_present:
        lines.extend(["", "**pLDDT band distribution:**"])
        for label, frac in (
            ("Very high (≥ 90)", f_very_high),
            ("Confident (70-90)", f_confident),
            ("Low (50-70)", f_low),
            ("Very low (< 50)", f_very_low),
        ):
            if isinstance(frac, (int, float)):
                lines.append(f"- {label}: {frac * 100:5.1f}%")
            elif frac is not None:
                lines.append(f"- {label}: {frac}")

    if cif_url:
        lines.extend(["", f"**CIF:** {cif_url}"])
    if pdb_url:
        lines.append(f"**PDB:** {pdb_url}")
    if pae_image_url:
        lines.append(f"**PAE image:** {pae_image_url}")

    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def _plddt_band(score: float) -> str:
    """Map a pLDDT score to its semantic band label."""
    if score >= 90:
        return "very high"
    if score >= 70:
        return "confident"
    if score >= 50:
        return "low"
    return "very low"


def fmt_publications(
    publications: list[dict[str, Any]],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Render the structured publication list extracted from a UniProt
    entry's ``references`` block."""
    if fmt == "json":
        return _json_envelope({"accession": accession, "publications": publications}, provenance)
    lines: list[str] = [
        f"## Publications cited by {accession} ({len(publications)} reference(s))",
        "",
    ]
    if not publications:
        lines.append("_No publications listed on this entry._")
    else:
        for p in publications[:50]:
            title = str(p.get("title", "") or "").strip()
            authors = p.get("authors") or []
            year = p.get("year") or ""
            journal = str(p.get("journal", "") or "")
            pmid = p.get("pubmed_id") or ""
            doi = p.get("doi") or ""
            head_bits: list[str] = []
            if pmid:
                head_bits.append(f"PMID:{pmid}")
            if doi:
                head_bits.append(f"doi:{doi}")
            if year:
                head_bits.append(str(year))
            head = " · ".join(head_bits) if head_bits else "(no identifier)"
            lines.append(f"### {head}")
            if title:
                lines.append(f"_{title}_")
            if authors:
                sample = ", ".join(str(a) for a in authors[:6])
                more = f" (+{len(authors) - 6} more)" if len(authors) > 6 else ""
                lines.append(f"{sample}{more}")
            if journal:
                lines.append(journal)
            positions = p.get("reference_positions") or []
            if positions:
                lines.append(f"**Cited for:** {'; '.join(str(x) for x in positions[:3])}")
            lines.append("")
        if len(publications) > 50:
            lines.append(f"... (+{len(publications) - 50} more)")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_properties(
    data: dict[str, Any],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Format the derived sequence-chemistry record produced by
    :func:`compute_protein_properties`."""
    if fmt == "json":
        return _json_envelope({"accession": accession, "properties": data}, provenance)
    lines: list[str] = [f"## Sequence properties: {accession}", ""]
    lines.append(f"**Length:** {data['length']} residues")
    lines.append(f"**Molecular weight:** {data['molecular_weight']:.1f} Da")
    lines.append(f"**Theoretical pI:** {data['theoretical_pi']:.2f}")
    lines.append(
        f"**Net charge at pH 7:** {data['net_charge_pH7']:+.1f} "
        f"(positive = basic, negative = acidic)"
    )
    lines.append(
        f"**GRAVY (Kyte-Doolittle hydropathy):** {data['gravy']:+.3f} "
        f"({'hydrophobic' if data['gravy'] > 0 else 'hydrophilic'})"
    )
    lines.append(f"**Aromatic fraction (F+W+Y):** {data['aromaticity'] * 100:.1f}%")
    e280 = data.get("extinction_coefficient_280nm")
    if e280 is not None:
        lines.append(
            f"**Extinction coefficient at 280 nm:** {e280} M⁻¹·cm⁻¹ "
            f"(1490·#Trp + 5500·#Tyr; assumes reduced cysteines)"
        )
    counts = data.get("amino_acid_counts") or {}
    if counts:
        ordered = ", ".join(f"{aa}:{counts[aa]}" for aa in sorted(counts) if counts[aa] > 0)
        lines.append("")
        lines.append(f"**Amino acid composition:** {ordered}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_features_at_position(
    features: list[Feature],
    accession: str,
    position: int,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Render the subset of features that overlap a residue position."""
    if fmt == "json":
        return _json_envelope(
            {"accession": accession, "position": position, "features": features},
            provenance,
        )
    lines: list[str] = [
        f"## Features at residue {position} of {accession} ({len(features)} feature(s))",
        "",
    ]
    if not features:
        lines.append(f"_No annotated features overlap position {position}._")
    else:
        for feat in features:
            ftype = str(feat.get("type", "?"))
            loc = feat.get("location") or {}
            start = (loc.get("start") or {}).get("value", "?")
            end = (loc.get("end") or {}).get("value", "?")
            desc = str(feat.get("description", "") or "").strip()
            range_str = f"{start}-{end}" if start != end else f"{start}"
            head = f"**{ftype}** [{range_str}]"
            if desc:
                head += f": {desc}"
            lines.append(f"- {head}")
            alt = feat.get("alternativeSequence") or {}
            if isinstance(alt, dict) and alt:
                orig = str(alt.get("originalSequence", "") or "")
                alts = alt.get("alternativeSequences") or []
                if orig and alts:
                    lines.append(f"  Variant: {orig} → {'/'.join(str(a) for a in alts)}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_variant_lookup(
    matches: list[Feature],
    accession: str,
    change: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Render UniProt natural-variant matches for an HGVS-style change."""
    if fmt == "json":
        return _json_envelope(
            {"accession": accession, "change": change, "matches": matches}, provenance
        )
    lines: list[str] = [
        f"## Variant lookup: {accession} {change} ({len(matches)} match(es))",
        "",
    ]
    if not matches:
        lines.append(
            f"_No UniProt natural-variant feature matches `{change}`. "
            f"This does not mean the variant is benign — UniProt only annotates "
            f"variants from the literature. See ClinVar / dbSNP for population data._"
        )
    else:
        for m in matches:
            loc = m.get("location") or {}
            pos = (loc.get("start") or {}).get("value", "?")
            alt = m.get("alternativeSequence") or {}
            orig = str(alt.get("originalSequence", "") or "")
            alts = alt.get("alternativeSequences") or []
            mutation = f"{orig}{pos}{'/'.join(str(a) for a in alts)}" if orig else f"pos {pos}"
            desc = str(m.get("description", "") or "").strip()
            lines.append(f"### {mutation}")
            if desc:
                lines.append(f"{desc}")
            evidences = m.get("evidences") or []
            eco_codes = sorted(
                {str(e.get("evidenceCode", "")) for e in evidences if e.get("evidenceCode")}
            )
            if eco_codes:
                lines.append(f"**Evidence:** {', '.join(eco_codes)}")
            lines.append("")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))
    return "\n".join(lines)


def fmt_disease_associations(
    associations: list[dict[str, Any]],
    accession: str,
    fmt: str = "markdown",
    *,
    provenance: Provenance | None = None,
) -> str:
    """Format the structured disease records extracted from an entry's
    ``DISEASE``-type comments."""
    if fmt == "json":
        return _json_envelope({"accession": accession, "diseases": associations}, provenance)
    lines: list[str] = [
        f"## Disease associations: {accession} ({len(associations)} record(s))",
        "",
    ]
    if not associations:
        lines.append(
            "_No DISEASE-type annotations on this entry. "
            "Absence here does not imply the protein is disease-irrelevant — "
            "see Open Targets / OMIM / DisGeNET for additional disease-gene evidence._"
        )
    else:
        for d in associations:
            name = str(d.get("name", "?") or "?")
            disease_id = str(d.get("disease_id", "") or "")
            acronym = str(d.get("acronym", "") or "")
            head = f"### {name}"
            extras: list[str] = []
            if acronym:
                extras.append(f"acronym {acronym}")
            if disease_id:
                extras.append(f"id {disease_id}")
            if extras:
                head += f"  ({', '.join(extras)})"
            lines.append(head)
            desc = str(d.get("description", "") or "").strip()
            if desc:
                lines.append(desc)
            xrefs = d.get("cross_references") or []
            if xrefs:
                bits = [
                    f"{x.get('database', '?')}:{x.get('id', '?')}" for x in xrefs if x.get("id")
                ]
                if bits:
                    lines.append(f"**Cross-refs:** {', '.join(bits)}")
            note = str(d.get("note", "") or "").strip()
            if note:
                lines.append(f"**Note:** {note[:280]}")
            lines.append("")
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
