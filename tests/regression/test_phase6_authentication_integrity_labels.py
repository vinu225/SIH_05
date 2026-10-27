import sys
from pathlib import Path
import json
import urllib.request
import pytest

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.findings import FindingOutcome, AssessmentPillar

BASE_URL = "http://localhost:8000"


def fetch_evaluation(scenario_id: str):
    url = f"{BASE_URL}/api/v1/evaluate/{scenario_id}"
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode("utf-8"))


class TestPhase6AuthenticationAndIntegrityLabels:
    """
    Phase 6 Verification Suite:
    Ensures clear distinctions between:
      - QR decoding
      - QR payload/document field matching
      - File integrity checks
      - Digital signature verification
      - Issuer authentication
      - Regulatory compliance assessment
    Ensures simulated fixtures, allowlist matches, and mock issuer endpoints are honestly labeled.
    Ensures visual anomalies are never interpreted as proof of fraud.
    """

    def test_qr_payload_match_labeling(self):
        """INST-01-COMPLIANT: QR payload match should be labeled as simulated / allowlist validated, not cryptographic issuer authentication."""
        data = fetch_evaluation("INST-001")
        findings = data.get("findings", [])
        qr_f = next((f for f in findings if f["finding_id"].startswith("FIND-QR-VERIFIED-")), None)
        assert qr_f is not None
        assert "(Simulated Verification / Allowlist Validated)" in qr_f["title"]
        assert "not live cryptographic government authentication" in qr_f["description"].lower()
        assert "(Simulated)" in qr_f["evidence"]["extracted_value"]

    def test_digital_signature_valid_simulated_label(self):
        """INST-01-COMPLIANT: Valid signature fixture should be explicitly labeled (Simulated Fixture)."""
        data = fetch_evaluation("INST-001")
        findings = data.get("findings", [])
        sig_f = next((f for f in findings if f["finding_id"].startswith("FIND-SIG-VALID-")), None)
        assert sig_f is not None
        assert "(Simulated Fixture)" in sig_f["title"]
        assert "Simulated fixture verification only" in sig_f["description"]
        assert "(Simulated Fixture)" in sig_f["evidence"]["extracted_value"]

    def test_digital_signature_invalid_simulated_label(self):
        """INST-15: Signature verification failure should be explicitly labeled (Simulated Fixture)."""
        data = fetch_evaluation("INST-015")
        findings = data.get("findings", [])
        sig_f = next((f for f in findings if f["finding_id"].startswith("FIND-SIG-INVALID-")), None)
        assert sig_f is not None
        assert "(Simulated Fixture)" in sig_f["title"]
        assert "simulated test fixture" in sig_f["description"].lower()
        assert "MOCK_INVALID (Simulated Fixture)" in sig_f["evidence"]["extracted_value"]

    def test_digital_signature_unavailable_simulated_label(self):
        """INST-13: Unavailable signature service should be explicitly labeled (Simulated Fixture)."""
        data = fetch_evaluation("INST-013")
        findings = data.get("findings", [])
        sig_f = next((f for f in findings if f["finding_id"].startswith("FIND-SIG-UNAVAILABLE-")), None)
        assert sig_f is not None
        assert "(Simulated Fixture)" in sig_f["title"]
        assert "Simulated test fixture returned manual verification required" in sig_f["description"]
        assert "MANUAL_VERIFICATION_REQUIRED (Simulated Fixture)" in sig_f["evidence"]["extracted_value"]

    def test_revoked_issuer_record_simulated_label(self):
        """INST-07: Revoked certificate status should be labeled (Simulated)."""
        data = fetch_evaluation("INST-007")
        findings = data.get("findings", [])
        rev_f = next((f for f in findings if f["finding_id"].startswith("FIND-QR-REVOKED-")), None)
        assert rev_f is not None
        assert "(Simulated)" in rev_f["title"]
        assert "(Simulated Authority Record)" in rev_f["description"]
        assert "(Simulated Issuer Record)" in rev_f["evidence"]["extracted_value"]

    def test_expired_issuer_record_simulated_label(self):
        """INST-06: Expired certificate in issuer records should be labeled (Simulated)."""
        data = fetch_evaluation("INST-006")
        findings = data.get("findings", [])
        exp_f = next((f for f in findings if f["finding_id"].startswith("FIND-QR-EXPIRED-")), None)
        assert exp_f is not None
        assert "(Simulated)" in exp_f["title"]
        assert "[Simulated Record]" in exp_f["evidence"]["extracted_value"]

    def test_unavailable_issuer_gateway_simulated_label(self):
        """INST-08: Unavailable gateway should be labeled (Simulated)."""
        data = fetch_evaluation("INST-008")
        findings = data.get("findings", [])
        unavail_f = next((f for f in findings if f["finding_id"].startswith("FIND-QR-UNAVAILABLE-")), None)
        assert unavail_f is not None
        assert "(Simulated)" in unavail_f["title"]
        assert "(Simulated Gateway)" in unavail_f["evidence"]["extracted_value"]

    def test_untrusted_qr_domain_label(self):
        """Untrusted QR destination should fail allowlist check without claiming fraudulent identity."""
        data = fetch_evaluation("INST-04-UNTRUSTED-QR-GPS")
        findings = data.get("findings", [])
        untrusted_f = next((f for f in findings if f["finding_id"].startswith("FIND-QR-UNTRUSTED-")), None)
        assert untrusted_f is not None
        assert untrusted_f["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
        assert "not present in the authorized trusted-issuer allowlist" in untrusted_f["description"]
        assert "fraud" not in untrusted_f["description"].lower()

    def test_visual_forensics_anomaly_not_called_fraud(self):
        """Verify that visual ELA anomalies in main.py evaluation pipeline are classified as Visual Inconsistency Without Baseline, not fraud."""
        main_py = Path(__file__).resolve().parent.parent.parent / "backend" / "app" / "main.py"
        content = main_py.read_text(encoding="utf-8")
        assert 'fire_finding.title = "Visual Inconsistency Detected Without Baseline"' in content
        assert 'fire_finding.outcome = FindingOutcome.UNABLE_TO_DETERMINE' in content
        idx = content.find("Visual Inconsistency")
        assert "fraud" not in content[idx:idx+400].lower()

    def test_frontend_file_integrity_label_distinction(self):
        """Verify frontend/src/App.tsx explicitly labels SHA-256 box as File Integrity (SHA-256 Hash)."""
        app_tsx_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "App.tsx"
        content = app_tsx_path.read_text(encoding="utf-8")
        assert "File Integrity (SHA-256 Hash)" in content
