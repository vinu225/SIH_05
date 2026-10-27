import json
import pytest
import urllib.request
import urllib.error
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.findings import AggregatedStatus, AssessmentPillar, FindingOutcome

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"

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


class TestPhase5FrontendVerification:
    """Verifies frontend UI accessibility, proxy routing, document inspection, and badge consistency."""

    def test_frontend_server_serves_spa(self):
        """Confirm Vite dev server at http://localhost:3000 serves index.html."""
        req = urllib.request.Request(FRONTEND_URL, method="GET")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "<!DOCTYPE html>" in content or "<div id=\"root\">" in content

    def test_frontend_proxy_to_backend_scenarios(self):
        """Confirm Vite proxy forwards /api/v1/scenarios to backend seamlessly."""
        req = urllib.request.Request(f"{FRONTEND_URL}/api/v1/scenarios", method="GET")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            scenarios = data.get("scenarios", [])
            assert len(scenarios) >= 15
            ids = [s["scenario_id"] for s in scenarios]
            for s in ALL_15_SCENARIOS:
                assert s in ids

    @pytest.mark.parametrize("scenario_id", ALL_15_SCENARIOS)
    def test_frontend_evaluation_and_badge_consistency(self, scenario_id):
        """
        For each institution, confirm evaluate API through frontend proxy matches
        backend contract, has proper badges, and never misrepresents status.
        """
        url = f"{FRONTEND_URL}/api/v1/evaluate/{scenario_id}"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))

        # Verify scenario identification
        assert data["scenario_id"] == scenario_id
        meta = data["application_metadata"]
        assert meta["application_id"]
        assert meta["institution_name"]

        # Verify pillar badges exist
        pillars = data["pillar_summaries"]
        for p in ["AUTHENTICITY", "COMPLETENESS", "REGULATORY_COMPLIANCE"]:
            assert p in pillars
            assert pillars[p]["status"] in ["Compliant", "Discrepancy Found", "Requires Officer Review"]

        # Verify clean cases are not flagged as discrepancies
        if scenario_id in ["INST-01-COMPLIANT", "INST-14-CLEAN-CAMPUS"]:
            assert data["overall_status"] == AggregatedStatus.COMPLIANT.value
            for p in pillars.values():
                assert p["status"] == AggregatedStatus.COMPLIANT.value

        # Verify unreadable/unavailable cases are never presented as successful authentication
        if scenario_id in ["INST-03-UNREADABLE-QR", "INST-04-MISSING-QR", "INST-08-SOURCE-UNAVAILABLE", "INST-13-SIG-UNAVAILABLE"]:
            auth_status = pillars["AUTHENTICITY"]["status"]
            assert auth_status == AggregatedStatus.REQUIRES_OFFICER_REVIEW.value

    @pytest.mark.parametrize("scenario_id", ALL_15_SCENARIOS)
    def test_frontend_document_rendering_and_ela_inspection(self, scenario_id):
        """
        Verify evidence inspection action: document rendering and ELA heatmap endpoints
        return valid image streams through the frontend proxy.
        """
        doc_name = "Fire_Safety_NOC.pdf"

        # 1. Page render
        render_url = f"{FRONTEND_URL}/api/v1/documents/{scenario_id}/{doc_name}/render?page=1&dpi=100"
        req_render = urllib.request.Request(render_url, method="GET")
        with urllib.request.urlopen(req_render) as resp_render:
            assert resp_render.status == 200
            assert resp_render.headers.get("content-type") == "image/png"
            img_bytes = resp_render.read()
            assert len(img_bytes) > 1000  # valid PNG binary

        # 2. ELA heatmap overlay
        ela_url = f"{FRONTEND_URL}/api/v1/documents/{scenario_id}/{doc_name}/ela?page=1"
        req_ela = urllib.request.Request(ela_url, method="GET")
        with urllib.request.urlopen(req_ela) as resp_ela:
            assert resp_ela.status == 200
            assert resp_ela.headers.get("content-type") in ["image/jpeg", "image/png"]
            ela_bytes = resp_ela.read()
            assert len(ela_bytes) > 500

        # 3. Document metadata
        meta_url = f"{FRONTEND_URL}/api/v1/documents/{scenario_id}/{doc_name}/meta"
        req_meta = urllib.request.Request(meta_url, method="GET")
        with urllib.request.urlopen(req_meta) as resp_meta:
            assert resp_meta.status == 200
            doc_meta = json.loads(resp_meta.read().decode("utf-8"))
            assert doc_meta["filename"] == doc_name
            assert doc_meta["total_pages"] >= 1
            assert "sha256_hash" in doc_meta
