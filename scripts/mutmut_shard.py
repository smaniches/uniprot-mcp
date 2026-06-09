#!/usr/bin/env python3
"""Run a disjoint, exhaustive *shard* of a file's mutmut mutants.

mutmut 2.5.1 has no native sharding: its ``run`` argument is either a
single mutation id or one file path, and ``--paths-to-mutate`` is
file-granular. The two largest source modules (``server.py`` and
``formatters.py``) are single files whose full mutmut run exceeds the
GitHub-hosted-runner 360-minute wall-time cap, so the per-module matrix
job is chronically cancelled.

This wrapper partitions the mutant set of a single file across N shards
*without changing what is measured*. It monkeypatches
``mutmut.__main__.parse_run_argument`` so that, after mutmut has built
the full, deterministic mutant list for the file (via ``list_mutations``
+ ``register_mutants``), we keep only a strided slice ``[shard::nshards]``
of each file's mutant list before mutmut computes ``config.total`` and
runs the mutants.

Why this preserves the kill-rate measurement exactly:

* Every shard rebuilds the identical full mutant list from the same
  fixed source (``list_mutations`` is deterministic), then takes the
  strided slice ``mutants[shard::nshards]``.
* Across ``shard = 0 .. nshards-1`` the strided slices are disjoint and
  their union is the complete list (no overlap, no gap).
* ``--use-coverage`` is left intact -- coverage skip is applied per
  mutant by mutmut exactly as in the unsharded run.
* The per-mutant ``--runner`` test command is byte-identical in every
  shard (it is passed straight through to mutmut and never touched
  here).

Therefore the sum over shards of KILLED / TIMEOUT / SUSPICIOUS /
SURVIVED equals the unsharded coverage run exactly. SKIPPED differs per
shard (each shard sees a different subset of skippable mutants) but
SKIPPED is excluded from the kill-rate denominator, so the rate is
unchanged. Strided (rather than contiguous-block) slicing interleaves
cheap and expensive mutants so the shards stay wall-time balanced.

The shard index/count are read from the environment so the workflow can
set them per matrix entry without disturbing mutmut's own CLI parsing:

    MUTMUT_SHARD_INDEX   0-based shard index            (default 0)
    MUTMUT_SHARD_COUNT   total number of shards         (default 1)

Usage (identical to ``mutmut run`` otherwise):

    MUTMUT_SHARD_INDEX=2 MUTMUT_SHARD_COUNT=5 \
        python scripts/mutmut_shard.py run \
            --paths-to-mutate=src/uniprot_mcp/server.py \
            --use-coverage \
            --tests-dir=tests/unit \
            --runner='python -m pytest -x --tb=no -q --no-header tests/unit' \
            --simple-output

With ``MUTMUT_SHARD_COUNT=1`` (the default) the slice is the whole list,
so this wrapper is a transparent pass-through to ``mutmut`` and behaves
identically to invoking ``mutmut`` directly.

Pinned to mutmut 2.5.1: this couples to the internal
``parse_run_argument`` seam, so the workflow installs ``mutmut==2.5.1``
exactly.
"""

from __future__ import annotations

import os
import sys


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {raw!r}") from exc
    return value


def main() -> int:
    shard_index = _positive_int("MUTMUT_SHARD_INDEX", 0)
    shard_count = _positive_int("MUTMUT_SHARD_COUNT", 1)

    if shard_count < 1:
        raise SystemExit("MUTMUT_SHARD_COUNT must be >= 1")
    if not (0 <= shard_index < shard_count):
        raise SystemExit(
            f"MUTMUT_SHARD_INDEX must be in [0, {shard_count}); got {shard_index}"
        )

    import mutmut.__main__ as mm

    _orig_parse = mm.parse_run_argument

    def _sharded_parse(argument, config, dict_synonyms, mutations_by_file, *args, **kwargs):
        # Let mutmut build the FULL, deterministic mutant list for the
        # target file(s) and register every mutant in its cache, exactly
        # as in an unsharded run.
        _orig_parse(argument, config, dict_synonyms, mutations_by_file, *args, **kwargs)

        if shard_count == 1:
            return  # transparent pass-through

        # Keep only this shard's strided slice. Disjoint + exhaustive
        # across all shard indices; interleaves cheap/expensive mutants.
        for filename in list(mutations_by_file):
            mutations_by_file[filename] = mutations_by_file[filename][shard_index::shard_count]

    mm.parse_run_argument = _sharded_parse

    # Hand control to mutmut's real CLI. do_run recomputes config.total
    # from the (now sliced) mutations_by_file AFTER parse_run_argument
    # returns, so the "N/M KILLED ..." progress line and exit code are
    # correct for this shard.
    from mutmut.__main__ import climain

    # climain is the click group; drop our own argv[0] and pass the rest
    # (e.g. "run --paths-to-mutate=... --use-coverage ...") straight through.
    sys.argv = ["mutmut", *sys.argv[1:]]
    return climain()


if __name__ == "__main__":
    raise SystemExit(main())
