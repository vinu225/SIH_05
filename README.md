# AICTE Regulatory Compliance & Application Scrutiny Decision-Support Platform
**Smart India Hackathon (SIH) Prototype**
**Organization:** All India Council for Technical Education (AICTE), Ministry of Education  
**Department:** Regulation Bureau  
**Regulatory Basis:** AICTE Approval Process Handbook (APH 2024–2027)

---

## Quick Start with Docker (Recommended)

Run the entire platform (FastAPI backend + React Scrutiny Validation Portal) in isolated containers with a single command:

```bash
docker compose up --build -d
```

* **AICTE Validation Portal (Frontend):** `http://localhost:3000` (also reachable on `http://localhost:5173`)
* **API Documentation & Swagger UI:** `http://localhost:8000/docs`
* **Backend Healthcheck:** `http://localhost:8000/api/v1/health`

To stop containers:
```bash
docker compose down
```

For live development mode with code hot-reloading:
```bash
docker compose -f docker-compose.dev.yml up --build
```

---

## Quick Start (Running Locally Without Docker)

### 1. Start the FastAPI Backend Service:
```powershell
cd backend
$env:PYTHONPATH="."
python -m uvicorn app.main:app --reload --port 8000
```
* **API Documentation & Swagger UI:** `http://localhost:8000/docs`
* **Healthcheck:** `http://localhost:8000/api/v1/health`

### 2. Start the AICTE Validation Portal (Frontend):
```powershell
cd aicte-validation-portal
npm install
npm run dev
```
* **Interactive Scrutiny Cockpit:** `http://localhost:5173`

### 3. Run Backend Test Suite:
```powershell
$env:PYTHONPATH="backend"
pytest backend/tests/
```

---

## 4 Live Test Demonstrations Available in the UI

1. **`INST-01-COMPLIANT` (Clean Approval):**
   * Meets UG Engineering FSR (1:20), Cadre Ratio (1:2:6), Land Deed matches declared area.
   * Status: **`Requirements Met — Pending Officer Review`**
2. **`INST-02-DATE-ALTERED` (Suspected Document Alteration):**
   * Localized ELA compression anomaly detected on isolated Fire NOC expiry year.
   * Status: **`Unable to Determine — Visual Inconsistency Without Baseline (Officer Review Required)`**
3. **`INST-03-LAND-CADRE-DISCREPANCY` (Regulatory Shortfall):**
   * Declared 5.0 Acres in portal vs. 2.1 Acres documented in registered Title Deed (**2.9 Acre variance**).
   * 0 Professors in department (**Cadre Ratio 1:2:6 deficit**).
   * Status: **`Discrepancy Found`**
4. **`INST-04-UNTRUSTED-QR-GPS` (Issuer Allowlist Failure):**
   * Certificate QR code targets an unauthorized non-government phishing domain.
   * Status: **`Untrusted QR Destination & Advisory: Location unverified`**

---

## Key Features Implemented

* **Authentic APH 2024–2027 Rule Engine:** Versioned JSON rules with exact Annexure 5 (FSR 1:20) and Chapter 1 clause citations.
* **Coordinate Normalization:** CropBox and rotation-aware matrix transforms matching PDF.js rendering.
* **Multi-Signal ELA Forensics:** Non-destructive pixel difference heatmaps as preliminary advisory signals.
* **Hash-Chained Audit Trail:** SHA-256 event-chained append-only log with tamper-detection verification.
* **Transparent Adapters:** Explicit **`[Simulated Verification (Mock Adapter)]`** labeling.
