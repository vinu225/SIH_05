import pytest
import json
import urllib.request
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.database import LocalDatabaseManager
from app.schemas.findings import FindingOutcome
from app.scenarios.resolver import dataset_resolver

BASE_URL = "http://localhost:8000"


class TestPhase2Registry:
    """
    Phase 2 Regression Test Suite:
    Verifies cross-application certificate registry, registration,
    authoritative duplicate/collision detection, and live API evaluation.
    """

    def test_certificate_registry_table_schema(self):
        """Verify certificate_registry table is properly initialized in SQLite."""
        db = LocalDatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(certificate_registry);")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}
            assert "certificate_id" in columns
            assert "application_id" in columns
            assert "scenario_id" in columns
            assert "institution_name" in columns

    def test_certificate_collision_logic(self):
        """Verify collision detection distinguishes same-applicant vs other-applicant."""
        db = LocalDatabaseManager()
        cert_id = "TEST-UNIT-CERT-999"

        # Register under App 1
        db.register_certificate(
            certificate_id=cert_id,
            application_id="APP-UNIT-001",
            scenario_id="INST-UNIT-01",
            institution_name="Alpha Tech",
        )

        # Same application should NOT report collision
        col_same = db.check_certificate_collision(cert_id, "APP-UNIT-001")
        assert len(col_same) == 0

        # Different application MUST report collision
        col_diff = db.check_certificate_collision(cert_id, "APP-UNIT-002")
        assert len(col_diff) == 1
        assert col_diff[0]["application_id"] == "APP-UNIT-001"
        assert col_diff[0]["institution_name"] == "Alpha Tech"

    def test_dataset_duplicate_certificate_indexed(self):
        """Verify dataset seed captures duplicate certificate TEST-FIRE-DUPLICATE-777."""
        db = LocalDatabaseManager()
        db.seed_certificate_registry(dataset_resolver)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM certificate_registry WHERE certificate_id = 'TEST-FIRE-DUPLICATE-777'")
            rows = cursor.fetchall()
            assert len(rows) >= 2
            app_ids = [r["application_id"] for r in rows]
            assert any("INST-10" in a for a in app_ids)
            assert any("INST-11" in a for a in app_ids)

    def test_live_api_duplicate_collision_finding(self):
        """Verify live evaluate endpoint detects cross-application certificate reuse on INST-10 and INST-11."""
        # Test INST-10
        url10 = f"{BASE_URL}/api/v1/evaluate/INST-10-DUPLICATE-CERT-A"
        req10 = urllib.request.Request(url10, method="POST")
        with urllib.request.urlopen(req10, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            col_finding = next((f for f in findings if "FIND-CERT-COLLISION" in f["finding_id"]), None)
            assert col_finding is not None
            assert col_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value
            assert col_finding["assessment_pillar"] == "AUTHENTICITY"
            assert "duplicate" in col_finding["title"].lower()

        # Test INST-11
        url11 = f"{BASE_URL}/api/v1/evaluate/INST-11-DUPLICATE-CERT-B"
        req11 = urllib.request.Request(url11, method="POST")
        with urllib.request.urlopen(req11, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            col_finding = next((f for f in findings if "FIND-CERT-COLLISION" in f["finding_id"]), None)
            assert col_finding is not None
            assert col_finding["outcome"] == FindingOutcome.DISCREPANCY_FOUND.value

        # Test Compliant (INST-01) has NO collision
        url01 = f"{BASE_URL}/api/v1/evaluate/INST-01-COMPLIANT"
        req01 = urllib.request.Request(url01, method="POST")
        with urllib.request.urlopen(req01, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            findings = data.get("findings", [])
            col_finding = next((f for f in findings if "FIND-CERT-COLLISION" in f["finding_id"]), None)
            assert col_finding is None
