import pytest
import json
import urllib.request
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.adapters.qr_engine import qr_engine, QRStatus, SignatureStatus
from app.schemas.findings import FindingOutcome, AssessmentPillar
from app.scenarios.resolver import dataset_resolver

BASE_URL = "http://localhost:8000"


class TestPhase1QREngine:
    """
    Phase 1 Regression Test Suite:
    Verifies dynamic QR code decoding, payload schema validation,
    destination allowlist verification, and digital signature inspection
    across actual document PDFs without hardcoded scenario IDs.
    """

    def test_dynamic_qr_compliant(self):
        """Verify dynamic decoding of authentic QR payload on INST-01."""
        pdf_path = dataset_resolver.resolve_document_path("INST-01-COMPLIANT", "Fire_Safety_NOC.pdf")
        res = qr_engine.detect_and_decode_qr(str(pdf_path))
        assert res.status == QRStatus.DECODED_PAYLOAD
        assert res.parsed_payload.get("certificate_id") == "TEST-FIRE-2024-001"
        assert res.is_trusted_destination is True

    def test_dynamic_qr_unreadable(self):
        """Verify blurred/degraded QR yields UNREADABLE_QR on INST-03-UNREADABLE-QR."""
        pdf_path = dataset_resolver.resolve_document_path("INST-03-UNREADABLE-QR", "Fire_Safety_NOC.pdf")
        res = qr_engine.detect_and_decode_qr(str(pdf_path))
        assert res.status == QRStatus.UNREADABLE
        assert "unreadable" in res.error_details.lower() or "blurred" in res.error_details.lower()

    def test_dynamic_qr_missing(self):
        """Verify document with no QR yields MISSING_QR on INST-04-MISSING-QR."""
        pdf_path = dataset_resolver.resolve_document_path("INST-04-MISSING-QR", "Fire_Safety_NOC.pdf")
        res = qr_engine.detect_and_decode_qr(str(pdf_path))
        assert res.status == QRStatus.MISSING

    def test_dynamic_qr_malformed(self):
        """Verify corrupted payload yields MALFORMED_PAYLOAD on INST-05-MALFORMED-PAYLOAD."""
        pdf_path = dataset_resolver.resolve_document_path("INST-05-MALFORMED-PAYLOAD", "Fire_Safety_NOC.pdf")
        res = qr_engine.detect_and_decode_qr(str(pdf_path))
        assert res.status == QRStatus.MALFORMED
        assert "CORRUPT_PAYLOAD" in res.raw_text

    def test_dynamic_qr_untrusted_destination(self):
        """Verify untrusted domain fails allowlist on INST-04-UNTRUSTED-QR-GPS."""
        pdf_path = dataset_resolver.resolve_document_path("INST-04-UNTRUSTED-QR-GPS", "Fire_Safety_NOC.pdf")
        res = qr_engine.detect_and_decode_qr(str(pdf_path))
        assert res.status == QRStatus.DECODED_URL
        assert res.is_trusted_destination is False
        assert "untrusted-external-domain.biz" in res.raw_text

    def test_dynamic_qr_revoked_status(self):
        """Verify revoked status extracted from QR on INST-07-REVOKED-STATUS."""
        pdf_path = dataset_resolver.resolve_document_path("INST-07-REVOKED-STATUS", "Fire_Safety_NOC.pdf")
        res = qr_engine.detect_and_decode_qr(str(pdf_path))
        assert res.status == QRStatus.DECODED_PAYLOAD
        assert res.parsed_payload.get("verification_status") == "REVOKED"

    def test_dynamic_signature_inspection(self):
        """Verify signature states: VALID, INVALID, UNAVAILABLE across scenarios."""
        # Valid signature
        p_valid = dataset_resolver.resolve_document_path("INST-01-COMPLIANT", "Fire_Safety_NOC.pdf")
        sig_valid = qr_engine.inspect_digital_signatures(str(p_valid))
        assert sig_valid.status == SignatureStatus.VALID

        # Invalid / tampered signature
        p_invalid = dataset_resolver.resolve_document_path("INST-15-TAMPER-SIG-INVALID", "Fire_Safety_NOC.pdf")
        sig_invalid = qr_engine.inspect_digital_signatures(str(p_invalid))
        assert sig_invalid.status == SignatureStatus.INVALID

        # Unavailable signature authority
        p_unavail = dataset_resolver.resolve_document_path("INST-13-SIG-UNAVAILABLE", "Fire_Safety_NOC.pdf")
        sig_unavail = qr_engine.inspect_digital_signatures(str(p_unavail))
        assert sig_unavail.status == SignatureStatus.UNAVAILABLE

    def test_live_api_dynamic_qr_evaluation(self):
        """Verify live evaluate endpoint correctly generates findings for QR & signatures dynamically."""
        # Test INST-04-UNTRUSTED-QR-GPS
        url04 = f"{BASE_URL}/api/v1/evaluate/INST-04-UNTRUSTED-QR-GPS"
        req04 = urllib.request.Request(url04, method="POST")
        with urllib.request.urlopen(req04, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            qr_finding = next(f for f in findings if "FIND-QR-UNTRUSTED" in f["finding_id"])
            assert qr_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
            assert qr_finding["assessment_pillar"] == "AUTHENTICITY"

        # Test INST-05-MALFORMED-PAYLOAD
        url05 = f"{BASE_URL}/api/v1/evaluate/INST-05-MALFORMED-PAYLOAD"
        req05 = urllib.request.Request(url05, method="POST")
        with urllib.request.urlopen(req05, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            qr_finding = next(f for f in findings if "FIND-QR-MALFORMED" in f["finding_id"])
            assert qr_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value

        # Test INST-15-TAMPER-SIG-INVALID
        url15 = f"{BASE_URL}/api/v1/evaluate/INST-15-TAMPER-SIG-INVALID"
        req15 = urllib.request.Request(url15, method="POST")
        with urllib.request.urlopen(req15, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            sig_finding = next(f for f in findings if "FIND-SIG-INVALID" in f["finding_id"])
            assert sig_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
