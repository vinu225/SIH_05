import pytest
import json
import urllib.request
import urllib.error
from pathlib import Path
import sys

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scenarios.registry import ScenarioRegistry, CanonicalScenarioEntry, DocumentInventoryItem


BASE_URL = "http://localhost:8000"
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DATASET_DIR = WORKSPACE_ROOT / "test_data" / "aicte_institutions"


class TestPhase0Baseline:
    """
    Phase 0 Regression Test Suite:
    Captures baseline operational integrity of live backend API,
    scenario loading, document rendering, and canonical scenario registry.
    """

    @pytest.mark.integration
    def test_live_api_healthcheck(self):
        """API_INTEGRATION_TEST: Verify live backend healthcheck endpoint."""
        url = f"{BASE_URL}/api/v1/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data.get("status") == "healthy"
            assert "AICTE" in data.get("service", "")

    @pytest.mark.integration
    def test_live_api_scenarios_loading(self):
        """API_INTEGRATION_TEST: Verify scenario loading endpoint returns valid scenarios."""
        url = f"{BASE_URL}/api/v1/scenarios"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            scenarios = data.get("scenarios", [])
            assert len(scenarios) > 0, "Expected at least 1 registered scenario"
            app_ids = [s["application_id"] for s in scenarios]
            assert "APP-2024-INST-01-COMPLIANT" in app_ids

    @pytest.mark.integration
    def test_live_document_rendering(self):
        """API_INTEGRATION_TEST: Verify document rendering endpoint returns valid PNG image."""
        url = f"{BASE_URL}/api/v1/documents/INST-01-COMPLIANT/Land_Title_Deed.pdf/render?page=1"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            content_type = res.headers.get("Content-Type")
            assert content_type == "image/png"
            image_bytes = res.read()
            assert len(image_bytes) > 1000, "Rendered page must not be empty"
            # Verify PNG magic bytes
            assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n", "Rendered output must have valid PNG magic header"

    @pytest.mark.integration
    def test_live_application_evaluation(self):
        """API_INTEGRATION_TEST: Verify application evaluation returns 5 finding records."""
        url = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data.get("scenario_id") == "INST-01-COMPLIANT"
            findings = data.get("findings", [])
            assert len(findings) >= 5, f"Expected at least 5 finding records, got {len(findings)}"
            outcomes = [f["outcome"] for f in findings]
            assert all(o == "Compliant" for o in outcomes), "INST-01-COMPLIANT findings must all be Compliant"

    @pytest.mark.unit
    def test_scenario_registry_discovery(self):
        """UNIT_TEST: Verify canonical registry discovers institutions and builds document inventory."""
        registry = ScenarioRegistry()
        count = registry.discover_scenarios(TEST_DATASET_DIR)
        assert count == 15, f"Expected exactly 15 discovered institutions, got {count}"
        
        inst_01 = registry.get("INST-01-COMPLIANT")
        assert inst_01 is not None
        assert inst_01.application_id == "APP-2024-INST-01-COMPLIANT"
        assert "Land_Title_Deed.pdf" in inst_01.document_inventory
        assert "Fire_Safety_NOC.pdf" in inst_01.document_inventory

    @pytest.mark.unit
    def test_scenario_input_hash_verification(self):
        """UNIT_TEST: Verify input hash verification succeeds on genuine files."""
        registry = ScenarioRegistry()
        registry.discover_scenarios(TEST_DATASET_DIR)
        
        check_result = registry.verify_scenario_inputs("INST-01-COMPLIANT")
        assert check_result["valid"] is True, f"Integrity check failed: {check_result.get('discrepancies')}"
        assert len(check_result["discrepancies"]) == 0

    @pytest.mark.unit
    def test_scenario_conflict_detection_prevents_silent_overwrite(self):
        """UNIT_TEST: Verify duplicate scenario registration with divergent path raises ValueError."""
        registry = ScenarioRegistry()
        entry_a = CanonicalScenarioEntry(
            scenario_id="TEST-COLLISION-01",
            institution_id="INST-A",
            application_id="APP-A",
            institution_name="Alpha College",
            source_directory="C:/path/alpha",
            application_metadata_path="C:/path/alpha/meta.json",
        )
        entry_b = CanonicalScenarioEntry(
            scenario_id="TEST-COLLISION-01",
            institution_id="INST-B",
            application_id="APP-B",
            institution_name="Beta College",
            source_directory="C:/path/beta",
            application_metadata_path="C:/path/beta/meta.json",
        )
        registry.register(entry_a)
        with pytest.raises(ValueError) as excinfo:
            registry.register(entry_b, allow_override=False)
        assert "Scenario conflict detected" in str(excinfo.value)
        assert len(registry.get_conflicts()) == 1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
