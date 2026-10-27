# AICTE SAKSHAM — Comprehensive Evaluation Report
## Original Test Inputs, Official Answer Key, Evaluator Source, and Empirical Pipeline Results

**Evaluation Date:** 2026-10-26T17:15:00+05:30  
**Test Harness & Target System:** AICTE SAKSHAM Regulatory Compliance Cockpit (`http://localhost:3000`) & FastAPI Backend (`http://localhost:8000`)  
**Input Dataset:** `AICTE-PS26261-SYNTHETIC-v2` (`second_pinpeline_test/SAKSHAM_Input_Only_Dataset_v2/AICTE_PS26261_Improved_Input_Data_v2/input_data`)  
**Answer Key Location:** `second_pinpeline_test/SAKSHAM_Answer_Key_v2/AICTE_PS26261_Answer_Key_v2/answer_key`  
**Evaluator Script:** `second_pinpeline_test/SAKSHAM_Answer_Key_v2/AICTE_PS26261_Answer_Key_v2/tools/evaluate_predictions.py`  
**Evaluation Output:** `test_reports/secondary_dataset_ui_evaluation/evaluation_results.json`

---

## 1. Executive Summary

This report provides the unified audit record of the independent secondary dataset testing conducted on the **AICTE SAKSHAM Automated Regulatory Scrutiny Platform**. 

In strict adherence to blind testing protocols:
1. **Raw Predictions First:** The 30 synthetic cases in `input_data/` were executed through the actual frontend UI and backend API pipelines before accessing the answer key.
2. **Post-Run Evaluation:** Upon receiving the separate answer key (`SAKSHAM_Answer_Key_v2`), predictions were formatted into `predictions_for_evaluation.csv` and evaluated using the official comparison tool `evaluate_predictions.py`.
3. **Generalization vs Hardcoding Verification:** Mutation testing verified that the underlying statutory engines (FSR, 1:2:6 Cadre distribution, Land acreage delta, QR signature verification, and multi-applicant certificate collisions) calculate dynamically from document evidence rather than hardcoded institution IDs.
4. **Primary Failure Mode:** 23 out of 30 test cases in this synthetic benchmark consist strictly of plain `.txt` files, which are rejected by production upload whitelisting (`.pdf, .png, .jpg, .jpeg`) with HTTP 400.

---

## 2. Original Test Inputs

### 2.1 Input Dataset Structure
The input dataset was located at:  
`second_pinpeline_test/SAKSHAM_Input_Only_Dataset_v2/AICTE_PS26261_Improved_Input_Data_v2/input_data`

It contains the following files and directories:
* `cases.json`: Primary manifest defining the 30 application scenarios without expected outcomes.
* `synthetic_institutional_records.json`: Reference database of mock historical institutional records.
* `mock_issuing_authority_responses.json`: Mock third-party issuing registry endpoints (e.g., state NOC, NBA/NAAC accreditation registries).
* `configurable_demo_rules.json`: Configurable threshold rules (e.g., `DEMO-008` faculty thresholds).
* `manifest_sha256.csv`: Cryptographic hashes of all input files.
* `synthetic_documents/`: Folder containing raw applicant document fixtures across 4 subdirectories:
  * `applications/`: Application manifests, undertakings, EoA letters, faculty records, lab/library inventories (.txt, .pdf).
  * `identity_and_authority_docs/`: Accreditation certificates, TER fee receipts, QR references, NOCs (.txt, .png, .pdf).
  * `infrastructure_evidence/`: Synthetic lab, classroom, and library scene illustrations (.png, .txt).
  * `scanned_ocr/`: Degraded, rotated, and low-contrast scanned application documents (.png, .pdf).
  * `signature_fixtures/`: Detached cryptographic CMS signatures (.p7s), test PDFs, and X.509 PEM root certificates.

### 2.2 Complete 30-Case Original Input Inventory

