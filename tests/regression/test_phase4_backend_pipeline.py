import io
import json
import pytest
import shutil
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scenarios.resolver import dataset_resolver
from app.schemas.findings import AggregatedStatus, AssessmentPillar, FindingOutcome

BASE_URL = "http://localhost:8000"

ALL_15_SCENARIOS = [
    "INST-01-COMPLIANT",
    "INST-02-QR-ID-MISMATCH",
    "INST-03-UNREADABLE-QR",
    "INST-04-MISSING-QR",
    "INST-05-MALFORMED-PAYLOAD",
    "INST-06-EXPIRED-CERT",
    "INST-07-REVOKED-STATUS",
    "INST-08-SOURCE-UNAVAILABLE",
    "INST-09-HOLDER-MISMATCH",
    "INST-10-DUPLICATE-CERT-A",
    "INST-11-DUPLICATE-CERT-B",
    "INST-12-TEXT-MISMATCH",
    "INST-13-SIG-UNAVAILABLE",
    "INST-14-CLEAN-CAMPUS",
    "INST-15-TAMPER-SIG-INVALID",
]


class TestPhase4BackendPipeline:
    """End-to-end testing of the complete backend verification pipeline across all 15 cases."""

    def test_requirement_1_and_2_load_and_evaluate_via_normal_api(self):
        """Points 1 & 2: Ingest and evaluate all 15 scenarios strictly via the normal API HTTP path."""
        for scenario_id in ALL_15_SCENARIOS:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{scenario_id}", data=b"", method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode())
                assert data["scenario_id"] == scenario_id
                assert "pillar_summaries" in data
                assert "findings" in data
                assert "overall_status" in data

    def test_requirement_3_and_4_traceable_evidence_and_stable_finding_ids(self):
        """Points 3 & 4: Confirm stable finding IDs, meaningful explanations, and traceable evidence."""
        for scenario_id in ALL_15_SCENARIOS:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{scenario_id}", data=b"", method="POST")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())

            for finding in data["findings"]:
                # Stable finding ID
                assert finding["finding_id"].startswith("FIND-")
                assert len(finding["finding_id"]) > 10

                # Meaningful explanation
                assert finding["title"] and len(finding["title"]) >= 3
                assert finding["description"] and len(finding["description"]) >= 10

                # Traceable evidence
                evidence = finding.get("evidence", {})
                assert evidence is not None

                # For non-dossier findings, check document reference
                if finding["assessment_pillar"] in [AssessmentPillar.REGULATORY_COMPLIANCE.value, AssessmentPillar.AUTHENTICITY.value]:
                    if evidence.get("source_document_name"):
                        assert evidence["source_document_name"].endswith((".pdf", ".png"))
                        assert evidence.get("page_number") is not None
                        assert evidence["page_number"] >= 1

                # If outcome is Discrepancy, must have extracted_value
                if finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value:
                    assert evidence.get("extracted_value") is not None, f"Missing extracted_value for {finding['finding_id']}"

    def test_requirement_5_honest_uncertain_and_review_required_status(self):
        """Point 5: Ambiguous, unreadable, or unavailable evidence produces honest review-required outcomes."""
        cases = [
            ("INST-03-UNREADABLE-QR", "FIND-QR-UNREADABLE-", FindingOutcome.UNABLE_TO_DETERMINE.value),
            ("INST-04-MISSING-QR", "FIND-QR-MISSING-", FindingOutcome.REQUIRED_EVIDENCE_MISSING.value),
            ("INST-08-SOURCE-UNAVAILABLE", "FIND-QR-UNAVAILABLE-", FindingOutcome.UNABLE_TO_DETERMINE.value),
            ("INST-13-SIG-UNAVAILABLE", "FIND-SIG-UNAVAILABLE-", FindingOutcome.UNABLE_TO_DETERMINE.value),
            ("INST-15-TAMPER-SIG-INVALID", "FIND-FIRE-", FindingOutcome.UNABLE_TO_DETERMINE.value),
        ]
        for scenario_id, prefix, expected_outcome in cases:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{scenario_id}", data=b"", method="POST")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())

            target_finding = next((f for f in data["findings"] if f["finding_id"].startswith(prefix)), None)
            assert target_finding is not None, f"Expected finding with prefix {prefix} in {scenario_id}"
            assert target_finding["outcome"] == expected_outcome, f"Expected {expected_outcome} for {target_finding['finding_id']}"

    def test_requirement_6_no_generic_mock_override_of_qr_errors(self):
        """Point 6: An error in QR processing cannot be overridden by a generic mock response."""
        qr_error_scenarios = [
            "INST-02-QR-ID-MISMATCH",
            "INST-03-UNREADABLE-QR",
            "INST-04-MISSING-QR",
            "INST-05-MALFORMED-PAYLOAD",
            "INST-07-REVOKED-STATUS",
            "INST-08-SOURCE-UNAVAILABLE",
            "INST-09-HOLDER-MISMATCH",
            "INST-12-TEXT-MISMATCH",
        ]
        for scenario_id in qr_error_scenarios:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{scenario_id}", data=b"", method="POST")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
            auth_status = data["pillar_summaries"]["AUTHENTICITY"]["status"]
            assert auth_status != AggregatedStatus.COMPLIANT.value, f"{scenario_id} AUTHENTICITY must not be Compliant"

    def test_requirement_7_three_pillars_remain_separate(self):
        """Point 7: Pillars remain separate and a finding in one does not erase a failure in another."""
        # INST-03: Regulatory has discrepancy, Authenticity has review required
        req_03 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/INST-03-UNREADABLE-QR", data=b"", method="POST")
        with urllib.request.urlopen(req_03) as resp:
            data_03 = json.loads(resp.read().decode())
        ps_03 = data_03["pillar_summaries"]
        assert ps_03["REGULATORY_COMPLIANCE"]["status"] == AggregatedStatus.DISCREPANCY_FOUND.value
        assert ps_03["AUTHENTICITY"]["status"] == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value
        assert ps_03["COMPLETENESS"]["status"] == AggregatedStatus.COMPLIANT.value

        # INST-06: Both Regulatory and Authenticity independently record discrepancies
        req_06 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/INST-06-EXPIRED-CERT", data=b"", method="POST")
        with urllib.request.urlopen(req_06) as resp:
            data_06 = json.loads(resp.read().decode())
        ps_06 = data_06["pillar_summaries"]
        assert ps_06["REGULATORY_COMPLIANCE"]["status"] == AggregatedStatus.DISCREPANCY_FOUND.value
        assert ps_06["AUTHENTICITY"]["status"] == AggregatedStatus.DISCREPANCY_FOUND.value
        assert ps_06["COMPLETENESS"]["status"] == AggregatedStatus.COMPLIANT.value

        # INST-15: Authenticity has discrepancy, Regulatory has review required
        req_15 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/INST-15-TAMPER-SIG-INVALID", data=b"", method="POST")
        with urllib.request.urlopen(req_15) as resp:
            data_15 = json.loads(resp.read().decode())
        ps_15 = data_15["pillar_summaries"]
        assert ps_15["AUTHENTICITY"]["status"] == AggregatedStatus.DISCREPANCY_FOUND.value
        assert ps_15["REGULATORY_COMPLIANCE"]["status"] == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value
        assert ps_15["COMPLETENESS"]["status"] == AggregatedStatus.COMPLIANT.value

    def test_requirement_8_repeated_evaluations_are_idempotent(self):
        """Point 8: Repeated evaluations produce identical findings and statuses when documents are unchanged."""
        test_cases = ["INST-01-COMPLIANT", "INST-03-UNREADABLE-QR", "INST-10-DUPLICATE-CERT-A", "INST-14-CLEAN-CAMPUS"]
        for scenario_id in test_cases:
            req1 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{scenario_id}", data=b"", method="POST")
            with urllib.request.urlopen(req1) as resp1:
                data1 = json.loads(resp1.read().decode())

            req2 = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{scenario_id}", data=b"", method="POST")
            with urllib.request.urlopen(req2) as resp2:
                data2 = json.loads(resp2.read().decode())

            assert data1["overall_status"] == data2["overall_status"]
            assert data1["pillar_summaries"] == data2["pillar_summaries"]
            assert len(data1["findings"]) == len(data2["findings"])
            for f1, f2 in zip(data1["findings"], data2["findings"]):
                assert f1["finding_id"] == f2["finding_id"]
                assert f1["outcome"] == f2["outcome"]

    def test_requirement_9_invalid_identifier_never_loads_baseline(self):
        """Point 9: Unknown scenario IDs return HTTP 404 rather than silently loading INST-01-COMPLIANT."""
        invalid_ids = ["INST-999", "INVALID-SCENARIO", "INST-9999", "NOT-A-REAL-INSTITUTION"]
        for bad_id in invalid_ids:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{bad_id}", data=b"", method="POST")
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 404
            err_body = json.loads(exc_info.value.read().decode())
            assert "not found" in err_body["detail"].lower()
            assert bad_id in err_body["detail"]

    def test_requirement_10_isolated_copy_mutation_detection(self):
        """Point 10: Verify reactive document evaluation on an isolated copy without mutating registered files."""
        # Create an isolated temporary copy in a temporary test scenario folder
        clean_src = dataset_resolver.active_root / "INST-01-COMPLIANT"
        temp_scenario_id = "INST-TEST-ISOLATED-MUTATION-99"
        temp_dir = dataset_resolver.active_root / temp_scenario_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy all files
            for item in clean_src.iterdir():
                if item.is_file():
                    shutil.copy2(item, temp_dir / item.name)

            # Mutate metadata in isolated copy to introduce an intentional land deficit (e.g. declared 10.0 acres)
            meta_path = temp_dir / "application_metadata.json"
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["application_id"] = f"APP-2024-{temp_scenario_id}"
            meta["declared_land_acres"] = 10.0  # Physical deed has 4.5 acres, creating a 5.5-acre discrepancy
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

            # Evaluate isolated copy through API
            req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/{temp_scenario_id}", data=b"", method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode())

            # Verify that the mutated isolated copy reacted dynamically
            assert data["overall_status"] == AggregatedStatus.DISCREPANCY_FOUND.value
            land_finding = next(f for f in data["findings"] if f["finding_id"].startswith("FIND-LAND-"))
            assert land_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
            assert "10.0" in str(land_finding["evidence"]["compared_against"])
            assert "4.5" in str(land_finding["evidence"]["extracted_value"])

            # Clean up isolated copy registration from certificate_registry before checking clean baseline
            from app.db.database import LocalDatabaseManager
            db = LocalDatabaseManager()
            with db.get_connection() as conn:
                conn.cursor().execute("DELETE FROM certificate_registry WHERE scenario_id = ?", (temp_scenario_id,))
                conn.commit()

            # Verify baseline INST-01-COMPLIANT was completely unaffected
            req_clean = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT", data=b"", method="POST")
            with urllib.request.urlopen(req_clean) as resp_clean:
                clean_data = json.loads(resp_clean.read().decode())
            assert clean_data["overall_status"] == AggregatedStatus.COMPLIANT.value

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            from app.db.database import LocalDatabaseManager
            db = LocalDatabaseManager()
            with db.get_connection() as conn:
                conn.cursor().execute("DELETE FROM certificate_registry WHERE scenario_id = ?", (temp_scenario_id,))
                conn.commit()
