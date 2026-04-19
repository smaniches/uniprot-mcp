"""Response formatters: JSON and Markdown output for UniProt data."""
import json


def _protein_name(entry):
    pd = entry.get("proteinDescription", {})
    rec = pd.get("recommendedName", {})
    if rec:
        return rec.get("fullName", {}).get("value", "Unknown")
    sub = pd.get("submissionNames", [])
    if sub:
        return sub[0].get("fullName", {}).get("value", "Unknown")
    return "Unknown"


def _gene_name(entry):
    genes = entry.get("genes", [])
    return genes[0].get("geneName", {}).get("value", "") if genes else ""


def _organism(entry):
    return entry.get("organism", {}).get("scientificName", "Unknown")


def fmt_entry(data, fmt="markdown"):
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    acc = data.get("primaryAccession", "?")
    name = _protein_name(data)
    gene = _gene_name(data)
    org = _organism(data)
    reviewed = "Swiss-Prot" if data.get("entryType", "").startswith("UniProtKB reviewed") else "TrEMBL"
    seq = data.get("sequence", {})
    lines = [f"## {acc}: {name}", ""]
    if gene:
        lines.append(f"**Gene:** {gene}")
    lines.append(f"**Organism:** {org}")
    lines.append(f"**Reviewed:** {reviewed}")
    if seq:
        lines.append(f"**Length:** {seq.get('length', '?')} aa | **Mass:** {seq.get('molWeight', '?')} Da")
    for c in data.get("comments", []):
        if c.get("commentType") == "FUNCTION":
            texts = c.get("texts", [])
            if texts:
                lines.extend(["", f"**Function:** {texts[0].get('value', '')}"])
        if c.get("commentType") == "SUBCELLULAR LOCATION":
            locs = [l.get("location", {}).get("value", "") for l in c.get("subcellularLocations", []) if l.get("location")]
            if locs:
                lines.append(f"**Localization:** {', '.join(locs[:5])}")
        if c.get("commentType") == "DISEASE":
            d = c.get("disease", {})
            if d:
                lines.append(f"**Disease:** {d.get('diseaseId', '')} - {d.get('description', '')[:150]}")
    xrefs = data.get("uniProtKBCrossReferences", [])
    if xrefs:
        dbs = {}
        for x in xrefs:
            dbs[x.get("database", "?")] = dbs.get(x.get("database", "?"), 0) + 1
        pdb_ids = [x.get("id", "") for x in xrefs if x.get("database") == "PDB"]
        lines.extend(["", f"**Cross-refs:** {len(xrefs)} across {len(dbs)} databases"])
        if pdb_ids:
            show = pdb_ids[:10]
            extra = f" (+{len(pdb_ids)-10} more)" if len(pdb_ids) > 10 else ""
            lines.append(f"**PDB:** {', '.join(show)}{extra}")
    return "\n".join(lines)


def fmt_search(data, fmt="markdown"):
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    results = data.get("results", [])
    lines = [f"**{len(results)} results**", ""]
    for i, e in enumerate(results, 1):
        acc = e.get("primaryAccession", "?")
        name = _protein_name(e)
        gene = _gene_name(e)
        org = _organism(e)
        rev = "SP" if e.get("entryType", "").startswith("UniProtKB reviewed") else "TR"
        length = e.get("sequence", {}).get("length", "?")
        g = f" ({gene})" if gene else ""
        lines.append(f"**{i}. [{acc}]** {name}{g}")
        lines.append(f"   {org} | {length} aa | {rev}")
        lines.append("")
    return "\n".join(lines)


def fmt_features(features, accession, fmt="markdown"):
    if fmt == "json":
        return json.dumps(features, indent=2, ensure_ascii=False, default=str)
    by_type = {}
    for f in features:
        by_type.setdefault(f.get("type", "?"), []).append(f)
    lines = [f"## Features: {accession} ({len(features)} total)", ""]
    for ftype, feats in sorted(by_type.items()):
        lines.append(f"### {ftype} ({len(feats)})")
        for feat in feats[:20]:
            loc = feat.get("location", {})
            s = loc.get("start", {}).get("value", "?")
            e = loc.get("end", {}).get("value", "?")
            desc = feat.get("description", "")
            lines.append(f"  {s}-{e}: {desc}" if desc else f"  {s}-{e}")
        if len(feats) > 20:
            lines.append(f"  ... (+{len(feats)-20} more)")
        lines.append("")
    return "\n".join(lines)