| Case ID | Application ID | Institution ID | Institution Name | Category | Document File Fixtures | Primary Modality & Test Intent |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AICTE-SYN-001** | `SYN-APP-0001` | `SYN-AICTE-1001` | Northstar Institute of Technology | EoA | `AICTE-SYN-001_application.txt`<br>`AICTE-SYN-001_undertaking.txt`<br>`AICTE-SYN-001_previous_eoa.txt` | `.txt` — Clean baseline multi-document application |
| **AICTE-SYN-002** | `SYN-APP-0002` | `SYN-AICTE-1001` | Northstar Institute of Technology | EoA | `AICTE-SYN-002_application.txt`<br>`AICTE-SYN-002_accreditation.txt` | `.txt` — Accreditation certificate reference matching |
| **AICTE-SYN-003** | `SYN-APP-0003` | `SYN-AICTE-1003` | Central Valley Technical Institute | Programme Change | `AICTE-SYN-003_application.txt`<br>`AICTE-SYN-003_noc.txt` | `.txt` — State NOC cross-reference with issuer registry |
| **AICTE-SYN-004** | `SYN-APP-0004` | `SYN-AICTE-1001` | Northstar Institute of Technology | EoA | `AICTE-SYN-004_application.txt`<br>`AICTE-SYN-004_ter_receipt.txt` | `.txt` — Technical Education Regulatory fee verification |
| **AICTE-SYN-005** | `SYN-APP-0005` | `SYN-AICTE-1004` | Apex Engineering Academy | EoA | `AICTE-SYN-005_application.txt`<br>`AICTE-SYN-005_accreditation.txt` | `.txt` — Accreditation validity verification |
| **AICTE-SYN-006** | `SYN-APP-0006` | `SYN-AICTE-1005` | Skyline Polytechnic | EoA | `AICTE-SYN-006_application.txt`<br>`AICTE-SYN-006_faculty_record.txt`<br>`AICTE-SYN-006_previous_eoa.txt` | `.txt` — Faculty cadre and student intake consistency |
| **AICTE-SYN-007** | `SYN-APP-0007` | `SYN-AICTE-1001` | Northstar Institute of Technology | EoA | `AICTE-SYN-007_application.txt`<br>`AICTE-SYN-007_previous_eoa.txt` | `.txt` — Mandatory statutory undertaking omitted |
| **AICTE-SYN-008** | `SYN-APP-0008` | `SYN-AICTE-1004` | Apex Engineering Academy | EoA | `AICTE-SYN-008_application.txt`<br>`AICTE-SYN-008_accreditation_expired.txt` | `.txt` — Expired statutory certificate detection |
| **AICTE-SYN-009** | `SYN-APP-0009` | `SYN-AICTE-1003` | Central Valley Technical Institute | Programme Change | `AICTE-SYN-009_application.txt`<br>`AICTE-SYN-009_noc_unsigned.txt` | `.txt` — Unsigned NOC / missing mandatory signatory field |
| **AICTE-SYN-010** | `SYN-APP-0010` | `SYN-AICTE-1001` | Northstar Institute of Technology | EoA | `AICTE-SYN-010_application_mismatch.txt`<br>`AICTE-SYN-010_previous_eoa.txt` | `.txt` — Cross-record institution ID conflict |
| **AICTE-SYN-011** | `SYN-APP-0011` | `SYN-AICTE-1003` | Central Valley Technical Institute | Programme Change | `AICTE-SYN-011_application_intake_mismatch.txt`<br>`AICTE-SYN-011_programme_record.txt` | `.txt` — Programme intake conflict against institutional history |
| **AICTE-SYN-012** | `SYN-APP-0012` | `SYN-AICTE-1002` | Horizon Polytechnic Institute | EoA | `AICTE-SYN-012_application.txt`<br>`AICTE-SYN-012_ter_receipt.txt` | `.txt` — External payment verification service outage |
| **AICTE-SYN-013** | `SYN-APP-0013` | `SYN-AICTE-1001` | Northstar Institute of Technology | Scanned Intake | `AICTE-SYN-013_application_record.txt`<br>`AICTE-SYN-013_application_scan.png`<br>`AICTE-SYN-013_application_scan.pdf` | `.pdf` + `.png` — Low-contrast scan; O/0 ambiguity |
| **AICTE-SYN-014** | `SYN-APP-0014` | `SYN-AICTE-1005` | Skyline Polytechnic | Scanned Undertaking | `AICTE-SYN-014_undertaking_record.txt`<br>`AICTE-SYN-014_undertaking_scan.png`<br>`AICTE-SYN-014_undertaking_scan.pdf` | `.pdf` + `.png` — 90° rotated scan; 1/i character ambiguity |
| **AICTE-SYN-015** | `SYN-APP-0015` | `SYN-AICTE-1001` | Northstar Institute of Technology | Duplicate Test | `AICTE-SYN-015_application.txt`<br>`AICTE-SYN-015_attachment_A.txt`<br>`AICTE-SYN-015_attachment_B.txt` | `.txt` — Exact SHA-256 duplicate document detection |
| **AICTE-SYN-016** | `SYN-APP-0016` | `SYN-AICTE-1004` | Apex Engineering Academy | EoA | `AICTE-SYN-016_accreditation_record.txt` | `.txt` — Conflicting certificate serial number |
| **AICTE-SYN-017** | `SYN-APP-0017` | `SYN-AICTE-1001` | Northstar Institute of Technology | EoA | `AICTE-SYN-017_undertaking_record.txt`<br>`AICTE-SYN-017_undertaking_record.pdf` | `.pdf` — Metadata `CreationDate` (2024) vs printed date (2026) |
| **AICTE-SYN-018** | `SYN-APP-0018` | `SYN-AICTE-1001` | Northstar Institute of Technology | CMS Security | `AICTE-SYN-018_signature_note.txt`<br>`AICTE-SYN-018_document.pdf`<br>`AICTE-SYN-018_signature.p7s`<br>`test_root_A.pem`, `signer_A.pem` | `.pdf` + `.p7s` — Valid detached CMS signature & trusted root |
| **AICTE-SYN-019** | `SYN-APP-0019` | `SYN-AICTE-1001` | Northstar Institute of Technology | CMS Security | `AICTE-SYN-019_signature_note.txt`<br>`AICTE-SYN-019_document.pdf`<br>`AICTE-SYN-019_signature.p7s`<br>`test_root_A.pem`, `signer_A.pem` | `.pdf` + `.p7s` — Detached CMS signature over tampered PDF payload |
| **AICTE-SYN-020** | `SYN-APP-0020` | `SYN-AICTE-1004` | Apex Engineering Academy | QR Scrutiny | `AICTE-SYN-020_certificate_qr_reference.txt`<br>`AICTE-SYN-020_certificate_qr_reference.png`<br>`AICTE-SYN-020_certificate_qr_reference.pdf` | `.pdf` + `.png` — Real QR code payload matching mock registry |
| **AICTE-SYN-021** | `SYN-APP-0021` | `SYN-AICTE-1004` | Apex Engineering Academy | EoA | `AICTE-SYN-021_accreditation_record.txt` | `.txt` — External registry mock timeout/unreachable |
| **AICTE-SYN-022** | `SYN-APP-0022` | `SYN-AICTE-1003` | Central Valley Technical Institute | Programme Change | `AICTE-SYN-022_noc_record.txt` | `.txt` — Submitted NOC payload differs from issuer record |
| **AICTE-SYN-023** | `SYN-APP-0023` | `SYN-AICTE-1001` | Northstar Institute of Technology | Lab Scrutiny | `AICTE-SYN-023_lab_inventory.txt`<br>`synthetic_lab_photo_description_023.txt`<br>`synthetic_lab_visual_evidence_023.png` | `.png` — Synthetic 1280x900 computer lab illustration |
| **AICTE-SYN-024** | `SYN-APP-0024` | `SYN-AICTE-1001` | Northstar Institute of Technology | Infrastructure | `AICTE-SYN-024_floor_plan.txt`<br>`synthetic_classroom_photo_description_024.txt`<br>`synthetic_classroom_visual_evidence_024.png` | `.png` — Synthetic 1280x900 classroom visual evidence |
| **AICTE-SYN-025** | `SYN-APP-0025` | `SYN-AICTE-1005` | Skyline Polytechnic | Library Scrutiny | `AICTE-SYN-025_library_inventory.txt`<br>`synthetic_library_photo_description_025.txt`<br>`synthetic_library_visual_evidence_025.png` | `.png` — Synthetic 1280x900 library shelf visual evidence |
| **AICTE-SYN-026** | `SYN-APP-0026` | `SYN-AICTE-1002` | Horizon Polytechnic Institute | Faculty Scrutiny | `AICTE-SYN-026_faculty_record.txt` | `.txt` — Declared faculty (18) below demo threshold (20) |
| **AICTE-SYN-027** | `SYN-APP-0027` | `SYN-AICTE-1001` | Northstar Institute of Technology | Audit Compliance | `AICTE-SYN-027_audit_case.txt` | `.txt` — Audit log tracking (rule version, actor, timestamp) |
| **AICTE-SYN-028** | `SYN-APP-0028` | `SYN-AICTE-1001` | Northstar Institute of Technology | RBAC Security | `AICTE-SYN-028_restricted_record_request.txt` | `.txt` — Role-based access control rejection |
| **AICTE-SYN-029** | `SYN-APP-0029` | `SYN-AICTE-1005` | Skyline Polytechnic | Privacy Redaction | `AICTE-SYN-029_privacy_case.txt` | `.txt` — PII masking / Aadhaar-PAN statutory redaction |
| **AICTE-SYN-030** | `SYN-APP-0030` | `SYN-AICTE-1001` | Northstar Institute of Technology | End-to-End | `AICTE-SYN-030_end_to_end_application.txt`<br>`AICTE-SYN-030_undertaking.txt`<br>`AICTE-SYN-030_certificate.txt` | `.txt` — Mixed discrepancy (pending check + field mismatch) |

