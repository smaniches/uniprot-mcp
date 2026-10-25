"""Offline checks for fail-closed mutation matrix reporting."""

from __future__ import annotations

import pathlib
import re
import runpy

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts/mutation_summary.py"
FUNCTIONS = runpy.run_path(str(SCRIPT), run_name="imported")
EXPECTED = FUNCTIONS["EXPECTED"]
summarize = FUNCTIONS["summarize"]


BUCKETS = {"killed": 3, "survived": 2, "timeout": 0, "suspicious": 0, "skipped": 0}


def _fixture(
    root: pathlib.Path,
    module: str,
    shard: int,
    count: int,
    *,
    done: int = 5,
    planned: int = 5,
) -> None:
    folder = root / f"mutmut-{module}-shard{shard}-of{count}" / "mutation-summary"
    folder.mkdir(parents=True, exist_ok=True)
    values = {
        "module": module,
        "shard": shard,
        "nshards": count,
        "path": f"src/uniprot_mcp/{module}.py",
        **BUCKETS,
        "done": done,
        "planned": planned,
        "complete": int(done == planned),
    }
    (folder / f"{module}-shard{shard}-of{count}.yaml").write_text(
        "".join(f"{key}: {value}\n" for key, value in values.items()), encoding="utf-8"
    )


def _full_roster(root: pathlib.Path) -> None:
    for module, count in EXPECTED.items():
        for shard in range(count):
            _fixture(root, module, shard, count)


def test_complete_matrix_is_a_valid_measurement(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    _full_roster(root)
    output = tmp_path / "summary.md"
    assert summarize(root, "success", output)
    text = output.read_text(encoding="utf-8")
    assert "COMPLETE" in text and "**TOTAL**" in text
    assert "60.00%" in text
    assert "DO NOT CITE" not in text


def test_partial_formatter_is_not_citable(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    _full_roster(root)
    _fixture(root, "formatters", 2, 6, done=4, planned=5)
    partial = next(root.rglob("formatters-shard2-of6.yaml"))
    partial.write_text(
        partial.read_text(encoding="utf-8").replace("killed: 3", "killed: 2"),
        encoding="utf-8",
    )
    output = tmp_path / "summary.md"
    assert not summarize(root, "failure", output)
    text = output.read_text(encoding="utf-8")
    assert "INCOMPLETE" in text and "DO NOT CITE" in text
    assert "unfinished shard formatters 2/6" in text
    assert "PARTIAL ONLY" in text


def test_missing_shard_fails_closed(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    _full_roster(root)
    missing = next(root.rglob("formatters-shard5-of6.yaml"))
    missing.unlink()
    output = tmp_path / "summary.md"
    assert not summarize(root, "success", output)
    assert "missing shards: formatters 5/6" in output.read_text(encoding="utf-8")


def test_zero_mutant_init_counts_as_complete(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    _full_roster(root)
    init = next(root.rglob("__init__-shard0-of1.yaml"))
    text = init.read_text(encoding="utf-8")
    for key in ("killed", "survived", "done", "planned"):
        text = re.sub(rf"^{key}: \d+$", f"{key}: 0", text, flags=re.MULTILINE)
    init.write_text(text, encoding="utf-8")
    assert summarize(root, "success", tmp_path / "summary.md")


def test_matrix_matches_expected_roster() -> None:
    workflow_path = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/mutation.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    matrix = workflow.split("        include:\n", 1)[1].split("    steps:\n", 1)[0]
    seen: set[tuple[str, int, int]] = set()
    for chunk in matrix.split("          - path:")[1:]:
        module = re.search(r"\n\s+module: (\S+)", chunk)
        shard = re.search(r"\n\s+shard: (\d+)", chunk)
        count = re.search(r"\n\s+nshards: (\d+)", chunk)
        assert module and shard and count
        seen.add((module.group(1), int(shard.group(1)), int(count.group(1))))
    expected = {
        (module, index, count) for module, count in EXPECTED.items() for index in range(count)
    }
    assert seen == expected


def test_strided_shards_are_disjoint_and_exhaustive() -> None:
    for mutants in (0, 1, 3, 6, 7, 38, 741, 742, 2000):
        slices = [set(range(mutants)[shard::6]) for shard in range(6)]
        assert set().union(*slices) == set(range(mutants))
        assert sum(len(part) for part in slices) == mutants


def test_non_success_matrix_status_invalidates_complete_artifacts(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    _full_roster(root)
    out = tmp_path / "summary.md"
    assert not summarize(root, "cancelled", out)
    assert "matrix concluded 'cancelled'" in out.read_text(encoding="utf-8")


def test_duplicate_summary_is_rejected(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    _full_roster(root)
    original = next(root.rglob("cache-shard0-of1.yaml"))
    duplicate = root / "duplicated" / "mutation-summary"
    duplicate.mkdir(parents=True)
    (duplicate / original.name).write_bytes(original.read_bytes())
    report = tmp_path / "summary.md"
    assert not summarize(root, "success", report)
    assert "duplicate shard" in report.read_text(encoding="utf-8")


def test_bucket_mismatch_is_rejected(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    _full_roster(root)
    original = next(root.rglob("client-shard0-of1.yaml"))
    original.write_text(
        original.read_text(encoding="utf-8").replace("killed: 3", "killed: 30"),
        encoding="utf-8",
    )
    report = tmp_path / "summary.md"
    assert not summarize(root, "success", report)
    assert "mutant bucket counts do not reconcile" in report.read_text(encoding="utf-8")


def test_no_artifacts_must_fail_with_an_explicit_report(tmp_path: pathlib.Path) -> None:
    report = tmp_path / "summary.md"
    assert not summarize(tmp_path / "nonexistent", "skipped", report)
    content = report.read_text(encoding="utf-8")
    assert "INCOMPLETE" in content
    assert "missing shards:" in content
    assert "PARTIAL ONLY" in content
