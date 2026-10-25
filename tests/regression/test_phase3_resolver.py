import pytest
import json
import urllib.request
import urllib.error
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scenarios.resolver import DatasetResolver, PathTraversalError
from fastapi import HTTPException


BASE_URL = "http://localhost:8000"


class TestPhase3Resolver:
    """
    Phase 3 Regression Test Suite:
    Verifies centralized dataset discovery, multi-root hierarchy,
    strict path-traversal prevention, and non-regression on live endpoints.
    """

    @pytest.mark.unit
    def test_resolver_root_hierarchy(self):
        """UNIT_TEST: Verify resolver identifies active roots properly."""
        resolver = DatasetResolver()
        assert resolver.active_root.exists()
        assert len(resolver.available_roots) >= 1
        assert "aicte_institutions" in str(resolver.active_root)

    @pytest.mark.unit
    def test_resolver_path_traversal_rejection_on_scenario_id(self):
        """UNIT_TEST: Verify malformed or escaping scenario IDs are strictly rejected."""
        resolver = DatasetResolver()
        malicious_ids = [
            "../etc/passwd",
            "..\\windows\\system32",
            "INST/../../secret",
            "INST-01;rm -rf",
            "INST 01 COMPLIANT",
            "",
        ]
        for bad_id in malicious_ids:
            with pytest.raises((PathTraversalError, HTTPException)) as excinfo:
                resolver.resolve_scenario_path(bad_id)
            assert excinfo.value.status_code == 400

    @pytest.mark.unit
    def test_resolver_path_traversal_rejection_on_document_name(self):
        """UNIT_TEST: Verify malformed or escaping document filenames are strictly rejected."""
        resolver = DatasetResolver()
        malicious_docs = [
            "../secret.txt",
            "..\\boot.ini",
            "sub/doc.pdf",
            "doc.pdf\x00.exe",
            "Fire_Safety_NOC.pdf/../../main.py",
        ]
        for bad_doc in malicious_docs:
            with pytest.raises((PathTraversalError, HTTPException)) as excinfo:
                resolver.resolve_document_path("INST-01-COMPLIANT", bad_doc)
            assert excinfo.value.status_code == 400

    @pytest.mark.unit
    def test_resolver_valid_scenario_resolution(self):
        """UNIT_TEST: Verify valid scenario path resolves cleanly."""
        resolver = DatasetResolver()
        p = resolver.resolve_scenario_path("INST-01-COMPLIANT")
        assert p.exists()
        assert p.is_dir()
        assert (p / "application_metadata.json").exists()

    @pytest.mark.unit
    def test_resolver_valid_document_resolution(self):
        """UNIT_TEST: Verify valid document path resolves cleanly."""
        resolver = DatasetResolver()
        doc_path = resolver.resolve_document_path("INST-01-COMPLIANT", "Land_Title_Deed.pdf")
        assert doc_path.exists()
        assert doc_path.is_file()

    @pytest.mark.integration
    def test_live_api_health_includes_diagnostics(self):
        """API_INTEGRATION_TEST: Verify live healthcheck returns resolver diagnostics."""
        url = f"{BASE_URL}/api/v1/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            diag = data.get("dataset_diagnostics")
            assert diag is not None
            assert "active_root" in diag
            assert diag.get("total_registered_scenarios", 0) >= 15

    @pytest.mark.integration
    def test_live_api_scenarios_listing_dynamic(self):
        """API_INTEGRATION_TEST: Verify live /api/v1/scenarios uses centralized resolver."""
        url = f"{BASE_URL}/api/v1/scenarios"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            scenarios = data.get("scenarios", [])
            assert len(scenarios) >= 15
            ids = [s["scenario_id"] for s in scenarios]
            assert "INST-01-COMPLIANT" in ids
            assert "INST-05-MALFORMED-PAYLOAD" in ids
            assert "INST-15-TAMPER-SIG-INVALID" in ids

    @pytest.mark.integration
    def test_live_document_rendering_unbroken(self):
        """API_INTEGRATION_TEST: Verify live document rendering functions after resolver integration."""
        url = f"{BASE_URL}/api/v1/documents/INST-01-COMPLIANT/Land_Title_Deed.pdf/render?page=1"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            assert res.headers.get("Content-Type") == "image/png"
            data = res.read()
            assert data[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.integration
    def test_live_evaluation_unbroken(self):
        """API_INTEGRATION_TEST: Verify evaluate endpoint runs cleanly with resolver."""
        url = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data["scenario_id"] == "INST-01-COMPLIANT"
            assert len(data.get("findings", [])) >= 5


if __name__ == "__main__":
    pytest.main(["-v", __file__])