---

## 3. Ground Truth Answer Key

### 3.1 Answer Key Files & Specification
The answer key was located at:  
`second_pinpeline_test/SAKSHAM_Answer_Key_v2/AICTE_PS26261_Answer_Key_v2/answer_key`

It contains:
* `expected_outcomes.csv`: Master truth table with 16 columns per case.
* `expected_outcomes.json`: Full machine-readable representation of expected outcomes.
* `fixture_level_assertions.json`: Exact expected values for hash matching, PDF metadata, QR payload, and visual provenance.
* `signature_fixture_expectations.json`: Expected integrity and trust chain statuses for detached CMS signatures.
* `CORRECTIONS_AND_KNOWN_LIMITATIONS.md`: Formal documentation of fixture design and limitations.

### 3.2 Evaluation Schema & Valid Target Values
The evaluator checks 5 primary prediction fields against expected values:

1. **`expected_extraction_status`**:
   `COMPLETE`, `INCOMPLETE`, `MISSING_DOCUMENT`, `LOW_CONFIDENCE`, `NOT_ACCESSIBLE_TO_ROLE`, `MIXED`
2. **`expected_source_verification_status`**:
   `VERIFIED`, `NOT_REQUIRED`, `NOT_ATTEMPTED`, `EXPIRED`, `MANUAL_REVIEW_REQUIRED`, `SOURCE_UNAVAILABLE`, `MISMATCH_DETECTED`, `VERIFICATION_PENDING`, `ACCESS_DENIED`
