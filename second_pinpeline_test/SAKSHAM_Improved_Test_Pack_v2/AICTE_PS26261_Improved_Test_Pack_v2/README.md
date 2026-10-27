# AICTE PS26261 Improved Synthetic Test Pack v2

This is a separate, improved version of the supplementary 30-case AICTE SAKSHAM dataset. The source ZIP is preserved unchanged.

## Layout
- `input_data/` — input files intended for SAKSHAM; contains no expected outcome labels.
- `answer_key/` — separate ground-truth answers and case notes. Do **not** expose this folder to the pipeline, model prompt, RAG index or system being evaluated.
- `tools/` — validation, CMS fixture verification and post-run prediction comparison tools.

## Quick start
1. Extract this archive to a working directory.
2. Point the test adapter or ingestion process only at `input_data/`. Do not recursively ingest the pack root.
3. Evaluate the case IDs from `input_data/cases.json` through the real SAKSHAM pipeline. Save predictions as a CSV matching the schema described by `tools/evaluate_predictions.py`.
4. Run `python tools/validate_dataset.py --root .`.
5. Run `python tools/verify_cms_fixtures.py --root .` where OpenSSL is available.
6. Only after inference finishes, compare predictions against `answer_key/expected_outcomes.csv` using `python tools/evaluate_predictions.py --predictions path/to/predictions.csv --answers answer_key/expected_outcomes.csv`.

## Required prediction CSV
Columns required: `case_id`, `predicted_extraction_status`, `predicted_source_verification_status`, `predicted_anomaly_label`, `predicted_infrastructure_status`, `predicted_workflow_decision`. The evaluator compares these predicted fields against the separate answer key.

## Synthetic-only notice
All institution records, documents, issuer responses, images, signatures and rules are synthetic. Demo rules are QA fixtures—not official AICTE standards. The detached CMS signatures are cryptographic test fixtures and are not embedded PDF signatures; they do not prove a real person's identity. The infrastructure images are generated illustrations, not real photographs.

## Answer-leakage guard
`input_data/cases.json` has case IDs, input paths and metadata only; it contains no `expected_*` fields. Expected statuses and detailed file assertions are in `answer_key/`. Do not recursively index the pack root or expose the answer key to the system under test. Factual mock source responses remain part of input evidence. Several outcome-revealing phrases and filenames from the earlier pack were neutralized.