def fmt_go(xrefs, accession, aspect_filter, fmt="markdown"):
    go_refs = [x for x in xrefs if x.get("database") == "GO"]
    if fmt == "json":
        return json.dumps(go_refs, indent=2, ensure_ascii=False, default=str)
    by_aspect = {"F": [], "P": [], "C": []}
    for ref in go_refs:
        go_id = ref.get("id", "")
        props = {p["key"]: p["value"] for p in ref.get("properties", [])}
        term = props.get("GoTerm", "")
        ev = props.get("GoEvidenceType", "")
        for prefix in ("F:", "P:", "C:"):
            if term.startswith(prefix):
                by_aspect[prefix[0]].append((go_id, term[2:], ev))
    if aspect_filter:
        by_aspect = {k: v for k, v in by_aspect.items() if k == aspect_filter}
    names = {"F": "Molecular Function", "P": "Biological Process", "C": "Cellular Component"}
    total = sum(len(v) for v in by_aspect.values())
    lines = [f"## GO: {accession} ({total} terms)", ""]
    for asp in ("F", "P", "C"):
        terms = by_aspect.get(asp, [])
        if not terms:
            continue
        lines.append(f"### {names[asp]} ({len(terms)})")
        for go_id, term, ev in terms:
            lines.append(f"  {go_id}: {term} [{ev}]")
        lines.append("")
    return "\n".join(lines)


def fmt_crossrefs(xrefs, accession, db_filter, fmt="markdown"):
    if db_filter:
        xrefs = [x for x in xrefs if x.get("database", "").lower() == db_filter.lower()]
    if fmt == "json":
        return json.dumps(xrefs, indent=2, ensure_ascii=False, default=str)
    by_db = {}
    for x in xrefs:
        by_db.setdefault(x.get("database", "?"), []).append(x.get("id", ""))
    lines = [f"## Cross-refs: {accession} ({len(by_db)} databases, {len(xrefs)} entries)", ""]
    for db in sorted(by_db):
        ids = by_db[db]
        show = ", ".join(ids[:15])
        extra = f" (+{len(ids)-15} more)" if len(ids) > 15 else ""
        lines.append(f"**{db}** ({len(ids)}): {show}{extra}")
    return "\n".join(lines)


def fmt_variants(features, accession, fmt="markdown"):
    variants = [f for f in features if f.get("type") == "Natural variant"]
    if fmt == "json":
        return json.dumps(variants, indent=2, ensure_ascii=False, default=str)
    lines = [f"## Variants: {accession} ({len(variants)})", ""]
    for v in variants[:50]:
        loc = v.get("location", {})
        pos = loc.get("start", {}).get("value", "?")
        desc = v.get("description", "")
        alt = v.get("alternativeSequence", {})
        orig = alt.get("originalSequence", "")
        alts = alt.get("alternativeSequences", [])
        mut = f"{orig}{pos}{'/'.join(alts)}" if orig else f"pos {pos}"
        lines.append(f"  **{mut}**: {desc}" if desc else f"  **{mut}**")
    if len(variants) > 50:
        lines.append(f"  ... (+{len(variants)-50} more)")
    return "\n".join(lines)


def fmt_idmapping(data, fmt="markdown"):
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    results = data.get("results", [])
    failed = data.get("failedIds", [])
    lines = [f"## ID Mapping: {len(results)} mapped, {len(failed)} failed", ""]
    for r in results[:50]:
        f = r.get("from", "?")
        to = r.get("to", {})
        to_id = to.get("primaryAccession", to.get("id", str(to))) if isinstance(to, dict) else str(to)
        lines.append(f"  {f} -> {to_id}")
    if len(results) > 50:
        lines.append(f"  ... (+{len(results)-50} more)")
    if failed:
        lines.extend(["", f"**Failed:** {', '.join(failed[:20])}"])
    return "\n".join(lines)


def fmt_taxonomy(data, fmt="markdown"):
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    results = data.get("results", [])
    lines = [f"## Taxonomy ({len(results)} results)", ""]
    for r in results:
        tid = r.get("taxonId", "?")
        sci = r.get("scientificName", "?")
        common = r.get("commonName", "")
        rank = r.get("rank", "")
        c = f" ({common})" if common else ""
        lines.append(f"  **{tid}**: {sci}{c} [{rank}]")
    return "\n".join(lines)
