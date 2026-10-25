"""Regression tests for mutation result completeness."""

from __future__ import annotations

import pathlib

from scripts.mutation_summary import EXPECTED, summarize


def _write(root: pathlib.Path, module: str, shard: int, n: int, *, done: int = 2) -> None:
    path = root / f"mutmut-{module}-shard{shard}-of{n}" / "mutation-summary"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{module}-{shard}.yaml").write_text(
        f"module: {module}\nshard: {shard}\nnshards: {n}\n"
        f"killed: {done}\nsurvived: 0\ntimeout: 0\n"
        f"suspicious: 0\nskipped: 0\ndone: {done}\n"
        "planned: 2\n"
        f"complete: {int(done == 2)}\n",
        encoding="utf-8",
    )


def test_incomplete_matrix_cannot_pass(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    for module, n in EXPECTED.items():
        for shard in range(n):
            _write(root, module, shard, n)
    out = tmp_path / "summary.md"
    assert summarize(root, "success", out)
    assert "COMPLETE" in out.read_text(encoding="utf-8")
    assert not summarize(root, "cancelled", out)
    assert "INCOMPLETE" in out.read_text(encoding="utf-8")
    _write(root, "formatters", 0, EXPECTED["formatters"], done=1)
    assert not summarize(root, "success", out)
    assert "unfinished shard" in out.read_text(encoding="utf-8")


def test_missing_shard_fails_closed(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "artifacts"
    for module, n in EXPECTED.items():
        for shard in range(n):
            if module == "formatters" and shard == 5:
                continue
            _write(root, module, shard, n)
    out = tmp_path / "summary.md"
    assert not summarize(root, "success", out)
    assert "missing shards: formatters 5/6" in out.read_text(encoding="utf-8")
