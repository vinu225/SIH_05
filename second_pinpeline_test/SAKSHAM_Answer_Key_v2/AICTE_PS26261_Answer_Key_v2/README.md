# Answer-key-only bundle

Use only after your pipeline has generated predictions. This folder contains expected answers and must not be supplied to the system under test, the LLM prompt, or a RAG index.

- `answer_key/expected_outcomes.csv` — spreadsheet-friendly 30-case expected results.
- `answer_key/expected_outcomes.json` — structured expectations and evidence references.
- `answer_key/fixture_level_assertions.json` — exact hash, metadata, QR, OCR, signature, visual-fixture and configurable-rule assertions.
- `answer_key/signature_fixture_expectations.json` — supplemental detached-CMS expectations.
- `answer_key/CORRECTIONS_AND_KNOWN_LIMITATIONS.md` — corrections and remaining limitations.
- `tools/evaluate_predictions.py` — post-run predictions comparator.

Predictions CSV needs `case_id` and: `predicted_extraction_status`, `predicted_source_verification_status`, `predicted_anomaly_label`, `predicted_infrastructure_status`, `predicted_workflow_decision`. Run:

```bash
python tools/evaluate_predictions.py --predictions results/predictions.csv --answers answer_key/expected_outcomes.csv
```

The test data and expected outcomes are synthetic QA material, not official AICTE regulatory decisions. Detached CMS files test real signature integrity with synthetic test keys/certificates; they are not embedded PDF signature fields or real-world issuer identity verification.
