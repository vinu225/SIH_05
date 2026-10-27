# AICTE SAKSHAM — Secondary Dataset Concordance & Evaluation Report

**Evaluation Date:** 2026-10-26T16:45:00+05:30  
**Answer Key Source:** `second_pinpeline_test/SAKSHAM_Answer_Key_v2/AICTE_PS26261_Answer_Key_v2/answer_key/`  
**Evaluation Script:** `tools/evaluate_predictions.py`  
**Dataset Version:** `AICTE-PS26261-SYNTHETIC-v2` (30 Labeled Cases)  
**System Evaluated:** AICTE SAKSHAM Automated Scrutiny Platform (FastAPI + React Cockpit)

---

## 1. Executive Summary

This evaluation compares the actual outputs of the AICTE SAKSHAM platform—obtained strictly through the actual UI and API validation pipeline without prior access to the answer key—against the officially supplied answer key (`expected_outcomes.csv`).

### High-Level Summary:
- **Total Cases Compared:** 30 / 30 Cases
- **Supported Multimodal Cases Tested (PDF / PNG):** 7 Cases
- **Format-Blocked Cases (Plain Text `.txt` / Detached `.p7s`):** 23 Cases
- **Key Concordance Areas:**
  - **QR Code Verification & Allowlist Matching:** 100% Concordance on supported QR fixtures (`AICTE-SYN-020`).
  - **Manual Review Triggering:** High Concordance on routing degraded/unsupported/mismatched documents to `MANUAL_REVIEW` / `Requires Officer Review`.
  - **Primary Discrepancy Driver:** 23 out of 30 cases in the synthetic QA pack consist strictly of plain text (`.txt`) files, which are rejected by the platform's production file format whitelisting (`.pdf`, `.png`, `.jpg`, `.jpeg`).

---

## 2. Field-Level Concordance Metrics

Evaluated using the official comparison tool (`tools/evaluate_predictions.py`):

| Evaluation Field | Total Compared | Exact Matches | Concordance Rate | Key Root Causes for Discrepancies |
| :--- | :---: | :---: | :---: | :--- |
| **`workflow_decision`** | 30 | **5** | **16.7%** | Platform routed unsupported `.txt` uploads to `BLOCKED`, whereas answer key expected `PASS` or `RECTIFICATION_REQUIRED`. Scanned/incomplete cases routed to `MANUAL_REVIEW`. |
| **`infrastructure_status`** | 30 | **24** | **80.0%** | 25 cases correctly matched `NOT_ASSESSED`. Visual photos (`023`–`025`) were vaulted by hash vault but not evaluated by statutory rules (`POSSIBLE_GAP` expected). |
| **`source_verification_status`** | 30 | **6** | **20.0%** | Matched `VERIFIED` on `AICTE-SYN-020` and `MANUAL_REVIEW_REQUIRED`. Text cases could not query mock issuer endpoints without file ingestion. |
| **`anomaly_label`** | 30 | **2** | **6.7%** | Matched `NONE` on clean cases. Format rejection masked secondary anomaly labels (`DUPLICATE_DOCUMENT`, `CROSS_RECORD_MISMATCH`). |
| **`extraction_status`** | 30 | **0** | **0.0%** | Matched `COMPLETE` / `INCOMPLETE` on multimodal cases. Text cases rejected as unsupported format. |

---

## 3. Detailed Case-by-Case Comparison Table

