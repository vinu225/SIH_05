import io
import json
import pytest
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scenarios.resolver import dataset_resolver, PathTraversalError
from app.schemas.findings import AggregatedStatus, AssessmentPillar, FindingOutcome

BASE_URL = "http://localhost:8000"

SCENARIO_SPECS = [
    {
        "index": 1,
        "canonical_id": "INST-01-COMPLIANT",
        "expected_overall": AggregatedStatus.COMPLIANT,
        "expected_auth": AggregatedStatus.COMPLIANT,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Clean baseline conforming to all APH norms",
    },
    {
        "index": 2,
        "canonical_id": "INST-02-QR-ID-MISMATCH",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Certificate ID divergence between printed text and QR payload",
    },
    {
        "index": 3,
        "canonical_id": "INST-03-UNREADABLE-QR",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.DISCREPANCY_FOUND,
        "primary_condition": "Unreadable degraded QR code + 2.9 acre land deficit and 0 professor cadre deficit",
    },
    {
        "index": 4,
        "canonical_id": "INST-04-MISSING-QR",
        "expected_overall": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "expected_auth": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Missing QR code verification block on statutory clearance",
    },
    {
        "index": 5,
        "canonical_id": "INST-05-MALFORMED-PAYLOAD",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Malformed non-JSON corrupt QR payload string",
    },
    {
        "index": 6,
        "canonical_id": "INST-06-EXPIRED-CERT",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.DISCREPANCY_FOUND,
        "primary_condition": "Expired fire safety certificate (validity ended 15-04-2023)",
    },
    {
        "index": 7,
        "canonical_id": "INST-07-REVOKED-STATUS",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Simulated revoked certificate status in issuer records + mock invalid signature",
    },
    {
        "index": 8,
        "canonical_id": "INST-08-SOURCE-UNAVAILABLE",
        "expected_overall": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "expected_auth": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Simulated issuer gateway HTTP 503 timeout / source unavailable",
    },
    {
        "index": 9,
        "canonical_id": "INST-09-HOLDER-MISMATCH",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Holder mismatch: Kalinga Institute vs Metropolitan Institute",
    },
    {
        "index": 10,
        "canonical_id": "INST-10-DUPLICATE-CERT-A",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Duplicate certificate reference collision with INST-11",
    },
    {
        "index": 11,
        "canonical_id": "INST-11-DUPLICATE-CERT-B",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Duplicate certificate reference collision with INST-10",
    },
    {
        "index": 12,
        "canonical_id": "INST-12-TEXT-MISMATCH",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Printed validity (31-12-2028) diverges from QR record (31-12-2022)",
    },
    {
        "index": 13,
        "canonical_id": "INST-13-SIG-UNAVAILABLE",
        "expected_overall": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "expected_auth": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Signature CRL/OCSP authority unavailable",
    },
    {
        "index": 14,
        "canonical_id": "INST-14-CLEAN-CAMPUS",
        "expected_overall": AggregatedStatus.COMPLIANT,
        "expected_auth": AggregatedStatus.COMPLIANT,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.COMPLIANT,
        "primary_condition": "Clean multi-division campus: 5.20 acres, 360 intake, 27 faculty",
    },
    {
        "index": 15,
        "canonical_id": "INST-15-TAMPER-SIG-INVALID",
        "expected_overall": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_auth": AggregatedStatus.DISCREPANCY_FOUND,
        "expected_compl": AggregatedStatus.COMPLIANT,
        "expected_reg": AggregatedStatus.REQUIRES_OFFICER_REVIEW,
        "primary_condition": "Digital signature verification failed + localized ELA compression anomaly",
    },
]


class TestPhase3DatasetAliasResolution:
    """Tests generic alias resolution across canonical IDs and 3-digit, 2-digit, 1-digit aliases."""

    @pytest.mark.parametrize("spec", SCENARIO_SPECS)
    def test_alias_equivalence_and_resolution(self, spec):
        idx = spec["index"]
        canonical = spec["canonical_id"]
        alias_3digit = f"INST-{idx:03d}"
        alias_2digit = f"INST-{idx:02d}"
        alias_1digit = f"INST-{idx}"

        p_canonical = dataset_resolver.resolve_scenario_path(canonical)
        p_3digit = dataset_resolver.resolve_scenario_path(alias_3digit)
        p_2digit = dataset_resolver.resolve_scenario_path(alias_2digit)
        p_1digit = dataset_resolver.resolve_scenario_path(alias_1digit)

        # All aliases must resolve to the identical physical directory
        assert p_canonical == p_3digit == p_2digit == p_1digit
        assert p_canonical.name == canonical
        assert p_canonical.exists()
        assert (p_canonical / "application_metadata.json").exists()

    def test_unknown_identifier_returns_404_without_fallback(self):
        with pytest.raises(Exception) as exc_info:
            dataset_resolver.resolve_scenario_path("INST-999")
        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

        with pytest.raises(Exception) as exc_info2:
            dataset_resolver.resolve_scenario_path("COMPLETELY-UNKNOWN-SCENARIO")
        assert "404" in str(exc_info2.value) or "not found" in str(exc_info2.value).lower()

    def test_path_traversal_rejection(self):
        with pytest.raises(PathTraversalError):
            dataset_resolver.sanitize_identifier("../INST-01-COMPLIANT")
        with pytest.raises(PathTraversalError):
            dataset_resolver.sanitize_identifier("..\\INST-01-COMPLIANT")
        with pytest.raises(PathTraversalError):
            dataset_resolver.sanitize_filename("../secret.key")