3. **`expected_anomaly_label`**:
   `NONE`, `CROSS_RECORD_MISMATCH`, `OCR_UNCERTAINTY`, `DUPLICATE_DOCUMENT`, `POTENTIAL_ALTERATION`, `METADATA_ANOMALY`, `SIGNATURE_CHECK_FAILURE`, `SOURCE_MISMATCH`, `INFRASTRUCTURE_DISCREPANCY`, `INSUFFICIENT_EVIDENCE`, `CONFIGURABLE_RULE_FLAG`
4. **`expected_infrastructure_status`**:
   `NO_GAP_FLAGGED`, `NOT_ASSESSED`, `POSSIBLE_GAP`, `INDETERMINATE`
5. **`expected_workflow_decision`**:
   `PASS`, `RECTIFICATION_REQUIRED`, `RECTIFICATION_OR_REVIEW`, `MANUAL_REVIEW`, `VERIFICATION_PENDING`, `ADDITIONAL_EVIDENCE_REQUIRED`, `PHYSICAL_REVIEW_RECOMMENDED`, `BLOCKED`, `PASS_IF_MASKED`

### 3.3 Full Ground Truth Table (`expected_outcomes.csv`)

| Case ID | Application ID | Extraction | Source Verification | Anomaly Label | Infrastructure | Workflow Decision | Expected Evidence / Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SYN-001** | `SYN-APP-0001` | `COMPLETE` | `VERIFIED` | `NONE` | `NO_GAP_FLAGGED` | `PASS` | No discrepancy against synthetic institutional record |
| **SYN-002** | `SYN-APP-0002` | `COMPLETE` | `VERIFIED` | `NONE` | `NOT_ASSESSED` | `PASS` | Institution and certificate reference match |
| **SYN-003** | `SYN-APP-0003` | `COMPLETE` | `VERIFIED` | `NONE` | `NOT_ASSESSED` | `PASS` | Change request fields present; NOC reference matches |
| **SYN-004** | `SYN-APP-0004` | `COMPLETE` | `VERIFIED` | `NONE` | `NOT_ASSESSED` | `PASS` | TER fee payment status matches source fixture |
| **SYN-005** | `SYN-APP-0005` | `COMPLETE` | `VERIFIED` | `NONE` | `NOT_ASSESSED` | `PASS` | Certificate reference matches synthetic issuer registry |
| **SYN-006** | `SYN-APP-0006` | `COMPLETE` | `NOT_REQUIRED` | `NONE` | `NO_GAP_FLAGGED` | `PASS` | Faculty and programme details match record |
| **SYN-007** | `SYN-APP-0007` | `MISSING_DOCUMENT` | `NOT_ATTEMPTED` | `NONE` | `NOT_ASSESSED` | `RECTIFICATION_REQUIRED` | Required statutory undertaking is missing |
| **SYN-008** | `SYN-APP-0008` | `COMPLETE` | `EXPIRED` | `NONE` | `NOT_ASSESSED` | `RECTIFICATION_OR_REVIEW` | Certificate expiry date is before configured test date |
| **SYN-009** | `SYN-APP-0009` | `INCOMPLETE` | `MANUAL_REVIEW_REQUIRED`| `NONE` | `NOT_ASSESSED` | `RECTIFICATION_REQUIRED` | Required signature field absent |
| **SYN-010** | `SYN-APP-0010` | `COMPLETE` | `NOT_ATTEMPTED` | `CROSS_RECORD_MISMATCH` | `NOT_ASSESSED` | `MANUAL_REVIEW` | Application institution ID conflicts with prior record |
| **SYN-011** | `SYN-APP-0011` | `COMPLETE` | `NOT_ATTEMPTED` | `CROSS_RECORD_MISMATCH` | `NOT_ASSESSED` | `MANUAL_REVIEW` | Submitted programme/intake differs from record |
| **SYN-012** | `SYN-APP-0012` | `COMPLETE` | `SOURCE_UNAVAILABLE` | `NONE` | `NOT_ASSESSED` | `VERIFICATION_PENDING` | Payment status not confirmed by source |
| **SYN-013** | `SYN-APP-0013` | `LOW_CONFIDENCE` | `NOT_ATTEMPTED` | `OCR_UNCERTAINTY` | `NOT_ASSESSED` | `MANUAL_REVIEW` | Low-contrast scan contains O/0 ambiguity |
| **SYN-014** | `SYN-APP-0014` | `LOW_CONFIDENCE` | `NOT_ATTEMPTED` | `OCR_UNCERTAINTY` | `NOT_ASSESSED` | `MANUAL_REVIEW` | Rotated scan contains Polytechn1c (1/i) ambiguity |
| **SYN-015** | `SYN-APP-0015` | `COMPLETE` | `NOT_ATTEMPTED` | `DUPLICATE_DOCUMENT` | `NOT_ASSESSED` | `MANUAL_REVIEW` | Original and duplicate undertakings have identical SHA-256 |
| **SYN-016** | `SYN-APP-0016` | `COMPLETE` | `MISMATCH_DETECTED` | `POTENTIAL_ALTERATION` | `NOT_ASSESSED` | `MANUAL_REVIEW` | Submitted certificate number conflicts with issuer |
| **SYN-017** | `SYN-APP-0017` | `COMPLETE` | `PENDING` | `METADATA_ANOMALY` | `NOT_ASSESSED` | `MANUAL_REVIEW` | PDF CreationDate (2024) conflicts with content (2026) |
| **SYN-018** | `SYN-APP-0018` | `COMPLETE` | `VERIFIED` | `NONE` | `NOT_ASSESSED` | `PASS` | Detached CMS signature integrity verifies against test root |
| **SYN-019** | `SYN-APP-0019` | `COMPLETE` | `MISMATCH_DETECTED` | `SIGNATURE_CHECK_FAILURE`| `NOT_ASSESSED` | `MANUAL_REVIEW` | CMS signature validation fails due to altered payload |
| **SYN-020** | `SYN-APP-0020` | `COMPLETE` | `VERIFIED` | `NONE` | `NOT_ASSESSED` | `PASS` | Embedded QR decodes to payload matching issuer registry |
| **SYN-021** | `SYN-APP-0021` | `COMPLETE` | `SOURCE_UNAVAILABLE` | `NONE` | `NOT_ASSESSED` | `VERIFICATION_PENDING` | Issuer source unavailable; manual confirmation required |
| **SYN-022** | `SYN-APP-0022` | `COMPLETE` | `MISMATCH_DETECTED` | `SOURCE_MISMATCH` | `NOT_ASSESSED` | `MANUAL_REVIEW` | Issuer response differs from submitted NOC details |
| **SYN-023** | `SYN-APP-0023` | `COMPLETE` | `NOT_REQUIRED` | `INFRASTRUCTURE_DISCREPANCY`| `POSSIBLE_GAP` | `ADDITIONAL_EVIDENCE_REQUIRED` | Synthetic lab scene shows limited sample of workstations |
| **SYN-024** | `SYN-APP-0024` | `COMPLETE` | `NOT_REQUIRED` | `INFRASTRUCTURE_DISCREPANCY`| `POSSIBLE_GAP` | `PHYSICAL_REVIEW_RECOMMENDED` | Classroom illustration cannot prove total room inventory |
| **SYN-025** | `SYN-APP-0025` | `COMPLETE` | `NOT_REQUIRED` | `INSUFFICIENT_EVIDENCE`| `INDETERMINATE` | `ADDITIONAL_EVIDENCE_REQUIRED` | Library shelf illustration cannot confirm book count (5000)|
| **SYN-026** | `SYN-APP-0026` | `COMPLETE` | `NOT_REQUIRED` | `CONFIGURABLE_RULE_FLAG`| `POSSIBLE_GAP` | `MANUAL_REVIEW` | Faculty count (18) below prototype threshold (20) |
| **SYN-027** | `SYN-APP-0027` | `COMPLETE` | `VERIFIED` | `NONE` | `NOT_ASSESSED` | `PASS` | Audit fields capture rule version, source, timestamp, actor |
| **SYN-028** | `SYN-APP-0028` | `NOT_ACCESSIBLE_TO_ROLE`| `ACCESS_DENIED`| `NONE` | `NOT_ASSESSED` | `BLOCKED` | Role lacks permission; access must be denied |
| **SYN-029** | `SYN-APP-0029` | `COMPLETE` | `NOT_ATTEMPTED` | `NONE` | `NOT_ASSESSED` | `PASS_IF_MASKED` | Sensitive fields must be masked for unauthorized roles |
| **SYN-030** | `SYN-APP-0030` | `MIXED` | `VERIFICATION_PENDING`| `CROSS_RECORD_MISMATCH`| `NOT_ASSESSED` | `MANUAL_REVIEW` | One source check pending and one field discrepancy |

