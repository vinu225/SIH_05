# AICTE SAKSHAM — Hardcoding & Generalization Inspection Findings

**Inspection Date:** 2026-10-26T16:35:00+05:30  
**Target Repository:** `c:\Users\vinuj\OneDrive\Desktop\SIH_2`  
**Inspected Components:** FastAPI Backend (`backend/app`), React Frontend Cockpit (`frontend/src/App.tsx`), Document Extractors (`backend/app/ingestion/extractor.py`), Rule Evaluator (`backend/app/rules/evaluator.py`), Scrutiny Resolver (`backend/app/scenarios/resolver.py`).

---

## 1. Executive Summary

A comprehensive, code-level and empirical investigation was performed across both the frontend React client and the backend scrutiny engine to determine whether AICTE SAKSHAM processes applications via **generic, evidence-driven logic** or **hardcoded scenario values and predetermined outcomes**.

### Key Verdict:
1. **Core Verification Engines (Backend): GENERIC & EVIDENCE-DRIVEN.**
   - Mathematical calculations (FSR, Cadre distribution 1:2:6, Land Deed acreage discrepancies), QR payload decoding, ELA forensic compression analysis, and certificate registry collision checks are computed dynamically from actual file contents and extracted numbers.
   - No branches exist in backend production evaluators that check for specific institution names or hardcoded scenario IDs to force a PASS or FAIL.
2. **Frontend UI Cockpit: PARTIAL HARDCODED SCENARIO KEYS DETECTED.**
   - A confirmed hardcoded defect exists in `frontend/src/App.tsx` where sidebar checklist status badges are hardcoded to specific scenario ID strings (`INST-02-DATE-ALTERED`, `INST-03-LAND-CADRE-DISCREPANCY`) instead of dynamically reflecting the backend's real finding records.
