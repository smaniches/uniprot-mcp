"""Contract tests for the disease & target atlas (examples/atlas/).

The atlas is a research-demonstration corpus. Each entry is an
unverified-by-default claim about how a UniProt accession maps to a
disease (via MONDO/OMIM) and a therapeutic axis. The contract tests
gate the *structural* correctness of those claims so that no entry
with a malformed accession, missing fields, or invalid JSON-LD ever
ships on `main`. The *content* correctness (does the claimed MONDO ID
really name the claimed disease?) is community-reviewable and cannot
be checked without an external ontology service.

Three gates here:

1. ``atlas.json`` parses as JSON and matches the JSON-LD shape we
   declare in `examples/atlas/atlas.json`.
2. Every UniProt accession in the manifest matches the official
   accession regex (`ACCESSION_RE` from `uniprot_mcp.client`). Bad
   accessions are caught before they reach the live API.
3. Every Markdown atlas entry referenced in the manifest exists on
   disk in `examples/atlas/`. No dangling references.

The optional integration test (`pytest --integration`) also calls
the live UniProt REST API for every accession and asserts a 200
response. That is run on demand, not on every push.

Note on epistemic discipline: the contract tests do not certify
that the *therapeutic axis*, *disease classification*, or *MONDO ID*
in any atlas entry is correct. They only certify that the references
are well-formed. Correctness of the biology is a matter for
community review and the explicit METHODOLOGY.md statement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from uniprot_mcp.client import ACCESSION_RE

REPO_ROOT = Path(__file__).resolve().parents[2]
ATLAS_DIR = REPO_ROOT / "examples" / "atlas"
ATLAS_JSON = ATLAS_DIR / "atlas.json"

# MONDO IDs are 7-digit zero-padded. http://purl.obolibrary.org/obo/MONDO_NNNNNNN
_MONDO_RE = re.compile(r"\Amondo:\d{7}\Z")
# OMIM entries are 6-digit numerals (sometimes preceded by a +/#/% but the
# atlas stores the bare numeric ID).
_OMIM_RE = re.compile(r"\A\d{6}\Z")
# DOID is variable-length numeric. http://purl.obolibrary.org/obo/DOID_NNNNNNN
_DOID_RE = re.compile(r"\Adoid:\d{1,8}\Z")
# NCBI taxonomy IDs are integers (1-7+ digits).
_TAXON_RE = re.compile(r"\Ancbitaxon:\d+\Z")
# ARO IDs are zero-padded 7-digit. http://purl.obolibrary.org/obo/ARO_NNNNNNN
_ARO_RE = re.compile(r"\Aaro:\d{7}\Z")


# Disease classes the atlas commits to using. The list lives here so the
# atlas can never accidentally introduce a new class without updating
# both the manifest and this gate at the same time.
_ALLOWED_DISEASE_CLASSES = {
    "Hereditary cancer",
    "Solid-tumour driver",
    "Single-gene rare disease",
    "Metabolic / lysosomal",
    "Neurodegenerative",
    "Cardiovascular / laminopathy",
    "Pharmacogenomic",
    "Infectious-disease drug-resistance",
}


@pytest.fixture(scope="module")
def manifest() -> dict:
    """Parse atlas.json once and share across tests."""
    if not ATLAS_JSON.exists():
        pytest.skip(f"{ATLAS_JSON} absent — atlas not yet built.")
    return json.loads(ATLAS_JSON.read_text(encoding="utf-8"))


def test_atlas_json_parses(manifest: dict) -> None:
    assert manifest, "atlas.json parsed but is empty"


def test_atlas_top_level_shape(manifest: dict) -> None:
    """Top-level JSON-LD record must declare type, license, version,
    creator, and an entries array."""
    assert manifest.get("@type") == "schema:Dataset"
    assert "@context" in manifest
    assert manifest.get("schema:license") == "https://www.apache.org/licenses/LICENSE-2.0"
    assert "schema:version" in manifest
    assert "entries" in manifest
    assert isinstance(manifest["entries"], list)
    assert len(manifest["entries"]) > 0


def test_every_entry_has_required_fields(manifest: dict) -> None:
    """Each entry must carry: a UniProt @id, a Markdown atlasFile, a
    name, a gene, an organism, a diseaseClass, and an exemplifies
    array. Missing any of these is a structural defect."""
    required = {"@id", "atlasFile", "name", "gene", "organism", "diseaseClass", "exemplifies"}
    for i, entry in enumerate(manifest["entries"]):
        missing = required - set(entry.keys())
        assert not missing, f"entry {i} ({entry.get('atlasFile', '?')}) missing fields: {missing}"


def test_every_uniprot_id_matches_official_regex(manifest: dict) -> None:
    """The @id of each entry is a UniProt accession with prefix
    `uniprot:`. The bare accession (after the prefix) must match the
    official UniProt ACCESSION_RE imported from the client."""
    for entry in manifest["entries"]:
        prefixed = entry["@id"]
        assert prefixed.startswith("uniprot:"), f"@id {prefixed!r} not under uniprot: prefix"
        bare = prefixed[len("uniprot:") :]
        assert ACCESSION_RE.match(bare), (
            f"bare accession {bare!r} (entry {entry.get('atlasFile')}) does not match "
            f"the official UniProt regex"
        )


def test_every_atlas_markdown_file_exists(manifest: dict) -> None:
    """Every entry's atlasFile must exist under examples/atlas/."""
    for entry in manifest["entries"]:
        path = ATLAS_DIR / entry["atlasFile"]
        assert path.exists(), f"missing atlas file: {path}"


