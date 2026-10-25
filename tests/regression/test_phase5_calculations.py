import pytest
import json
import urllib.request
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ingestion.extractor import PyMuPDFExtractor
from app.rules.evaluator import APHRuleEvaluator
from app.schemas.findings import FindingOutcome, AssessmentPillar
from app.scenarios.resolver import dataset_resolver

BASE_URL = "http://localhost:8000"


@pytest.fixture
def evaluator():
    return APHRuleEvaluator()


class TestPhase5Calculations:
    """
    Phase 5 Regression Test Suite:
    Verifies dynamic land and faculty extraction from PDF documents,
    removal of invented defaults, adherence to APH norm calculations,
    and live API evaluation.
    """

    def test_dynamic_land_extraction_inst01(self):
        """Verify dynamic land acreage extraction on INST-01 (4.50 Acres)."""
        scenario_path = dataset_resolver.resolve_scenario_path("INST-01-COMPLIANT")
        land_pdf = scenario_path / "Land_Title_Deed.pdf"
        assert land_pdf.exists()

        data = PyMuPDFExtractor.extract_land_deed_data(str(land_pdf))
        assert data["registered_acres"] == 4.5
        assert data["normalized_bbox"] is not None
        assert data["page_number"] == 1

    def test_dynamic_land_extraction_inst03(self):
        """Verify dynamic land acreage extraction on INST-03 (2.10 Acres)."""
        scenario_path = dataset_resolver.resolve_scenario_path("INST-03-LAND-CADRE-DISCREPANCY")
        land_pdf = scenario_path / "Land_Title_Deed.pdf"
        assert land_pdf.exists()

        data = PyMuPDFExtractor.extract_land_deed_data(str(land_pdf))
        assert data["registered_acres"] == 2.1
        assert data["normalized_bbox"] is not None

    def test_dynamic_faculty_extraction_inst01(self):
        """Verify dynamic faculty count extraction on INST-01 (2 Prof, 4 Assoc Prof, 12 Asst Prof)."""
        scenario_path = dataset_resolver.resolve_scenario_path("INST-01-COMPLIANT")
        fac_pdf = scenario_path / "Faculty_Portfolio.pdf"
        assert fac_pdf.exists()

        data = PyMuPDFExtractor.extract_faculty_roster_data(str(fac_pdf))
        assert data["professors"] == 2
        assert data["assoc_professors"] == 4
        assert data["asst_professors"] == 12
        assert data["total_faculty"] == 18
        assert data["normalized_bbox"] is not None

    def test_dynamic_faculty_extraction_inst03(self):
        """Verify dynamic faculty count extraction on INST-03 (0 Prof, 2 Assoc Prof, 14 Asst Prof)."""
        scenario_path = dataset_resolver.resolve_scenario_path("INST-03-LAND-CADRE-DISCREPANCY")
        fac_pdf = scenario_path / "Faculty_Portfolio.pdf"
        assert fac_pdf.exists()

        data = PyMuPDFExtractor.extract_faculty_roster_data(str(fac_pdf))
        assert data["professors"] == 0
        assert data["assoc_professors"] == 2
        assert data["asst_professors"] == 14
        assert data["total_faculty"] == 16

    def test_evaluator_missing_evidence_honesty(self, evaluator):
        """Verify no invented defaults: missing values yield REQUIRED_EVIDENCE_MISSING."""
        res_land = evaluator.evaluate_land_consistency(
            application_id="TEST-MISSING",
            declared_acres=4.0,
            deed_acres=None,
        )
        assert res_land.outcome == FindingOutcome.REQUIRED_EVIDENCE_MISSING

        res_fsr = evaluator.evaluate_fsr(
            application_id="TEST-MISSING",
            program_category="ENGINEERING_AND_TECHNOLOGY",
            level="UG",
            total_students=240,
            total_faculty=None,
        )
        assert res_fsr.outcome == FindingOutcome.REQUIRED_EVIDENCE_MISSING

        res_cadre = evaluator.evaluate_cadre_ratio(
            application_id="TEST-MISSING",
            professors=None,
            assoc_professors=2,
            asst_professors=10,
        )
        assert res_cadre.outcome == FindingOutcome.REQUIRED_EVIDENCE_MISSING

    def test_fsr_intake_tiers(self, evaluator):
        """Verify standard APH norm calculations across various student intake tiers."""
        # 180 intake: requires round(180/20) = 9
        r180_pass = evaluator.evaluate_fsr("T180", "ENGINEERING_AND_TECHNOLOGY", "UG", 180, 9)
        assert r180_pass.outcome == FindingOutcome.COMPLIANT
        r180_fail = evaluator.evaluate_fsr("T180", "ENGINEERING_AND_TECHNOLOGY", "UG", 180, 8)
        assert r180_fail.outcome == FindingOutcome.DISCREPANCY_FOUND

        # 300 intake: requires round(300/20) = 15
        r300_pass = evaluator.evaluate_fsr("T300", "ENGINEERING_AND_TECHNOLOGY", "UG", 300, 15)
        assert r300_pass.outcome == FindingOutcome.COMPLIANT
        r300_fail = evaluator.evaluate_fsr("T300", "ENGINEERING_AND_TECHNOLOGY", "UG", 300, 14)
        assert r300_fail.outcome == FindingOutcome.DISCREPANCY_FOUND

        # 360 intake: requires round(360/20) = 18
        r360_pass = evaluator.evaluate_fsr("T360", "ENGINEERING_AND_TECHNOLOGY", "UG", 360, 18)
        assert r360_pass.outcome == FindingOutcome.COMPLIANT

    def test_live_api_scenario_evaluation_dynamic(self):
        """Verify live FastAPI /api/v1/evaluate/{id} endpoint dynamically computes land and cadre."""
        # Test INST-01
        url01 = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT"
        req01 = urllib.request.Request(url01, method="POST")
        with urllib.request.urlopen(req01, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            land = next(f for f in findings if "LAND" in f["finding_id"])
            assert land["outcome"] == FindingOutcome.COMPLIANT.value
            cadre = next(f for f in findings if "CADRE" in f["finding_id"])
            assert cadre["outcome"] == FindingOutcome.COMPLIANT.value

        # Test INST-03
        url03 = f"{BASE_URL}/api/v1/evaluate/INST-03-LAND-CADRE-DISCREPANCY"
        req03 = urllib.request.Request(url03, method="POST")
        with urllib.request.urlopen(req03, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            land = next(f for f in findings if "LAND" in f["finding_id"])
            assert land["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
            assert "2.9" in land["evidence"]["discrepancy_magnitude"]
            cadre = next(f for f in findings if "CADRE" in f["finding_id"])
            assert cadre["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