class TestPhase3DeterministicEvaluationDate:
    """Verifies parameterized evaluation_date behavior, boundary conditions, and error handling."""

    def test_evaluate_before_expiry_compliant(self):
        # INST-06 certificate expires 15-04-2023. Evaluating before on 2022-01-01 must be Compliant.
        url = f"{BASE_URL}/api/v1/evaluate/INST-06-EXPIRED-CERT?evaluation_date=2022-01-01"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
        assert data["effective_evaluation_date"] == "2022-01-01"

        fire_finding = next(f for f in data["findings"] if f["finding_id"].startswith("FIND-FIRE-"))
        assert fire_finding["outcome"] == FindingOutcome.COMPLIANT.value
        assert "valid until" in fire_finding["description"].lower()

    def test_evaluate_on_expiry_compliant(self):
        # Evaluating on exact expiry date 2023-04-15
        url = f"{BASE_URL}/api/v1/evaluate/INST-06-EXPIRED-CERT?evaluation_date=2023-04-15"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
        assert data["effective_evaluation_date"] == "2023-04-15"

        fire_finding = next(f for f in data["findings"] if f["finding_id"].startswith("FIND-FIRE-"))
        assert fire_finding["outcome"] == FindingOutcome.COMPLIANT.value

    def test_evaluate_after_expiry_discrepancy(self):
        # Evaluating after expiry on 2023-04-16 must produce Discrepancy Found
        url = f"{BASE_URL}/api/v1/evaluate/INST-06-EXPIRED-CERT?evaluation_date=2023-04-16"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
        assert data["effective_evaluation_date"] == "2023-04-16"

        fire_finding = next(f for f in data["findings"] if f["finding_id"].startswith("FIND-FIRE-"))
        assert fire_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
        assert "expired" in fire_finding["description"].lower()

    def test_invalid_evaluation_date_returns_422(self):
        url = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT?evaluation_date=not-a-date"
        req = urllib.request.Request(url, data=b"", method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 422


class TestPhase3All15InstitutionsEndToEnd:
    """Validates complete evaluation across all 15 institutions using short aliases."""

    @pytest.mark.parametrize("spec", SCENARIO_SPECS)
    def test_end_to_end_institution_evaluation(self, spec):
        alias = f"INST-{spec['index']:03d}"
        url = f"{BASE_URL}/api/v1/evaluate/{alias}"
        req = urllib.request.Request(url, data=b"", method="POST")

        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())

        # 1. Canonical scenario resolution
        assert data["scenario_id"] == spec["canonical_id"]
        assert "application_metadata" in data
        assert "effective_evaluation_date" in data

        # 2. Overall workflow status
        assert data["overall_status"] == spec["expected_overall"].value

        # 3. Three distinct pillars
        pillars = data["pillar_summaries"]
        assert AssessmentPillar.AUTHENTICITY.value in pillars
        assert AssessmentPillar.COMPLETENESS.value in pillars
        assert AssessmentPillar.REGULATORY_COMPLIANCE.value in pillars

        assert pillars[AssessmentPillar.AUTHENTICITY.value]["status"] == spec["expected_auth"].value
        assert pillars[AssessmentPillar.COMPLETENESS.value]["status"] == spec["expected_compl"].value
        assert pillars[AssessmentPillar.REGULATORY_COMPLIANCE.value]["status"] == spec["expected_reg"].value

        # 4. Mandatory findings trace & evidence references
        findings = data["findings"]
        assert len(findings) >= 5, f"Expected at least 5 findings for {spec['canonical_id']}"

        for f in findings:
            assert f["finding_id"].startswith("FIND-")
            assert f["assessment_pillar"] in [p.value for p in AssessmentPillar]
            ev = f.get("evidence", {})
            assert ev is not None
            # Check source document reference if present
            if ev.get("source_document_name"):
                assert ev["source_document_name"].endswith((".pdf", "Dossier"))
            if ev.get("page_number"):
                assert isinstance(ev["page_number"], int) and ev["page_number"] >= 1

    def test_unreadable_and_unavailable_are_not_fraud(self):
        # INST-003: Unreadable QR must NOT produce a fraudulent finding, but Unable to Determine
        req_03 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/INST-003", data=b"", method="POST")
        with urllib.request.urlopen(req_03) as resp:
            data_03 = json.loads(resp.read().decode())
        qr_03 = next(f for f in data_03["findings"] if f["finding_id"].startswith("FIND-QR-"))
        assert qr_03["outcome"] == FindingOutcome.UNABLE_TO_DETERMINE.value

        # INST-008: Source unavailable must produce Unable to Determine
        req_08 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/INST-008", data=b"", method="POST")
        with urllib.request.urlopen(req_08) as resp:
            data_08 = json.loads(resp.read().decode())
        qr_08 = next(f for f in data_08["findings"] if f["finding_id"].startswith("FIND-QR-"))
        assert qr_08["outcome"] == FindingOutcome.UNABLE_TO_DETERMINE.value

        # INST-013: Signature authority unavailable must produce Unable to Determine
        req_13 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/INST-013", data=b"", method="POST")
        with urllib.request.urlopen(req_13) as resp:
            data_13 = json.loads(resp.read().decode())
        sig_13 = next(f for f in data_13["findings"] if f["finding_id"].startswith("FIND-SIG-"))
        assert sig_13["outcome"] == FindingOutcome.UNABLE_TO_DETERMINE.value
