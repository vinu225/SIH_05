# Input-only dataset (v2)

Use this folder as the only dataset path supplied to the system under test. It intentionally omits expected outcomes.

- `cases.json`: 30 input case manifests with relative paths; no expected_* fields.
- `synthetic_institutional_records.json`: synthetic reference records.
- `mock_issuing_authority_responses.json`: synthetic/mock source records.
- `configurable_demo_rules.json`: explicit demo rule settings; none are official AICTE requirements.
- `synthetic_documents/`: text, PDF, image, QR and signature fixtures.
- `manifest_sha256.csv`: SHA-256 hashes for input files except the manifest itself.

All institutions and documents are synthetic. Any mock issuer result is test data only. See the top-level README for validation and evaluation steps.
