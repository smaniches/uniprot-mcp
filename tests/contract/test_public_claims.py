"""Public statements must match what the repository contains.

Three things are pinned here, each of which had drifted before:

* **Benchmark status.** The repository holds a sealed answer key and a
  verifier for it. The runner and scorer are scaffolds, so no system has
  been evaluated. While that is so, the public documents have to say it
  and must not present the answer-key verification as a benchmark result.
  When ``run.py`` gains a body, the first test below fails and the
  documents are due for an update in the same change.
* **Frozen evidence.** The prompts, the committed digests and the recorded
  verifier output are historical records and must not change.
* **Stated values and versions.** Worked numbers, the documented pK table
  and version-specific notes are compared with the implementation.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from tests.benchmark import run as benchmark_run
from tests.benchmark import score as benchmark_score
from uniprot_mcp.proteinchem import compute_protein_properties

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "tests" / "benchmark"
RUN_RECORD = BENCHMARK / "run-2026-04-26-v1.1.0"


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _flat(relative: str) -> str:
    """File text as one line: blockquote markers dropped and runs of
    whitespace collapsed, so that wrapping is irrelevant."""
    unquoted = re.sub(r"(?m)^>[ \t]?", "", _text(relative))
    return " ".join(unquoted.split())


# ---------------------------------------------------------------------------
# Benchmark status
# ---------------------------------------------------------------------------


def test_benchmark_runner_and_scorer_are_scaffolds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Neither script runs anything: both announce themselves as scaffolds
    and return a failing status."""
    out_dir = tmp_path / "run"
    assert benchmark_run.main(["--comparator", "uniprot-mcp", "--out", str(out_dir)]) == 1
    runner_notice = capsys.readouterr().err
    assert "[scaffold]" in runner_notice
    assert "No benchmark run has been made" in runner_notice
    assert list(out_dir.iterdir()) == []  # nothing was produced

    status = benchmark_score.main(
        ["--run-dir", str(out_dir), "--graders", "a,b", "--arbitrator", "c"]
    )
    assert status == 1
    scorer_notice = capsys.readouterr().err
    assert "[scaffold]" in scorer_notice
    assert "Nothing has been scored" in scorer_notice


# Each public document that mentions the benchmark, with the sentence that
# tells the reader no system has been evaluated.
_NO_EVALUATION_STATEMENTS = {
    "README.md": "No system has been evaluated against the prompts",
    "OVERVIEW.md": "no server or baseline has been run against the prompts",
    "docs/index.md": "No system has been run against it yet.",
    "docs/CLAIMS.md": "neither this server nor a baseline has been run against the prompts",
    "docs/COMPETITIVE_LANDSCAPE.md": "No server or baseline has been run against the prompts yet",
    "tests/benchmark/README.md": "The benchmark has not been run.",
    "tests/benchmark/AUDIT.md": "No benchmark run exists.",
    "tests/benchmark/run-2026-04-26-v1.1.0/README.md": "The benchmark itself has not been run",
}


@pytest.mark.parametrize("document,statement", sorted(_NO_EVALUATION_STATEMENTS.items()))
def test_documents_say_that_no_system_has_been_evaluated(document: str, statement: str) -> None:
    assert statement in _flat(document), f"{document} no longer states: {statement!r}"


# Wording that presented the answer-key verification as a result for the
# server. None of it may come back while the scaffolds are scaffolds.
_WITHDRAWN_WORDING = (
    "verified 30/30 against live UniProt",
    "measured run at 30/30",
    "30/30 sealed-prompt benchmark verified",
    "re-runs the benchmark live",
    "tools are mutually consistent at this commit",
    "# Benchmark run —",
)


@pytest.mark.parametrize(
    "document",
    [*sorted(_NO_EVALUATION_STATEMENTS), "mkdocs.yml", ".zenodo.json", "REVIEWER.md"],
)
def test_documents_do_not_present_the_answer_key_check_as_a_benchmark_result(
    document: str,
) -> None:
    flat = _flat(document)
    for wording in _WITHDRAWN_WORDING:
        assert wording not in flat, f"{document} contains withdrawn wording: {wording!r}"


def test_readme_separates_answer_key_validation_from_system_evaluation() -> None:
    readme = _flat("README.md")
    assert "## Benchmark protocol: sealed answer key, no system run yet" in _text("README.md")
    assert "The answer key has been validated" in readme
    assert "It is not a measurement of this server." in readme
    assert "are scaffolds that exit without running anything" in readme


def test_answer_key_record_carries_its_correction_and_points_at_the_original() -> None:
    record = _flat("tests/benchmark/run-2026-04-26-v1.1.0/README.md")
    assert "Correction dated 2026-11-11." in record
    assert "Neither imports or calls `uniprot-mcp`" in record
    assert "It is not a score for any system." in record
    # The pre-correction wording stays reachable at an immutable revision.
    assert (
        "https://github.com/smaniches/uniprot-mcp/blob/"
        "ba34026d8c831a840ddee23c4c8c768d1d03d3e6/"
        "tests/benchmark/run-2026-04-26-v1.1.0/README.md"
    ) in record
    # The recorded result itself is still stated.
    assert "**30 / 30 prompts verified.**" in record


# ---------------------------------------------------------------------------
# Frozen evidence
# ---------------------------------------------------------------------------

_FROZEN = {
    BENCHMARK / "prompts.jsonl": "b8369c83a8531b96bcf808585a165c58d4c937b158e21150e2863a97325d4705",
    BENCHMARK
    / "expected.hashes.jsonl": "0dc192226cc05ed4245677a80958eaf6603186343e87487500a72ad5fe49ac79",
    RUN_RECORD
    / "verify-output.txt": "3a3f5dc792e3d333eb33c37b591bc35d1a21ec3302745abce5440f4ae3a2953b",
}


