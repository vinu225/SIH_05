import pytest
import json
import urllib.request
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.findings import AggregatedStatus, AssessmentPillar, FindingOutcome

BASE_URL = "http://localhost:8000"


class TestPhase6Aggregation:
    """
    Phase 6 Regression Test Suite:
    Verifies canonical results model, three-pillar taxonomy separation,
    mandatory completeness evaluation, and non-conflating honest status roll-up.
    """

    def test_canonical_result_model_structure(self):
        """Verify endpoint returns CanonicalEvaluationResult schema with 3-pillar breakdown."""
        url = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))

            assert "overall_status" in data
            assert "pillar_summaries" in data
            assert "findings" in data
            assert "evaluated_at" in data

            summaries = data["pillar_summaries"]
            assert "AUTHENTICITY" in summaries
            assert "COMPLETENESS" in summaries
            assert "REGULATORY_COMPLIANCE" in summaries

            # Verify schema of each finding
            for finding in data["findings"]:
                assert "finding_id" in finding
                assert "assessment_pillar" in finding
                assert "outcome" in finding
                assert "evidence" in finding
                assert "confidence_or_uncertainty" in finding
                assert "applicable_rule" in finding

    def test_completeness_pillar_evaluation(self):
        """Verify completeness pillar marks 3/3 attachments compliant on full scenario."""
        url = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            compl_summary = data["pillar_summaries"]["COMPLETENESS"]
            assert compl_summary["status"] == AggregatedStatus.COMPLIANT.value
            assert compl_summary["compliant_count"] >= 1
            assert compl_summary["discrepancy_count"] == 0

    def test_honest_roll_up_compliant(self):
        """Verify fully compliant institution yields overall_status = 'Compliant'."""
        url = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data["overall_status"] == AggregatedStatus.COMPLIANT.value

    def test_honest_roll_up_discrepancy(self):
        """Verify clear violation yields overall_status = 'Discrepancy Found'."""
        # Land & Cadre discrepancy
        url03 = f"{BASE_URL}/api/v1/evaluate/INST-03-LAND-CADRE-DISCREPANCY"
        req03 = urllib.request.Request(url03, method="POST")
        with urllib.request.urlopen(req03, timeout=10) as res:
            assert res.status == 200
            data03 = json.loads(res.read().decode("utf-8"))
            assert data03["overall_status"] == AggregatedStatus.DISCREPANCY_FOUND.value

        # Untrusted QR destination
        url04 = f"{BASE_URL}/api/v1/evaluate/INST-04-UNTRUSTED-QR-GPS"
        req04 = urllib.request.Request(url04, method="POST")
        with urllib.request.urlopen(req04, timeout=10) as res:
            assert res.status == 200
            data04 = json.loads(res.read().decode("utf-8"))
            assert data04["overall_status"] == AggregatedStatus.DISCREPANCY_FOUND.value

    def test_honest_roll_up_requires_officer_review(self):
        """
        Verify missing evidence or advisory visual anomalies roll up
        strictly to 'Requires Officer Review' without inventing defaults or falsely condemning.
        """
        # Missing QR yields Requires Officer Review
        url_miss = f"{BASE_URL}/api/v1/evaluate/INST-04-MISSING-QR"
        req_miss = urllib.request.Request(url_miss, method="POST")
        with urllib.request.urlopen(req_miss, timeout=10) as res:
            assert res.status == 200
            data_miss = json.loads(res.read().decode("utf-8"))
            assert data_miss["overall_status"] == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value
            assert data_miss["pillar_summaries"]["AUTHENTICITY"]["status"] == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value

        # Gateway Unavailable yields Requires Officer Review
        url_unavail = f"{BASE_URL}/api/v1/evaluate/INST-08-SOURCE-UNAVAILABLE"
        req_unavail = urllib.request.Request(url_unavail, method="POST")
        with urllib.request.urlopen(req_unavail, timeout=10) as res:
            assert res.status == 200
            data_unavail = json.loads(res.read().decode("utf-8"))
            assert data_unavail["overall_status"] == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value
            assert data_unavail["pillar_summaries"]["AUTHENTICITY"]["status"] == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value

        # Unreadable QR has Authenticity = Requires Officer Review (while having independent regulatory land deficit)
        url_unread = f"{BASE_URL}/api/v1/evaluate/INST-03-UNREADABLE-QR"
        req_unread = urllib.request.Request(url_unread, method="POST")
        with urllib.request.urlopen(req_unread, timeout=10) as res:
            assert res.status == 200
            data_unread = json.loads(res.read().decode("utf-8"))
            assert data_unread["pillar_summaries"]["AUTHENTICITY"]["status"] == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value

