"""Ensure the source-only index cannot be mistaken for a maintained clinical atlas."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "examples" / "atlas"


def test_no_unsourced_curated_atlas_active() -> None:
    assert not (ATLAS / "atlas.json").exists()
    retired = (
        "tp53 brca1 brca2 mlh1 egfr kras braf erbb2 cftr htt dmd hbb smn1 "
        "fbn1 nf1 pah gba app snca myh7 lmna cyp2d6 vkorc1 g6pd tem1"
    ).split()
    assert not [name for name in retired if (ATLAS / f"{name}.md").exists()]


def test_source_index_remains_with_integrity_manifest() -> None:
    assert (ATLAS / "comprehensive_index.tsv").exists()
    assert (ATLAS / "comprehensive_index_pathogens.tsv").exists()
    assert (ATLAS / "manifest.json").exists()
    assert (ATLAS / "METHODOLOGY.md").exists()