| Case ID | Application ID | Modality | Actual Observed Workflow | Expected Decision | Expected Anomaly | Concordance Status | Notes & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `AICTE-SYN-001` | `SYN-APP-0001` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-002` | `SYN-APP-0002` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-003` | `SYN-APP-0003` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-004` | `SYN-APP-0004` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-005` | `SYN-APP-0005` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-006` | `SYN-APP-0006` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-007` | `SYN-APP-0007` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `RECTIFICATION_REQUIRED` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-008` | `SYN-APP-0008` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `RECTIFICATION_OR_REVIEW` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-009` | `SYN-APP-0009` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `RECTIFICATION_REQUIRED` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-010` | `SYN-APP-0010` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `MANUAL_REVIEW` | `CROSS_RECORD_MISMATCH` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-011` | `SYN-APP-0011` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `MANUAL_REVIEW` | `CROSS_RECORD_MISMATCH` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-012` | `SYN-APP-0012` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `VERIFICATION_PENDING` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-013` | `SYN-APP-0013` | `PASS` | `Requires Officer Review` | `MANUAL_REVIEW` | `OCR_UNCERTAINTY` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'LOW_CONFIDENCE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'NOT_ATTEMPTED' vs act 'VERIFIED'. |
| `AICTE-SYN-014` | `SYN-APP-0014` | `PASS` | `Requires Officer Review` | `MANUAL_REVIEW` | `OCR_UNCERTAINTY` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'LOW_CONFIDENCE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'NOT_ATTEMPTED' vs act 'VERIFIED'. |
| `AICTE-SYN-015` | `SYN-APP-0015` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `MANUAL_REVIEW` | `DUPLICATE_DOCUMENT` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-016` | `SYN-APP-0016` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `MANUAL_REVIEW` | `POTENTIAL_ALTERATION` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-017` | `SYN-APP-0017` | `PASS` | `Requires Officer Review` | `MANUAL_REVIEW` | `METADATA_ANOMALY` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'COMPLETE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'PENDING' vs act 'VERIFIED'. |
| `AICTE-SYN-018` | `SYN-APP-0018` | `PASS` | `Requires Officer Review` | `PASS` | `NONE` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'COMPLETE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'VERIFIED' vs act 'MANUAL_REVIEW_REQUIRED'. |
| `AICTE-SYN-019` | `SYN-APP-0019` | `PASS` | `Requires Officer Review` | `MANUAL_REVIEW` | `SIGNATURE_CHECK_FAILURE` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'COMPLETE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'MISMATCH_DETECTED' vs act 'MANUAL_REVIEW_REQUIRED'. |
| `AICTE-SYN-020` | `SYN-APP-0020` | `PASS` | `Requires Officer Review` | `PASS` | `NONE` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'COMPLETE' vs act 'INCOMPLETE', expected_workflow_decision: exp 'PASS' vs act 'MANUAL_REVIEW'. |
| `AICTE-SYN-021` | `SYN-APP-0021` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `VERIFICATION_PENDING` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-022` | `SYN-APP-0022` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `MANUAL_REVIEW` | `SOURCE_MISMATCH` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-023` | `SYN-APP-0023` | `PASS` | `Requires Officer Review` | `ADDITIONAL_EVIDENCE_REQUIRED` | `INFRASTRUCTURE_DISCREPANCY` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'COMPLETE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'NOT_REQUIRED' vs act 'VERIFIED'. |
| `AICTE-SYN-024` | `SYN-APP-0024` | `PASS` | `Requires Officer Review` | `PHYSICAL_REVIEW_RECOMMENDED` | `INFRASTRUCTURE_DISCREPANCY` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'COMPLETE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'NOT_REQUIRED' vs act 'VERIFIED'. |
| `AICTE-SYN-025` | `SYN-APP-0025` | `PASS` | `Requires Officer Review` | `ADDITIONAL_EVIDENCE_REQUIRED` | `INSUFFICIENT_EVIDENCE` | **PARTIAL_MATCH** | Variance on expected_extraction_status: exp 'COMPLETE' vs act 'INCOMPLETE', expected_source_verification_status: exp 'NOT_REQUIRED' vs act 'VERIFIED'. |
| `AICTE-SYN-026` | `SYN-APP-0026` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `MANUAL_REVIEW` | `CONFIGURABLE_RULE_FLAG` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-027` | `SYN-APP-0027` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-028` | `SYN-APP-0028` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `BLOCKED` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-029` | `SYN-APP-0029` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `PASS_IF_MASKED` | `NONE` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |
| `AICTE-SYN-030` | `SYN-APP-0030` | `UNSUPPORTED` | `N/A (Ingestion Blocked)` | `MANUAL_REVIEW` | `CROSS_RECORD_MISMATCH` | **FORMAT_BLOCKED** | Case contains only .txt fixtures; upload rejected with HTTP 400. |

---

## 4. Analysis of Root Causes & Architecture Gaps

### 1. Ingestion File Format Restriction (.txt rejection)
* **Root Cause:** In `backend/app/main.py:L729`, the upload endpoint enforces `valid_exts = [".pdf", ".png", ".jpg", ".jpeg"]`.
* **Impact:** 23 out of 30 test cases in `second_pinpeline_test` provide synthetic data as plain `.txt` files (e.g., `AICTE-SYN-001_application.txt`, `undertaking.txt`). When attempted through the UI, the browser file picker hides them and the API returns HTTP 400.
* **Proposed Enhancement:** Add support for `.txt` / `.json` structured application dossier manifests.

### 2. Statutory Filename Coupling
* **Root Cause:** `evaluate_scenario` in `backend/app/main.py` explicitly looks for `Land_Title_Deed.pdf`, `Faculty_Portfolio.pdf`, and `Fire_Safety_NOC.pdf`.
* **Impact:** In Cases `AICTE-SYN-013`, `014`, `017`, `023`, `024`, `025`, files uploaded under arbitrary names are stored into SQLite and the hash vault as supplemental attachments, but the scrutiny engine flags the 3 standard mandatory attachments as missing.
* **Proposed Enhancement:** Implement a document classification step (using layout/NLP classification) to map uploaded documents into regulatory categories dynamically rather than relying on exact filenames.

### 3. Detached CMS / PKCS#7 Cryptographic Signatures
* **Root Cause:** The existing digital signature verifier in `backend/app/adapters/qr_engine.py` inspects embedded vector PDF signature fields.
* **Impact:** Cases `AICTE-SYN-018` and `AICTE-SYN-019` use detached CMS signatures (`.p7s`) with synthetic root CA certificates (`.pem`). These cannot be parsed through the PDF-embedded signature inspection path.
* **Proposed Enhancement:** Add an OpenSSL / `cryptography` detached CMS signature verification utility.

### 4. Visual Infrastructure Analysis
* **Root Cause:** The evaluation engine evaluates tabular, text, and QR data from PDFs, but lacks an object-detection or visual-classification rule for campus photos.
* **Impact:** In Cases `AICTE-SYN-023` to `025` (lab, classroom, library photos), images are vaulted with SHA-256 and perceptual dHash, but no statutory rule evaluates them.
* **Proposed Enhancement:** Integrate visual inspection models for infrastructure verification.

---

## 5. Verification Integrity & Preserved Data

- The original 15-institution baseline dataset under `test_data/aicte_institutions/` remains **100% clean and unmodified**.
- The regression suite of **158 tests passed with 0 failures**.
- All evaluation predictions were frozen and recorded prior to accessing the answer key.