@pytest.mark.parametrize("path,digest", list(_FROZEN.items()), ids=lambda v: getattr(v, "name", ""))
def test_frozen_benchmark_evidence_is_byte_identical(path: Path, digest: str) -> None:
    """Prompts, sealed digests and the recorded verifier output as they were
    at v1.3.17. A correction may add context around them; it may not touch
    them."""
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_no_benchmark_run_directory_holds_comparator_output() -> None:
    """The only ``run-*`` directories are the answer-key record and the
    withdrawn transcript. A real run would add transcripts and scores, and
    the status statements above would then be out of date."""
    runs = sorted(p.name for p in BENCHMARK.glob("run-*") if p.is_dir())
    assert runs == ["run-2026-04-25-roundtrip", "run-2026-04-26-v1.1.0"]
    assert sorted(p.name for p in RUN_RECORD.iterdir()) == ["README.md", "verify-output.txt"]
    assert not (BENCHMARK / "graders.md").exists()


# ---------------------------------------------------------------------------
# Stated values and versions
# ---------------------------------------------------------------------------

_INS_HUMAN = (
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGG"
    "PGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
)


def test_readme_insulin_example_shows_what_the_tool_returns() -> None:
    p = compute_protein_properties(_INS_HUMAN)
    expected = (
        f"MW {round(p['molecular_weight']):,} Da, pI {p['theoretical_pi']:.2f}, "
        f"ε₂₈₀ {p['extinction_coefficient_280nm']:,} M⁻¹·cm⁻¹"
    )
    assert expected == "MW 11,981 Da, pI 5.22, ε₂₈₀ 16,960 M⁻¹·cm⁻¹"
    readme = _text("README.md")
    assert expected in readme
    assert f"{p['length']}-residue precursor" in readme


_SIDE_CHAIN_ROWS = {
    "C": "Cys",
    "D": "Asp",
    "E": "Glu",
    "H": "His",
    "K": "Lys",
    "R": "Arg",
    "Y": "Tyr",
}
_N_TERMINAL_NAMES = {
    "A": "Ala",
    "E": "Glu",
    "M": "Met",
    "P": "Pro",
    "S": "Ser",
    "T": "Thr",
    "V": "Val",
}


def test_documented_pk_table_is_the_table_the_code_applies() -> None:
    page = _text("docs/sequence-chemistry.md")
    model = compute_protein_properties("G")["charge_model"]
    assert f"The theoretical pI and the net charge use the {model['pk_set']} pK set." in page
    assert set(model["side_chain_pk"]) == set(_SIDE_CHAIN_ROWS)
    for residue, pk in model["side_chain_pk"].items():
        assert f"| {_SIDE_CHAIN_ROWS[residue]} side chain | {pk:.2f} |" in page
    assert f"| Carboxyl terminus | {model['c_terminus_pk']:.2f} |" in page
    assert f"| Amino terminus | {model['n_terminus_pk']:.2f}." in page
    for residue, name in _N_TERMINAL_NAMES.items():
        own = compute_protein_properties(residue)["charge_model"]["n_terminus_pk"]
        assert own != model["n_terminus_pk"]
        assert f"{name} {own:.2f}" in page
    # A residue outside that list takes the default.
    assert compute_protein_properties("Q")["charge_model"]["n_terminus_pk"] == 7.5


def test_sequence_chemistry_page_is_published_and_linked() -> None:
    assert "  - Sequence chemistry: sequence-chemistry.md" in _text("mkdocs.yml")
    assert "(docs/sequence-chemistry.md)" in _text("README.md")
    assert "(sequence-chemistry.md)" in _text("docs/tools.md")


# Version-specific notes that had outlived their version.
_STALE = {
    "README.md": (
        "(post-flip)",
        "Status note (v1.1.3)",
        "v1.2.0 target",
        "releases/tag/v1.1.0",
        "Lehninger",
        "24,980",
        "benchmark capture script",
    ),
    "OVERVIEW.md": ("v1.2.0 target", "v1.2.0 uplift", "v1.2.0 path"),
    "docs/index.md": ("v1.2.0 target", "1005 offline"),
    "docs/CLAIMS.md": ("v1.2.0 target", "1005 offline", "benchmark capture"),
    "docs/MUTATION_SCORES.md": ("(v1.2.0 target)", "Current state (v1.1.6)"),
    "docs/RELEASE.md": ("but not v1.1.5",),
}


@pytest.mark.parametrize("document", sorted(_STALE))
def test_documents_carry_no_outdated_version_notes(document: str) -> None:
    flat = _flat(document)
    for phrase in _STALE[document]:
        assert phrase not in flat, f"{document} still contains {phrase!r}"


def test_mutation_documents_state_that_no_threshold_is_enforced() -> None:
    """The summary script is the authority on the gate; the documents have
    to agree with the line it prints."""
    script = _text("scripts/mutation_summary.py")
    assert "Gate threshold: 0.0 (measurement-only); target 0.95 is not enforced." in script
    assert "At version 1.3.17 the threshold is still 0.0" in _flat("docs/MUTATION_SCORES.md")
    assert "It does not fail on a kill rate." in _flat("docs/MUTATION_SCORES.md")
    assert "no kill-rate threshold is enforced" in _flat("README.md")
    assert re.search(r"No kill-rate threshold is enforced", _flat("OVERVIEW.md"))


def test_readme_release_link_does_not_name_a_superseded_release() -> None:
    readme = _text("README.md")
    assert "[GitHub Release](https://github.com/smaniches/uniprot-mcp/releases)" in readme
    assert not re.search(r"releases/tag/v\d", readme)