3. **Pipeline Ingestion: HARDCODED FILENAME ASSUMPTIONS.**
   - The evaluation pipeline strictly assumes 3 predetermined PDF document filenames (`Land_Title_Deed.pdf`, `Faculty_Portfolio.pdf`, `Fire_Safety_NOC.pdf`). Unfamiliar document naming conventions (such as the secondary dataset's `.txt` fixtures or differently named PDFs) cannot be automatically routed into the core evaluation rules without renaming or classification mapping.

---

## 2. Confirmed Defects & Hardcoded Code Patterns

### Defect 1: Scenario-Keyed Checklist Badges in UI Cockpit
* **File:** `frontend/src/App.tsx`
* **Lines:** 628–645
* **Severity:** **HIGH** (Frontend Visual Hardcoding)
* **Observed Code:**
```tsx
const declarationDocs = [
  {
    id: 'Fire_Safety_NOC',
    title: 'Fire Safety Certificate',
    status: selectedScenario === 'INST-02-DATE-ALTERED' ? 'flagged' : 'ok',
    subtext: selectedScenario === 'INST-02-DATE-ALTERED' ? 'ELA compression anomaly' : 'Valid statutory period',
  },
  {
    id: 'Land_Title_Deed',
    title: 'Land Title Deed',
    status: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'flagged' : 'ok',
    subtext: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'FSI/FAR Discrepancy' : 'FAR norms verified',
  },
  {
    id: 'Faculty_Portfolio',
    title: 'Faculty Portfolio',
    status: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'flagged' : 'ok',
    subtext: selectedScenario === 'INST-03-LAND-CADRE-DISCREPANCY' ? 'FSR 1:30 (Req 1:20)' : 'FSR & Cadre ratio met',
  },
];
```
* **Impact:** When a user selects or creates an unfamiliar scenario (e.g. `AICTE-SYN-013` or any secondary dataset scenario), the sidebar checklist badges default to `ok` ("Valid statutory period", "FAR norms verified", "FSR & Cadre ratio met"), regardless of the actual backend findings returned in the central observation panel.
* **Remediation:** Compute badge status dynamically by filtering `evaluationData.findings` for corresponding rules (e.g. `APH-2024-FIRE-NOC-VALIDITY`, `APH-2024-LAND-DEED-SYNC`, `APH-2024-FSR-ENGG-UG`).

---

### Defect 2: Hardcoded Default Values on New Scenario Ingestion
* **File:** `backend/app/main.py`
* **Lines:** 759–769
* **Severity:** **MEDIUM** (Arbitrary Baseline Ingestion)
* **Observed Code:**
```python
if not meta_path.exists():
    app_meta = {
        "application_id": f"APP-2024-{clean_scenario_id}",
        "institution_name": institution_name or f"Institution ({scenario_id})",
        "institution_category": "UG Engineering & Technology",
        "declared_land_acres": 4.0,
        "total_approved_students": 240,
        "created_at": datetime.now().isoformat(),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(app_meta, f, indent=2)
```
* **Impact:** Registering a new application through the UI automatically assumes `4.0` acres and `240` students. If an applicant uploads documents from an institution with different declared metrics, the evaluator evaluates against `4.0` acres and `240` students rather than prompting the user or extracting declared figures from an application declaration form.
* **Remediation:** Allow users to input declared intake and acreage during registration in the UI modal, or dynamically extract declared fields from the application form.

---

### Defect 3: Fixed Document Filename Expectations
* **File:** `backend/app/main.py`
* **Lines:** 130, 151, 189, 557–562
* **Severity:** **HIGH** (Generalization Limitation)
* **Observed Code:**
```python
land_pdf_path = scenario_dir / "Land_Title_Deed.pdf"
fac_pdf_path = scenario_dir / "Faculty_Portfolio.pdf"
fire_noc_path = scenario_dir / "Fire_Safety_NOC.pdf"
mandatory_docs = [
    ("Land_Title_Deed.pdf", "DOC-LAND-001"),
    ("Faculty_Portfolio.pdf", "DOC-FACULTY-001"),
    ("Fire_Safety_NOC.pdf", "DOC-FIRE-001"),
]
```
* **Impact:** If an institution uploads documents under different naming conventions (e.g., `AICTE-SYN-001_application.txt`, `AICTE-SYN-020_certificate_qr_reference.pdf`, `Title_Deed_Registry_2024.pdf`), the evaluation engine cannot associate them with statutory scrutiny checks unless they are specifically re-mapped to these 3 fixed filenames.

---

## 3. Generalization Capabilities Verified (Dynamic Logic)

### Verification 1: Dynamic Numerical Evaluation
* **Evaluators Tested:** `APHRuleEvaluator.evaluate_land_consistency`, `APHRuleEvaluator.evaluate_fsr`, `APHRuleEvaluator.evaluate_cadre_ratio`.
* **Empirical Evidence:** In `backend/app/rules/evaluator.py`, outcomes are computed using dynamic mathematical expressions:
  - FSR: `required_faculty = int(round(total_students / required_ratio))`
  - Cadre: `if professors == 0 and total_faculty >= 6: DISCREPANCY_FOUND`
  - Land: `diff = round(declared_acres - deed_acres, 2); if diff > 0.05: DISCREPANCY_FOUND`
* **Mutation Reactivity Test:**
  - Tested mutating declared land from 4.5 acres to 6.0 acres in an isolated environment against a 4.5-acre deed.
  - The evaluator immediately changed from `COMPLIANT` to `FindingOutcome.DISCREPANCY_FOUND` with dynamic evidence payload `1.50 Acres discrepancy`. No hardcoded response table was used.

### Verification 2: Dynamic QR Decoding & Allowlist Validation
* **Engine:** `backend/app/adapters/qr_engine.py` (`qr_engine.detect_and_decode_qr`)
* **Empirical Evidence:** Uses OpenCV `cv2.QRCodeDetector` to physically locate and decode QR codes from document raster renders. Checks against authorized domain patterns (`gov.in`, `nic.in`, `state.gov.in`) and validates JSON schema payloads dynamically.

### Verification 3: Cryptographic Integrity & Tamper Detection
* **Vault:** `backend/app/forensics/hash_vault.py`
* **Empirical Evidence:** Every uploaded document is hashed with SHA-256 and visual dHash upon upload and verified before evaluation. Modifying a single byte on disk results in an immediate hash failure in the canonical registry.

---

## 4. Summary Matrix of Potential Hardcoding Risks

| Risk Category | Status | Evidence / Analysis |
| :--- | :---: | :--- |
| **Branches Keyed to Institution IDs** | **ABSENT (Clean)** | Zero branches in `backend/app` check for specific institution IDs to dictate findings. |
| **Predetermined Finding Outcomes** | **ABSENT (Clean)** | All findings in backend evaluators are generated dynamically based on extracted parameters. |
| **Hardcoded Default Scenario Intake/Land** | **CONFIRMED DEFECT** | `backend/app/main.py:L763` defaults to 4.0 acres and 240 students on new case creation. |
| **UI Badges Scenario-Keyed** | **CONFIRMED DEFECT** | `frontend/src/App.tsx:L628-645` ties sidebar badges to `selectedScenario === 'INST-02-...'`. |
| **Fixed Statutory Filenames** | **CONFIRMED LIMITATION** | Evaluator only evaluates files named `Land_Title_Deed.pdf`, `Faculty_Portfolio.pdf`, `Fire_Safety_NOC.pdf`. |
| **File Format Whitelisting** | **CONFIRMED LIMITATION** | UI and backend reject `.txt`, `.p7s`, `.pem` files, preventing ingestion of plain-text test packs. |
| **Generic Mock Response Override** | **ABSENT (Clean)** | Unit test `test_requirement_6_no_generic_mock_override_of_qr_errors` passed; QR errors are never masked by mocks. |