def test_every_disease_class_is_allowed(manifest: dict) -> None:
    """diseaseClass must be in the allowlist. Adding a new class
    requires updating both the manifest and the allowlist in the
    same commit."""
    for entry in manifest["entries"]:
        cls = entry["diseaseClass"]
        assert cls in _ALLOWED_DISEASE_CLASSES, (
            f"entry {entry.get('atlasFile')} carries unrecognised diseaseClass {cls!r}; "
            f"add to _ALLOWED_DISEASE_CLASSES if intentional"
        )


def test_every_organism_has_taxon_id(manifest: dict) -> None:
    """Every entry's organism must declare an NCBI Taxonomy ID under
    the ncbitaxon: prefix."""
    for entry in manifest["entries"]:
        org = entry.get("organism", {})
        taxon = org.get("taxonId", "")
        assert _TAXON_RE.match(taxon), (
            f"entry {entry.get('atlasFile')} organism.taxonId {taxon!r} does not match ncbitaxon: pattern"
        )


def test_disease_ids_are_well_formed(manifest: dict) -> None:
    """Each disease's @id must match either MONDO or DOID format.
    Pharmacogenomic entries may use a synthetic placeholder under
    mondo:0000001 (we treat that as a valid sentinel)."""
    for entry in manifest["entries"]:
        for disease in entry.get("diseases", []):
            did = disease.get("@id", "")
            ok = _MONDO_RE.match(did) or _DOID_RE.match(did)
            assert ok, (
                f"entry {entry.get('atlasFile')} disease @id {did!r} is not a "
                f"well-formed MONDO or DOID identifier"
            )


def test_omim_ids_are_well_formed(manifest: dict) -> None:
    """If `omim` is present and non-null, every element must be a
    6-digit OMIM identifier (bare digits, not URL)."""
    for entry in manifest["entries"]:
        omim = entry.get("omim")
        if omim is None:
            continue
        assert isinstance(omim, list), f"entry {entry.get('atlasFile')} omim must be a list or null"
        for oid in omim:
            assert _OMIM_RE.match(str(oid)), (
                f"entry {entry.get('atlasFile')} OMIM id {oid!r} is not a 6-digit number"
            )


