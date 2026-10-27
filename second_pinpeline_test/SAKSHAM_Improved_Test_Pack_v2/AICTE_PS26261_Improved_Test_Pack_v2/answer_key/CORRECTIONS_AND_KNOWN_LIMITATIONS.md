# Corrections and Known Limitations — v2

This is an improved synthetic QA pack. It is not official AICTE source material and must not be used to make real approval decisions. The original archive is preserved separately.

## Corrected or added fixtures
- `AICTE-SYN-003`: added matching mock NOC record `SYN-NOC-5003` while preserving `SYN-NOC-5023` for the separate mismatch scenario `AICTE-SYN-022`.
- `AICTE-SYN-015`: added `undertaking_original.txt` and `undertaking_duplicate.txt` with byte-identical content so exact SHA-256 duplicate behavior can be tested.
- `AICTE-SYN-017`: added an actual PDF with PDF CreationDate set to 2024-01-01 while its content states 2026-10-19. This is a metadata inconsistency signal only.
- `AICTE-SYN-018`: added an actual PDF plus detached CMS signature and synthetic trusted test certificate chain. OpenSSL can validate signature integrity and the synthetic trust chain. This is not an embedded PDF signature field or real-world identity authentication.
- `AICTE-SYN-019`: added a signed payload altered after signature generation. Verification should fail because the bytes no longer match the detached CMS signature. An additional valid-but-untrusted signer fixture is included for trust-chain testing.
- `AICTE-SYN-020`: added a real QR PNG and a PDF with the QR embedded. QR payload matches the mock issuer data; this remains a synthetic reference match, not live issuer authentication.
- `AICTE-SYN-023` to `025`: added raster PNG visual fixtures instead of relying only on descriptions. These are generated illustrations, not photographs of real facilities. Visual conclusions should remain conservative.
- `AICTE-SYN-026`: configured explicit threshold 20 for Computer Engineering, explicitly marked as an illustrative QA rule, not an official AICTE standard. The case expects manual review when declared faculty count 18 is below that threshold.
- `AICTE-SYN-013` and `AICTE-SYN-014`: added image-only scanned PDFs/PNG fixtures to test OCR ambiguity (O/0 and 1/i). Some Hindi text is included in the scan; OCR quality should be measured, not assumed.

## Separate input and answer key
- `input_data/` contains only inputs, reference records, demo rules, and document files. It does not include expected outcome fields.
- `answer_key/` contains expected results. Do not index the answer key into an LLM/RAG retriever or submit it to the evaluator under test.
- `tools/evaluate_predictions.py` compares actual predictions with the answer key after the evaluation is complete.

## Remaining limitations
- CMS fixtures are detached CMS signatures over PDF payload bytes. They test real cryptographic integrity and test-CA trust verification, but do not claim an embedded PDF `/ByteRange` signature. A separate PDF-signature field parser would be needed for genuine PAdES-style verification.
- Visual infrastructure files are synthetic illustrations, not real-world photos; they can test image ingestion paths but cannot establish real facility compliance.
- OCR images are synthetic, with known intended text. They are not a substitute for a representative field-collected Hindi/English scan benchmark.
- Rules remain `DEMO-*` and are not official statutory thresholds.
- Some cases such as audit logging/access control require running the appropriate SAKSHAM workflow endpoint and checking audit side effects; file fixtures alone cannot prove endpoint behavior.

## Answer leakage reduction
Input fixture filenames and text were neutralized where the previous versions literally stated expected outcomes (for example, “Expected workflow” or “Expected behavior”). The input case manifest contains no `expected_*` fields. Source-system facts such as a mock registry status remain in the input because they are the evidence to compare against. Use `answer_key/fixture_level_assertions.json` for exact content-hash, metadata, QR, OCR and signature assertions.
