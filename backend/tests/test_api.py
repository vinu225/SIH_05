import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["rules_edition"] == "AICTE Approval Process Handbook 2024-2027"


def test_get_rules():
    res = client.get("/api/v1/rules")
    assert res.status_code == 200
    rules = res.json()["rules"]
    assert len(rules) >= 5
    rule_ids = [r["rule_id"] for r in rules]
    assert "APH-2024-FSR-ENGG-UG" in rule_ids
    assert "APH-2024-LAND-DEED-SYNC" in rule_ids


def test_evaluate_compliant_scenario():
    res = client.post("/api/v1/evaluate/INST-01-COMPLIANT")
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_id"] == "INST-01-COMPLIANT"
    findings = data["findings"]
    assert len(findings) >= 3
    # All findings should be compliant
    for f in findings:
        assert f["outcome"] == "Compliant"


def test_evaluate_land_cadre_discrepancy():
    res = client.post("/api/v1/evaluate/INST-03-LAND-CADRE-DISCREPANCY")
    assert res.status_code == 200
    findings = res.json()["findings"]
    outcomes = [f["outcome"] for f in findings]
    assert "Discrepancy Found" in outcomes


def test_evaluate_untrusted_qr():
    res = client.post("/api/v1/evaluate/INST-04-UNTRUSTED-QR-GPS")
    assert res.status_code == 200
    findings = res.json()["findings"]
    titles = [f["title"] for f in findings]
    assert "Untrusted QR Issuer Destination" in titles


def test_audit_trail_endpoint():
    res = client.get("/api/v1/audit/trail")
    assert res.status_code == 200
    data = res.json()
    assert data["chain_integrity_valid"] is True
    assert data["total_events"] > 0


def test_db_stats():
    res = client.get("/api/v1/db/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["database_type"] == "SQLite 3 Relational Database"
    tables = data["tables"]
    assert tables["institutions"] >= 4
    assert tables["documents"] >= 12
    assert tables["aph_rules"] >= 5