def test_aro_id_well_formed_when_present(manifest: dict) -> None:
    """ARO IDs (CARD antibiotic-resistance ontology) are 7-digit
    zero-padded under the aro: prefix."""
    for entry in manifest["entries"]:
        aro = entry.get("aro")
        if aro is None:
            continue
        assert _ARO_RE.match(aro), f"entry {entry.get('atlasFile')} ARO id {aro!r} malformed"


def test_atlas_size_minimum(manifest: dict) -> None:
    """Atlas should never shrink unexpectedly. v1.1.0 baseline is 25
    entries; future versions can expand but reductions need explicit
    review."""
    n = len(manifest["entries"])
    assert n >= 25, (
        f"atlas has only {n} entries; v1.1.0 baseline is 25 — investigate why entries went missing"
    )


def test_no_duplicate_disease_ontology_id_with_distinct_names(manifest: dict) -> None:
    """Each disease ontology @id must be associated with at most one
    normalized (lowercased, stripped) disease name across the curated
    atlas. A reused ID with a different name is almost always a
    copy-paste error — the kind that surfaced in v1.1.2 review and
    motivated this test in v1.1.3.

    The optional ``examples/atlas/aliases_whitelist.json`` lists IDs
    where multiple distinct labels are intentional (alias / preferred
    form pairs documented by hand). Entries listed there are exempt;
    every other ID must collapse to a single name.
    """
    import collections

    whitelist_path = ATLAS_DIR / "aliases_whitelist.json"
    whitelist: set[str] = set()
    if whitelist_path.exists():
        try:
            data = json.loads(whitelist_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            pytest.fail(f"aliases_whitelist.json is not valid JSON: {exc}")
        if not isinstance(data, dict) or not isinstance(data.get("aliases"), list):
            pytest.fail(
                "aliases_whitelist.json must be a JSON object with an "
                '\'aliases\' array of {"id": ..., "justification": ...} entries'
            )
        whitelist = {entry["id"] for entry in data["aliases"] if isinstance(entry, dict)}

    id_to_names: dict[str, set[str]] = collections.defaultdict(set)
    for entry in manifest["entries"]:
        for disease in entry.get("diseases", []):
            ontology_id = disease.get("@id")
            name = (disease.get("name") or "").strip().lower()
            if ontology_id and name:
                id_to_names[ontology_id].add(name)

    conflicts = {
        oid: sorted(names)
        for oid, names in id_to_names.items()
        if len(names) > 1 and oid not in whitelist
    }
    assert not conflicts, (
        "Duplicate ontology @id values map to distinct disease names:\n"
        + "\n".join(f"  {oid}: {names!r}" for oid, names in conflicts.items())
        + "\nIf the divergence is intentional, document each id in "
        "examples/atlas/aliases_whitelist.json with a justification field."
    )


# ---------------------------------------------------------------------------
# Optional live-API verification (opt-in via --integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_every_uniprot_accession_resolves_live(manifest: dict) -> None:
    """For every atlas entry, the bare UniProt accession must resolve
    to HTTP 200 against the live UniProt REST API.

    This is the *content-correctness* gate the structural tests cannot
    apply: a well-formed accession is no guarantee that the entry
    actually exists at UniProt. We hit the live API to verify.

    Opt-in via ``pytest --integration``; not run on every push (would
    introduce a network dependency to fast offline CI)."""
    import httpx

    client = httpx.Client(
        base_url="https://rest.uniprot.org",
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": "uniprot-mcp-atlas-verifier/1.0", "Accept": "application/json"},
        follow_redirects=True,
    )
    failures: list[str] = []
    try:
        for entry in manifest["entries"]:
            bare = entry["@id"][len("uniprot:") :]
            r = client.get(f"/uniprotkb/{bare}.json")
            if r.status_code != 200:
                failures.append(
                    f"{entry.get('atlasFile')}: UniProt {bare} returned HTTP {r.status_code}"
                )
    finally:
        client.close()
    assert not failures, "Atlas accessions failing live verification:\n  " + "\n  ".join(failures)
