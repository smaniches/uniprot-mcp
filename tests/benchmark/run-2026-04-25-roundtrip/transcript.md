# Historical provenance transcript — withdrawn as verification evidence

**Correction dated 2026-10-25.**

The former April 25, 2026 transcript displayed specific UniProt
response hashes and successful verification verdicts, but did not
preserve the corresponding upstream response bodies needed to
independently validate those exact receipts. It must **not** be cited
as evidence of a successful live provenance round trip or as a
reproducible scientific observation.

This correction does not assert that the provenance implementation is
defective. The unit and optional live integration tests remain
separate evidence for their respective contracts.

For a genuinely recorded and byte-bound example, use the
[October 15, 2026 TP53 R175H capture](../../../examples/01_clinical_variant_interpretation.jsonl),
the [preserved upstream bodies](../../../examples/captures/2026-10-15_tp53_r175h/),
and `tests/contract/test_tp53_capture_binding.py`.

The former transcript remains recoverable in the Git commit history,
rather than being silently rewritten into an invented new capture.