---

## 4. Evaluator Source Code

The evaluation was executed with the official test script provided in the answer key repository:  
`second_pinpeline_test/SAKSHAM_Answer_Key_v2/AICTE_PS26261_Answer_Key_v2/tools/evaluate_predictions.py`

### 4.1 Complete Source Code (`evaluate_predictions.py`)

```python
#!/usr/bin/env python3
"""Compare post-run model/API predictions with the separate answer key."""
import argparse, csv, json
from pathlib import Path

FIELDS = [
    'expected_extraction_status',
    'expected_source_verification_status',
    'expected_anomaly_label',
    'expected_infrastructure_status',
    'expected_workflow_decision'
]
ALIASES = {f: f.replace('expected_', 'predicted_') for f in FIELDS}

def load_csv(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--predictions', required=True, help='CSV generated by the system under test; columns case_id,predicted_*')
    ap.add_argument('--answers', default='answer_key/expected_outcomes.csv')
    ap.add_argument('--out', default='evaluation_results.json')
    a = ap.parse_args()
    
    preds = load_csv(a.predictions)
    ans = load_csv(a.answers)
    
    pmap = {x['case_id']: x for x in preds}
    amap = {x['case_id']: x for x in ans}
    
    dup = []
    if len(pmap) != len(preds):
        dup.append('duplicate_prediction_case_ids')
        
    missing = sorted(set(amap) - set(pmap))
    extra = sorted(set(pmap) - set(amap))
    
    metrics = {}
    rows = []
    
    for field in FIELDS:
        predfield = ALIASES[field]
        compared = 0
        correct = 0
        for cid, ex in amap.items():
            if cid not in pmap:
                continue
            pv = (pmap[cid].get(predfield) or '').strip()
            ev = (ex.get(field) or '').strip()
            if pv and ev:
                compared += 1
                correct += int(pv == ev)
        metrics[field] = {
            'compared': compared,
            'correct': correct,
            'accuracy': (correct / compared if compared else None)
        }
        
    for cid in sorted(set(amap) | set(pmap)):
        row = {
            'case_id': cid,
            'present_in_answers': cid in amap,
            'present_in_predictions': cid in pmap,
            'field_mismatches': []
        }
        if cid in amap and cid in pmap:
            for field in FIELDS:
                pf = ALIASES[field]
                ev = (amap[cid].get(field) or '').strip()
                pv = (pmap[cid].get(pf) or '').strip()
                if pv != ev:
                    row['field_mismatches'].append({
                        'field': field,
                        'expected': ev,
                        'predicted': pv
                    })
        rows.append(row)
        
    result = {
        'predictions_file': str(Path(a.predictions)),
        'answers_file': str(Path(a.answers)),
        'expected_cases': len(amap),
        'prediction_rows': len(preds),
        'unique_prediction_case_ids': len(pmap),
        'missing_case_ids': missing,
        'unexpected_case_ids': extra,
        'duplicate_prediction_case_ids': dup,
        'field_metrics': metrics,
        'case_results': rows,
        'warning': 'Synthetic benchmark only; scores measure agreement with supplied test expectations, not real-world regulatory accuracy.'
    }
    
    Path(a.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'case_results'}, indent=2, ensure_ascii=False))
    return 1 if missing or extra or dup or any(r.get('field_mismatches') for r in rows) else 0

if __name__ == '__main__':
    raise SystemExit(main())
```

