import pytest
import tempfile
import json
from app.audit.chained_logger import HashChainedAuditLogger


def test_audit_chain_valid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        log_path = tmp.name

    logger = HashChainedAuditLogger(log_file_path=log_path)
    logger.log_event("OFF-01", "SCRUTINY_OFFICER", "EVALUATE_APH_RULE", "APP-101", {"status": "Compliant"})
    logger.log_event("OFF-01", "SCRUTINY_OFFICER", "OFFICER_OVERRIDE", "APP-101", {"reason": "Supplemental deed provided"})

    is_valid, err = logger.verify_chain_integrity()
    assert is_valid is True
    assert err is None


def test_audit_chain_tamper_detected():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        log_path = tmp.name

    logger = HashChainedAuditLogger(log_file_path=log_path)
    logger.log_event("OFF-01", "SCRUTINY_OFFICER", "ACTION_1", "APP-101", {"val": 100})
    logger.log_event("OFF-01", "SCRUTINY_OFFICER", "ACTION_2", "APP-101", {"val": 200})

    # Tamper with file manually
    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data[0]["details"]["val"] = 999  # Tamper!
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Re-instantiate logger and verify
    tampered_logger = HashChainedAuditLogger(log_file_path=log_path)
    is_valid, err = tampered_logger.verify_chain_integrity()
    assert is_valid is False
    assert "Tampered event #1" in err
