# Build and validation report — AICTE PS26261 Improved Test Pack v2

## Build scope
A separate v2 pack was created from the provided 30-case pack. The source ZIP was not modified. `input_data/` is answer-free; `answer_key/` holds expected outcomes.

## Improvements
- Added matching issuer record for SYN-003 without removing the SYN-022 mismatch reference.
- Added byte-identical original/duplicate files for SYN-015.
- Added actual PDF metadata inconsistency for SYN-017.
- Added detached CMS signed payload fixtures: valid/trusted, tampered/invalid, and valid but untrusted. Public test certificates are included; private signing keys are not.
- Added an actual QR PNG plus a PDF containing the QR for SYN-020.
- Added actual generated raster illustrations for infrastructure cases SYN-023 to SYN-025; not real facility photographs.
- Added image-only OCR scan PDFs and PNGs for SYN-013 and SYN-014.
- Added explicit synthetic-only faculty threshold configuration for SYN-026.
- Separated input cases from expected outcomes and added hashes for input and answer-key files.

## Validation status
Validation is executed by the included `tools/validate_dataset.py` and `tools/verify_cms_fixtures.py`. Results are recorded after the actual commands run; do not infer validation success from this report alone.


## Final verification run (2026-10-26)
- Dataset validation: 234/234 checks passed; input manifest has 76 payload entries.
- CMS fixture checks: valid/trusted fixture verified successfully; tampered payload was rejected; valid signature from the untrusted test CA was rejected by the trusted root and accepted only when verified against its own synthetic root.
- QR check: decoded payload from standalone PNG successfully (PASS).
- PDF visual preflight: rendered the metadata PDF, QR certificate PDF, and both image-only OCR PDFs; no blank pages detected.
- PDF inspection: [{"file": "synthetic_documents/applications/AICTE-SYN-017_undertaking_metadata_anomaly.pdf", "pages": 1, "text_layer_chars_page1": 331, "creationDate": "D:20240101000000Z"}, {"file": "synthetic_documents/scanned_ocr/AICTE-SYN-013_application_ocr_ambiguous_scan.pdf", "pages": 1, "text_layer_chars_page1": 0, "creationDate": "D:20261025090000Z"}, {"file": "synthetic_documents/scanned_ocr/AICTE-SYN-014_undertaking_ocr_ambiguous_scan.pdf", "pages": 1, "text_layer_chars_page1": 0, "creationDate": "D:20261025090000Z"}, {"file": "synthetic_documents/identity_and_authority_docs/AICTE-SYN-020_certificate_qr_reference.pdf", "pages": 1, "text_layer_chars_page1": 287, "creationDate": "D:20261025090000Z"}]
- Answer-key manifest: 5 payload entries; both manifests exclude themselves to avoid recursive self-hashing.
- OCR scan fixtures now appear in the input case manifests for SYN-013 and SYN-014. Their PDF pages are image-only (no selectable text); OCR performance still needs to be measured through the system under test.

## Additional answer-leakage and fixture checks
- Outcome-revealing wording was removed from several input text fixtures; filenames for OCR/signature/metadata/duplicate cases were neutralized where appropriate. The actual source facts needed to compute outcomes remain present.
- Added `answer_key/fixture_level_assertions.json` with exact SHA-256 values for the duplicate pair, actual PDF metadata date, QR payload, OCR scan modality, CMS integrity/trust expectations, infrastructure image provenance, and the explicitly synthetic faculty threshold.
- Recomputed input manifest entries: 76 (the input manifest excludes itself).
- Answer key remains outside the input-only archive.


## Final package verification after input neutralization
- Input-only validator: 30 cases, 76 hashed input files, 0 issues.
- Full pack validator: 234/234 checks passed; 76 input payload files are covered by SHA-256 manifest.
- CMS checks: valid/trusted signature passed; changed-payload signature rejected; valid signature from alternate synthetic root rejected under root A and accepted under root C.
- Prediction comparator smoke test: matching 30-row predictions returned exit code 0; a deliberately incorrect field returned exit code 1.
- Input case manifests contain no `expected_*` fields. Outcome labels and detailed fixture assertions remain in the sibling answer key folder and separate answer-key ZIP.
- Input files use neutralized names/text where the earlier fixture directly stated the expected answer.
