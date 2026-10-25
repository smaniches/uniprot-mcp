# Source-backed research example

The only published example transcript is
[TP53 R175H](01_clinical_variant_interpretation.jsonl), a **recorded
live session from October 15, 2026**. Its source responses from UniProt,
ClinVar, and AlphaFold DB are preserved in
[captures/2026-10-15_tp53_r175h/](captures/2026-10-15_tp53_r175h/).
The capture manifest records request URLs, timestamps, software versions,
raw response digests, and canonical response digests.

The test `tests/contract/test_tp53_capture_binding.py` recomputes
the digests from the stored bytes and verifies that the recorded tool
messages match the capture. Run it from the repository root:

```bash
pytest -q tests/contract/test_tp53_capture_binding.py
```

**Evidence boundary:** Reproducing source bytes does not independently
validate clinical interpretation. A ClinVar germline classification is not
a somatic treatment recommendation, and a global AlphaFold pLDDT is not
residue-specific structural validation.

The former BRCA1, hypothetical future-verification, and TEM-1
illustrative transcripts were withdrawn. They were not source-byte-bound
captures and should not be presented as scientific observations, verified
provenance receipts, or clinical advice.

For a new example, first record the real upstream responses, freeze
their exact source metadata and bytes, add a matching digest-verification
test, and only then publish a source-attributed transcript. If only a
suggested workflow exists, keep it outside the published examples.
