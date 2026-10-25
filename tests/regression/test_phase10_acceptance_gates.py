import io
import json
import pytest
import shutil
import urllib.request
from pathlib import Path
import sys
import fitz
import qrcode

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scenarios.resolver import dataset_resolver
from app.schemas.findings import FindingOutcome, AggregatedStatus, AssessmentPillar

BASE_URL = "http://localhost:8000"
UNSEEN_SCENARIO_ID = "INST-TEST-UNSEEN-99"


@pytest.fixture(scope="module")
def unseen_institution_dir():
    """
    Creates a completely unseen institution folder and valid PDF artifacts
    to rigorously verify Principle A (zero hardcoded scenario IDs).
    """
    inst_dir = dataset_resolver.active_root / UNSEEN_SCENARIO_ID
    inst_dir.mkdir(parents=True, exist_ok=True)

    # 1. application_metadata.json
    metadata = {
        "application_id": "APP-2024-UNSEEN-99",
        "institution_name": "Antigravity Institute of Advanced Technology",
        "institution_category": "UG Engineering & Technology",
        "declared_land_acres": 5.0,
        "total_approved_students": 300,
        "created_at": "2026-10-25T12:00:00",
    }
    with open(inst_dir / "application_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # 2. Land_Title_Deed.pdf (5.00 Acres)
    land_pdf = inst_dir / "Land_Title_Deed.pdf"
    doc_land = fitz.open()
    page_land = doc_land.new_page(width=612, height=792)
    page_land.insert_text(
        (50, 72),
        "GOVERNMENT LAND REVENUE DEPARTMENT\n"
        "OFFICIAL TITLE DEED & REVENUE RECORD\n\n"
        "Institution: Antigravity Institute of Advanced Technology\n"
        "Total Registered Land Measure: 5.00 Acres\n"
        "Survey Numbers: 991/1, 991/2\n"
        "Classification: Contiguous Educational Land Parcel\n",
        fontsize=12,
    )
    doc_land.save(str(land_pdf))
    doc_land.close()

    # 3. Faculty_Portfolio.pdf (2 Prof, 4 Assoc, 10 Asst = 16 total, Intake: 300 -> FSR = 18.75 <= 20)
    fac_pdf = inst_dir / "Faculty_Portfolio.pdf"
    doc_fac = fitz.open()
    page_fac = doc_fac.new_page(width=612, height=792)
    page_fac.insert_text(
        (50, 72),
        "FACULTY PORTFOLIO & CADRE STATEMENT\n\n"
        "Institution: Antigravity Institute of Advanced Technology\n"
        "Approved Student Intake: 300\n"
        "Total Registered Teaching Faculty: 16\n\n"
        "Cadre Distribution:\n"
        "- Professors: 2\n"
        "- Associate Professors: 4\n"
        "- Assistant Professors: 10\n",
        fontsize=12,
    )
    doc_fac.save(str(fac_pdf))
    doc_fac.close()

    # 4. Fire_Safety_NOC.pdf (With genuine QR code and valid dates)
    fire_pdf = inst_dir / "Fire_Safety_NOC.pdf"
    doc_fire = fitz.open()
    page_fire = doc_fire.new_page(width=612, height=792)
    page_fire.insert_text(
        (50, 72),
        "STATE FIRE & RESCUE SERVICES DEPARTMENT\n"
        "OFFICIAL FIRE SAFETY COMPLIANCE CERTIFICATE\n\n"
        "Certificate / NOC Reference: NOC-STATE-2024-UNSEEN-99\n"
        "Date of Inspection / Issuance: 01-01-2024\n"
        "To Expiry Date: 31-12-2027\n"
        "Status: Approved and Valid for Educational Occupancy\n",
        fontsize=12,
    )

    # Embed valid QR code pointing to an allowed portal endpoint
    qr_payload = json.dumps({
        "certificate_id": "NOC-STATE-2024-UNSEEN-99",
        "institution_name": "Antigravity Institute of Advanced Technology",
        "expiry_date": "31-12-2027",
        "portal_verification_url": "https://eservices.tn.gov.in/fire/verify/NOC-STATE-2024-UNSEEN-99",
    })
    qr_img = qrcode.make(qr_payload)
    img_byte_arr = io.BytesIO()
    qr_img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    rect = fitz.Rect(400, 100, 520, 220)
    page_fire.insert_image(rect, stream=img_bytes)

    doc_fire.save(str(fire_pdf))
    doc_fire.close()

    yield inst_dir

    # Cleanup after tests
    shutil.rmtree(str(inst_dir), ignore_errors=True)


class TestPhase10AcceptanceGates:
    """Master Acceptance Gate Tests for AICTE SAKSHAM Verification Engine."""

    @pytest.mark.integration
    def test_gate_a_unseen_institution_clean_evaluation(self, unseen_institution_dir):
        """
        Acceptance Gate A:
        A completely unseen institution with zero historical references in the code
        must be ingested, parsed, and evaluated dynamically based purely on physical bytes.
        """
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/evaluate/{UNSEEN_SCENARIO_ID}",
            data=b"",
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())

        # Assert canonical response structure
        assert data["scenario_id"] == UNSEEN_SCENARIO_ID
        assert data["overall_status"] == AggregatedStatus.COMPLIANT.value

        # Assert 3-pillar breakdown
        pillars = data["pillar_summaries"]
        assert pillars["AUTHENTICITY"]["status"] == AggregatedStatus.COMPLIANT.value
        assert pillars["COMPLETENESS"]["status"] == AggregatedStatus.COMPLIANT.value
        assert pillars["REGULATORY_COMPLIANCE"]["status"] == AggregatedStatus.COMPLIANT.value

        # Verify individual findings are all Compliant
        for finding in data["findings"]:
            assert finding["outcome"] == FindingOutcome.COMPLIANT.value, (
                f"Finding '{finding['finding_id']}' unexpectedly failed: {finding['description']}"
            )

    @pytest.mark.integration
    def test_gate_b_content_change_reactivity(self, unseen_institution_dir):
        """
        Acceptance Gate B:
        Modifying document bytes dynamically MUST instantly change evaluation results.
        Mutate Land_Title_Deed.pdf from 5.00 acres to 2.00 acres (3.00 acre deficit).
        """
        land_pdf = unseen_institution_dir / "Land_Title_Deed.pdf"

        # Overwrite Land_Title_Deed.pdf with a 2.00 Acre deficit
        doc_land = fitz.open()
        page_land = doc_land.new_page(width=612, height=792)
        page_land.insert_text(
            (50, 72),
            "GOVERNMENT LAND REVENUE DEPARTMENT\n"
            "OFFICIAL TITLE DEED & REVENUE RECORD\n\n"
            "Institution: Antigravity Institute of Advanced Technology\n"
            "Total Registered Land Measure: 2.00 Acres\n"
            "Survey Numbers: 991/1 (Partial Allocation)\n",
            fontsize=12,
        )
        doc_land.save(str(land_pdf))
        doc_land.close()

        # Re-evaluate scenario
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/evaluate/{UNSEEN_SCENARIO_ID}",
            data=b"",
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())

        # Overall status must reflect Discrepancy Found
        assert data["overall_status"] == AggregatedStatus.DISCREPANCY_FOUND.value

        # Regulatory compliance pillar must reflect discrepancy
        pillars = data["pillar_summaries"]
        assert pillars["REGULATORY_COMPLIANCE"]["status"] == AggregatedStatus.DISCREPANCY_FOUND.value
        assert pillars["REGULATORY_COMPLIANCE"]["discrepancy_count"] >= 1

        # Locate the land deficit finding
        land_finding = next(
            (f for f in data["findings"] if f["applicable_rule"]["rule_id"] == "APH-2024-LAND-DEED-SYNC"),
            None,
        )
        assert land_finding is not None
        assert land_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
        assert "3.00" in land_finding["evidence"]["discrepancy_magnitude"]
        assert "2.00" in str(land_finding["evidence"]["extracted_value"])