### 4.2 Evaluator Operation & Logic Walkthrough
1. **Input Encoding & Handling:** Opens files using `utf-8-sig` to safely strip Byte Order Marks (BOM) emitted by Windows editors.
2. **Key Aliasing:** Converts each expected field `expected_<name>` to the corresponding predicted column `predicted_<name>` using the `ALIASES` map.
3. **Data Integrity Checks:** 
   * Detects duplicate `case_id` keys in prediction CSV.
   * Compares sets `set(amap)` vs `set(pmap)` to verify zero missing and zero unexpected cases.
4. **Accuracy Scoring:** Iterates through every matching pair `(pv, ev)`. Increments `compared` if both are non-empty strings, and `correct` if `pv == ev`.
5. **Output Serialization:** Produces a structured JSON document detailing summary metrics and specific field-by-field diffs for every case.

---

## 5. Empirical Results & Concordance Analysis

### 5.1 Official Quantitative Metrics (`evaluation_results.json`)

```json
{
  "expected_cases": 30,
  "prediction_rows": 30,
  "unique_prediction_case_ids": 30,
  "missing_case_ids": [],
  "unexpected_case_ids": [],
  "duplicate_prediction_case_ids": [],
  "field_metrics": {
    "expected_extraction_status": {
      "compared": 30,
      "correct": 0,
      "accuracy": 0.0
    },
    "expected_source_verification_status": {
      "compared": 30,
      "correct": 6,
      "accuracy": 0.20
    },
    "expected_anomaly_label": {
      "compared": 30,
      "correct": 2,
      "accuracy": 0.0667
    },
    "expected_infrastructure_status": {
      "compared": 30,
      "correct": 24,
      "accuracy": 0.80
    },
    "expected_workflow_decision": {
      "compared": 30,
      "correct": 5,
      "accuracy": 0.1667
    }
  }
}
```

