#!/usr/bin/env python3
"""Aggregate mutation shards only when the declared matrix is complete.

The report is still written on failure, so cancelled/time-limited runs retain
partial evidence without presenting it as a completed mutation score.
"""

from __future__ import annotations

import os
import pathlib
import sys

# Mirror the workflow matrix. Tests assert the two rosters remain identical.
EXPECTED = {
    "__init__": 1,
    "proteinchem": 1,
    "cache": 1,
    "client": 1,
    "formatters": 6,
    "server": 5,
}
BUCKETS = ("killed", "survived", "timeout", "suspicious", "skipped")


def _read_summary(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            raise ValueError(f"invalid summary line in {path.name}: {line!r}")
        key, value = (part.strip() for part in line.split(":", 1))
        if key in result:
            raise ValueError(f"duplicate {key} in {path.name}")
        result[key] = value
    return result


def _counts(summary: dict[str, str]) -> dict[str, int]:
    fields = (*BUCKETS, "done", "planned", "complete")
    values = {field: int(summary[field]) for field in fields}
    if any(value < 0 for value in values.values()):
        raise ValueError("negative mutant counts")
    if values["complete"] not in (0, 1):
        raise ValueError("complete must be 0 or 1")
    if values["done"] > values["planned"]:
        raise ValueError("processed mutants exceed planned mutants")
    if values["done"] != sum(values[field] for field in BUCKETS):
        raise ValueError("mutant bucket counts do not reconcile")
    if values["complete"] and values["done"] != values["planned"]:
        raise ValueError("incomplete progress incorrectly marked complete")
    return values


def summarize(root: pathlib.Path, run_result: str, output: pathlib.Path) -> bool:
    expected = {(module, index) for module, n in EXPECTED.items() for index in range(n)}
    seen: set[tuple[str, int]] = set()
    errors: list[str] = []
    by_module: dict[str, dict[str, int]] = {}

    for path in sorted(root.rglob("*.yaml")):
        try:
            summary = _read_summary(path)
            module = summary["module"]
            shard = int(summary["shard"])
            nshards = int(summary["nshards"])
            key = (module, shard)
            if module not in EXPECTED or nshards != EXPECTED[module] or key not in expected:
                raise ValueError(f"unexpected shard {module!r} {shard}/{nshards}")
            if key in seen:
                raise ValueError(f"duplicate shard {module!r} {shard}/{nshards}")
            counts = _counts(summary)
            seen.add(key)
            row = by_module.setdefault(module, {bucket: 0 for bucket in BUCKETS})
            for bucket in BUCKETS:
                row[bucket] += counts[bucket]
            if counts["complete"] != 1:
                errors.append(
                    f"unfinished shard {module} {shard}/{nshards}: "
                    f"{counts['done']}/{counts['planned']} mutants processed"
                )
        except (KeyError, ValueError, OSError) as exc:
            errors.append(f"invalid artifact {path}: {exc}")

    missing = sorted(expected - seen)
    if missing:
        labels = ", ".join(f"{mod} {idx}/{EXPECTED[mod]}" for mod, idx in missing)
        errors.append("missing shards: " + labels)
    if run_result != "success":
        errors.append(f"mutation matrix concluded {run_result!r}, not 'success'")

    complete = not errors
    lines = [
        f"## Mutation testing summary — {'COMPLETE' if complete else 'INCOMPLETE'}",
        "",
    ]
    if errors:
        lines += ["**DO NOT CITE THIS AS A COMPLETE MUTATION SCORE.**", ""]
        lines += [f"- {reason}" for reason in errors]
        lines.append("")
    lines += [
        "| module | shards | killed | survived | timeout | suspicious | skipped | kill rate |",
        "|---|---|---|---|---|---|---|---|",
    ]
    totals = {bucket: 0 for bucket in BUCKETS}
    for module in EXPECTED:
        if module not in by_module:
            continue
        counts = by_module[module]
        for bucket in BUCKETS:
            totals[bucket] += counts[bucket]
        denominator = sum(counts[bucket] for bucket in BUCKETS[:-1])
        detected = counts["killed"] + counts["timeout"] + counts["suspicious"]
        rate = detected / denominator if denominator else 0.0
        n = sum(1 for key in seen if key[0] == module)
        lines.append(
            f"| {module} | {n}/{EXPECTED[module]} | "
            + " | ".join(str(counts[bucket]) for bucket in BUCKETS)
            + f" | {rate:.2%} |"
        )

    denominator = sum(totals[bucket] for bucket in BUCKETS[:-1])
    detected_total = totals["killed"] + totals["timeout"] + totals["suspicious"]
    overall = detected_total / denominator if denominator else 0.0
    label = "TOTAL" if complete else "PARTIAL ONLY"
    lines.append(
        f"| **{label}** | {len(seen)}/{len(expected)} | "
        + " | ".join(f"**{totals[bucket]}**" for bucket in BUCKETS)
        + f" | **{overall:.2%}** |"
    )
    lines += ["", "Gate threshold: 0.0 (measurement-only); target 0.95 is not enforced.", ""]
    output.write_text("\n".join(lines), encoding="utf-8")
    return complete


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: mutation_summary.py ARTIFACT_ROOT OUTPUT_FILE", file=sys.stderr)
        return 2
    root, output = (pathlib.Path(path) for path in sys.argv[1:])
    success = summarize(root, os.environ.get("MUTATION_MATRIX_RESULT", "unknown"), output)
    if not success:
        print(f"Mutation testing INCOMPLETE; see {output}", file=sys.stderr)
        return 1
    print(f"Mutation testing COMPLETE; report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
