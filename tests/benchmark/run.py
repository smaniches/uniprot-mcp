"""Benchmark runner — execute each prompt under one comparator.

This is a v1 SCAFFOLD. The body is a stub that argparse-parses the
expected CLI shape and exits with a non-zero status pointing at the
sealing-and-execution work. Full body lands alongside the first
benchmark run, which requires:

  1. Sealed `expected.jsonl` and `expected.hashes.jsonl` on `main`.
  2. ANTHROPIC_API_KEY in the environment.
  3. (`uniprot-mcp` comparator) the MCP server installed and a
     stdio-transport orchestrator wired to it.
  4. (`vanilla-claude` comparator) WebFetch enabled.
  5. (`manual` comparator) a human running the protocol in
     `graders.md`.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
PROMPTS_PATH = HERE / "prompts.jsonl"

VALID_COMPARATORS = {"uniprot-mcp", "vanilla-claude", "manual"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--comparator",
        required=True,
        choices=sorted(VALID_COMPARATORS),
        help="which system answers the prompts",
    )
    p.add_argument(
        "--out",
        required=True,
        type=pathlib.Path,
        help="run directory; created if absent (e.g. run-2026-05-12/)",
    )
    p.add_argument(
        "--prompt-id",
        type=int,
        default=None,
        help="run a single prompt only (debugging); default is all 30",
    )
    return p.parse_args(argv)


def load_prompts() -> list[dict]:
    return [
        json.loads(line)
        for line in PROMPTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    prompts = load_prompts()
    if args.prompt_id is not None:
        prompts = [p for p in prompts if p["prompt_id"] == args.prompt_id]
        if not prompts:
            print(f"ERROR: no prompt with id {args.prompt_id}", file=sys.stderr)
            return 2
    args.out.mkdir(parents=True, exist_ok=True)

    print(
        f"[scaffold] would run {len(prompts)} prompt(s) under comparator={args.comparator} "
        f"into {args.out}/, but the runner body has not yet been wired.",
        file=sys.stderr,
    )
    print(
        "[scaffold] To unblock, complete the sealing step (see "
        "tests/benchmark/AUDIT.md `Sealing checklist`) and replace this stub.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