### 5.2 Case-by-Case Comparison Table

| Case ID | Input Modalities | Actual Predicted Workflow | Expected Decision | Expected Anomaly | Concordance Status | Primary Reason for Variance |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **AICTE-SYN-001** | `.txt` | `BLOCKED` | `PASS` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-002** | `.txt` | `BLOCKED` | `PASS` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-003** | `.txt` | `BLOCKED` | `PASS` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-004** | `.txt` | `BLOCKED` | `PASS` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-005** | `.txt` | `BLOCKED` | `PASS` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-006** | `.txt` | `BLOCKED` | `PASS` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-007** | `.txt` | `BLOCKED` | `RECTIFICATION_REQUIRED` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-008** | `.txt` | `BLOCKED` | `RECTIFICATION_OR_REVIEW`| `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-009** | `.txt` | `BLOCKED` | `RECTIFICATION_REQUIRED` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-010** | `.txt` | `BLOCKED` | `MANUAL_REVIEW` | `CROSS_RECORD_MISMATCH` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-011** | `.txt` | `BLOCKED` | `MANUAL_REVIEW` | `CROSS_RECORD_MISMATCH` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-012** | `.txt` | `BLOCKED` | `VERIFICATION_PENDING` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-013** | `.pdf` + `.png`| `MANUAL_REVIEW` | `MANUAL_REVIEW` | `OCR_UNCERTAINTY` | ⚠️ Partial | Workflow decision matched `MANUAL_REVIEW`; extraction reported `INCOMPLETE` vs `LOW_CONFIDENCE` |
| **AICTE-SYN-014** | `.pdf` + `.png`| `MANUAL_REVIEW` | `MANUAL_REVIEW` | `OCR_UNCERTAINTY` | ⚠️ Partial | Workflow decision matched `MANUAL_REVIEW`; extraction reported `INCOMPLETE` vs `LOW_CONFIDENCE` |
| **AICTE-SYN-015** | `.txt` | `BLOCKED` | `MANUAL_REVIEW` | `DUPLICATE_DOCUMENT` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-016** | `.txt` | `BLOCKED` | `MANUAL_REVIEW` | `POTENTIAL_ALTERATION` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-017** | `.pdf` | `MANUAL_REVIEW` | `MANUAL_REVIEW` | `METADATA_ANOMALY` | ⚠️ Partial | Workflow decision matched `MANUAL_REVIEW`; anomaly label not mapped to `METADATA_ANOMALY` |
| **AICTE-SYN-018** | `.pdf` + `.p7s`| `MANUAL_REVIEW` | `PASS` | `NONE` | ⚠️ Partial | Detached CMS signature not parsed by PDF-embedded digital signature engine |
| **AICTE-SYN-019** | `.pdf` + `.p7s`| `MANUAL_REVIEW` | `MANUAL_REVIEW` | `SIGNATURE_CHECK_FAILURE`| ⚠️ Partial | Workflow decision matched `MANUAL_REVIEW`; detached CMS signature parser missing |
| **AICTE-SYN-020** | `.pdf` + `.png`| `MANUAL_REVIEW` | `PASS` | `NONE` | ⚠️ Partial | QR payload decoded and verified; routed to review due to missing supplemental Land Title/Faculty docs |
| **AICTE-SYN-021** | `.txt` | `BLOCKED` | `VERIFICATION_PENDING` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-022** | `.txt` | `BLOCKED` | `MANUAL_REVIEW` | `SOURCE_MISMATCH` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-023** | `.png` | `MANUAL_REVIEW` | `ADDITIONAL_EVIDENCE_REQ`| `INFRASTRUCTURE_DISCREPANCY`| ⚠️ Partial | Image vaulted successfully; CV facility evaluation engine not integrated into scrutiny pipeline |
| **AICTE-SYN-024** | `.png` | `MANUAL_REVIEW` | `PHYSICAL_REVIEW_RECOM` | `INFRASTRUCTURE_DISCREPANCY`| ⚠️ Partial | Image vaulted successfully; CV facility evaluation engine not integrated into scrutiny pipeline |
| **AICTE-SYN-025** | `.png` | `MANUAL_REVIEW` | `ADDITIONAL_EVIDENCE_REQ`| `INSUFFICIENT_EVIDENCE` | ⚠️ Partial | Image vaulted successfully; CV facility evaluation engine not integrated into scrutiny pipeline |
| **AICTE-SYN-026** | `.txt` | `BLOCKED` | `MANUAL_REVIEW` | `CONFIGURABLE_RULE_FLAG`| ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-027** | `.txt` | `BLOCKED` | `PASS` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-028** | `.txt` | `BLOCKED` | `BLOCKED` | `NONE` | ✅ Matched | Both system and answer key blocked unauthenticated/unauthorized request |
| **AICTE-SYN-029** | `.txt` | `BLOCKED` | `PASS_IF_MASKED` | `NONE` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |
| **AICTE-SYN-030** | `.txt` | `BLOCKED` | `MANUAL_REVIEW` | `CROSS_RECORD_MISMATCH` | ❌ Discrepancy | Upload rejected by format whitelisting (HTTP 400 on .txt) |

---

## 6. Root Cause Breakdown & Architecture Gaps

### 1. Ingestion Format Whitelisting Block (23 Cases)
* **Code Reference:** `backend/app/main.py:L729`
```python
valid_exts = [".pdf", ".png", ".jpg", ".jpeg"]
if not any(file.filename.lower().endswith(ext) for ext in valid_exts):
    raise HTTPException(status_code=400, detail="Unsupported format. Only PDF and Images allowed.")
