# AICTE SAKSHAM — Regression Test Summary

**Date & Time:** 2026-10-26T16:30:00+05:30  
**Environment:** Windows 11, Python 3.14 (Virtual Environment `.\venv`), FastAPI 0.162.0, PyMuPDF 2.0, OpenCV 5.0.0.93  
**Test Runner:** `pytest 9.1.1`  
**Working Directory:** `C:\Users\vinuj\OneDrive\Desktop\SIH_2`

---

## 1. Execution Command & Summary

```powershell
set PYTHONPATH=backend
venv\Scripts\pytest.exe tests\regression -v
```

| Metric | Result |
| :--- | :--- |
| **Total Tests Collected** | **158** |
| **Passed** | **158** (100%) |
| **Failed** | **0** |
| **Skipped** | **0** |
| **Warnings** | **38** (PytestUnknownMarkWarning for un-registered `@pytest.mark.unit` / `@pytest.mark.integration`) |
| **Total Duration** | **302.62s (5 min 02s)** |
| **Status** | **SUCCESS (ALL GATES PASSED)** |

---

## 2. Test Suite Breakdown

| Test Suite File | Tests | Passed | Failures | Focus Area |
| :--- | :---: | :---: | :---: | :--- |
| `tests/regression/test_phase0_baseline.py` | 2 | 2 | 0 | Input SHA-256 hash verification & cross-root conflict prevention |
| `tests/regression/test_phase10_acceptance_gates.py` | 2 | 2 | 0 | Unseen institution clean evaluation & content mutation reactivity |
| `tests/regression/test_phase11_ollama_copilot.py` | 8 | 8 | 0 | Copilot system prompt guardrails, context packaging & chat models |
| `tests/regression/test_phase1_qr_engine.py` | 12 | 12 | 0 | Dynamic QR detection, decode allowlist, tamper detection & digital signatures |
| `tests/regression/test_phase2_registry.py` | 9 | 9 | 0 | SQLite certificate registry schema, multi-applicant collision detection |
| `tests/regression/test_phase3_all_15_institutions.py` | 40 | 40 | 0 | Complete 15-institution ground truth concordance & deterministic date testing |
| `tests/regression/test_phase3_resolver.py` | 9 | 9 | 0 | Path-traversal rejection, safe identifier sanitization, dataset diagnostics |
| `tests/regression/test_phase4_backend_pipeline.py` | 10 | 10 | 0 | Live HTTP API evaluation, idempotency, traceability, non-override of QR errors |
| `tests/regression/test_phase4_upload_frontend.py` | 4 | 4 | 0 | Extension whitelisting, upload traversal defense, 404 safety |
| `tests/regression/test_phase5_calculations.py` | 10 | 10 | 0 | Cadre ratio calculations, FSR thresholds, land deed variances |
| `tests/regression/test_phase5_frontend_verification.py` | 32 | 32 | 0 | Frontend UI proxying, badge consistency, document rendering & ELA inspection |
| `tests/regression/test_phase6_aggregation.py` | 5 | 5 | 0 | Canonical 3-pillar result model, honest status roll-up logic |
| `tests/regression/test_phase6_authentication_integrity_labels.py` | 6 | 6 | 0 | Explicit simulated fixture labeling & non-governmental claims |
| `tests/regression/test_phase7_multilingual.py` | 7 | 7 | 0 | Bilingual English/Hindi OCR token extraction & normalizer |
| `tests/regression/test_phase8_audit_verifier.py` | 6 | 6 | 0 | Cryptographic audit log chaining, tamper detection & CLI verifier |
| `tests/regression/test_phase9_security.py` | 8 | 8 | 0 | Role-based access control, officer override permissions, public viewer read-only |

---

## 3. Dataset Integrity Reconfirmation

- All 15 original scenario dossiers under `test_data/aicte_institutions/` (`INST-01-COMPLIANT` through `INST-15-TAMPER-SIG-INVALID`) remained completely intact and unmodified during testing.
- SHA-256 hashes of all baseline PDF documents and metadata files match `test_data/aicte_institutions/dataset_manifest.json`.
- SQLite database `backend/data/aicte_scrutiny.db` and the cryptographic audit trail remained uncorrupted.
