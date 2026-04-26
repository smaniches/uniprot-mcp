"""Benchmark scorer — aggregate two-grader scores into a final table.

This is a v1 SCAFFOLD. Same shape as `run.py`: argparse-validates,
then exits with a non-zero status referencing the sealing-and-execution
work. Full body lands alongside the first benchmark run.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import pathlib
import sys


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--run-dir",
        required=True,
        type=pathlib.Path,
        help="directory produced by run.py for one specific date / run",
    )
    p.add_argument(
        "--graders",
        required=True,
        help="comma-separated grader names (must match graders.md entries)",
    )
    p.add_argument(
        "--arbitrator",
        required=True,
        help="single arbitrator name (must match graders.md)",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.run_dir.is_dir():
        print(f"ERROR: {args.run_dir} is not a directory", file=sys.stderr)
        return 2
    print(
        f"[scaffold] would aggregate scores in {args.run_dir} from graders "
        f"{args.graders.split(',')} with arbitrator {args.arbitrator}, "
        "but the scorer body has not yet been wired.",
        file=sys.stderr,
    )
    print(
        "[scaffold] To unblock, complete the sealing step and replace this stub.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