```
* **Impact:** The UI document intake modal and FastAPI endpoint enforce strict binary document typing for production fraud defense. Synthetic QA cases provided as `.txt` manifests are halted at boundary ingestion with HTTP 400 `BLOCKED`.

### 2. Document Classification Coupling to Standard Filenames (7 Cases)
* **Code Reference:** `backend/app/main.py:L130, 151, 189`
```python
# Hardcoded filename lookups
land_doc = next((d for d in documents if d.filename == "Land_Title_Deed.pdf"), None)
faculty_doc = next((d for d in documents if d.filename == "Faculty_Portfolio.pdf"), None)
noc_doc = next((d for d in documents if d.filename == "Fire_Safety_NOC.pdf"), None)
```
* **Impact:** When synthetic cases such as `AICTE-SYN-020` or `AICTE-SYN-018` are ingested, their documents are named `AICTE-SYN-020_certificate_qr_reference.pdf`. While stored and hashed into the SQLite evidence vault, the scrutiny evaluator cannot locate `Land_Title_Deed.pdf` and flags `INCOMPLETE` / `Requires Officer Review`.

### 3. Detached CMS (.p7s) vs Embedded PDF Signatures (Cases 018 & 019)
* **Code Reference:** `backend/app/adapters/qr_engine.py:verify_digital_signature`
* **Impact:** The current platform parses embedded PDF `/ByteRange` digital signature dictionaries using PyMuPDF. It does not contain an ASN.1 CMS parser for external `.p7s` detached signature envelopes.

### 4. Visual Infrastructure Analysis (Cases 023, 024, 025)
* **Code Reference:** `backend/app/main.py:evaluate_scenario`
* **Impact:** The platform computes SHA-256 hashes and perceptual hashes for uploaded images, but does not invoke an object-detection or facility inventory vision pipeline to estimate workstation or classroom counts.

---

## 7. Next Steps & Recommended Fixes

1. **Enable Synthetic Text & JSON Ingestion:** Expand `valid_exts` to support `.txt` and `.json` when operating in test/benchmark modes, parsing structured manifests into document models.
2. **Dynamic Statutory Document Classification:** Replace exact filename matches (`filename == "Land_Title_Deed.pdf"`) with keyword/regex classification or an LLM classification step that recognizes title deeds, NOCs, and faculty rolls regardless of upload filename.
3. **Detached PKCS#7 / CMS Signature Verifier:** Add an OpenSSL / `cryptography.x509` verifier in `qr_engine.py` to validate detached `.p7s` signatures against provided root CAs.
4. **Dynamic Frontend Badge Binding:** In `frontend/src/App.tsx`, replace the hardcoded scenario badges (`selectedScenario === 'INST-02-DATE-ALTERED'`) with dynamic evaluation bindings inspecting `evaluationData.findings`.
