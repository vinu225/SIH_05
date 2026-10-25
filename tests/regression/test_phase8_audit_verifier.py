import json
import pytest
import subprocess
import sys
import tempfile
import sqlite3
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.audit.chained_logger import HashChainedAuditLogger
from app.audit.verifier import AuditChainVerifier, AuditVerificationReport


@pytest.fixture
def temp_audit_file():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def temp_sqlite_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


class TestPhase8AuditVerifier:
    """Regression test suite for Phase 8 Independent Audit Chain Verifier."""

    @pytest.mark.unit
    def test_valid_chain_verification(self, temp_audit_file):
        """Verify an intact, un-tampered chain validates successfully."""
        logger = HashChainedAuditLogger(log_file_path=temp_audit_file)
        for i in range(1, 6):
            logger.log_event(
                actor_id=f"OFFICER-{i:02d}",
                role="SCRUTINY_OFFICER",
                action="VERIFY_DOCUMENT",
                application_id="APP-TEST-001",
                details={"doc_index": i, "status": "APPROVED"},
            )

        report = AuditChainVerifier.verify_json_file(temp_audit_file)
        assert report.is_valid is True
        assert report.total_events == 5
        assert report.tampered_event_id is None
        assert report.head_hash is not None
        assert len(report.head_hash) == 64

    @pytest.mark.unit
    def test_tamper_detection_payload_alteration(self, temp_audit_file):
        """Verify alteration of payload data within a block is detected."""
        logger = HashChainedAuditLogger(log_file_path=temp_audit_file)
        for i in range(1, 4):
            logger.log_event(
                actor_id="OFFICER-01",
                role="SCRUTINY_OFFICER",
                action="VERIFY_DOCUMENT",
                application_id="APP-TEST-001",
                details={"status": "APPROVED"},
            )

        # Maliciously tamper with event #2's details in JSON file
        with open(temp_audit_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        events[1]["details"]["status"] = "FORGED_APPROVAL"
        with open(temp_audit_file, "w", encoding="utf-8") as f:
            json.dump(events, f)

        report = AuditChainVerifier.verify_json_file(temp_audit_file)
        assert report.is_valid is False
        assert report.tampered_sequence_number == 2
        assert "Hash mismatch" in report.tamper_reason

    @pytest.mark.unit
    def test_tamper_detection_link_break(self, temp_audit_file):
        """Verify modification of previous_hash link is detected."""
        logger = HashChainedAuditLogger(log_file_path=temp_audit_file)
        for i in range(1, 4):
            logger.log_event(
                actor_id="OFFICER-01",
                role="SCRUTINY_OFFICER",
                action="VERIFY_DOCUMENT",
                application_id="APP-TEST-001",
                details={"step": i},
            )

        # Corrupt the previous_hash link of event #3
        with open(temp_audit_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        events[2]["previous_hash"] = "f" * 64
        with open(temp_audit_file, "w", encoding="utf-8") as f:
            json.dump(events, f)

        report = AuditChainVerifier.verify_json_file(temp_audit_file)
        assert report.is_valid is False
        assert report.tampered_sequence_number == 3
        assert "Broken cryptographic link" in report.tamper_reason

    @pytest.mark.unit
    def test_tamper_detection_event_omission(self, temp_audit_file):
        """Verify deletion/omission of an intermediate event is detected."""
        logger = HashChainedAuditLogger(log_file_path=temp_audit_file)
        for i in range(1, 5):
            logger.log_event(
                actor_id="OFFICER-01",
                role="SCRUTINY_OFFICER",
                action="EVALUATION_STEP",
                application_id="APP-TEST-001",
                details={"step": i},
            )

        # Delete event #2
        with open(temp_audit_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        del events[1]  # Remove sequence 2
        with open(temp_audit_file, "w", encoding="utf-8") as f:
            json.dump(events, f)

        report = AuditChainVerifier.verify_json_file(temp_audit_file)
        assert report.is_valid is False
        assert "Sequence discontinuity" in report.tamper_reason

    @pytest.mark.unit
    def test_sqlite_db_audit_verification(self, temp_sqlite_db):
        """Verify verification against SQLite table schema."""
        conn = sqlite3.connect(temp_sqlite_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                sequence_number INTEGER,
                timestamp TEXT,
                actor_id TEXT,
                role TEXT,
                action TEXT,
                target_application_id TEXT,
                details TEXT,
                previous_hash TEXT,
                event_hash TEXT
            )
        """)

        # Insert 3 chained events
        prev_h = "0" * 64
        for seq in range(1, 4):
            evt_id = f"EVT-{seq:05d}"
            ts = "2026-10-25T12:00:00"
            details = {"field": "test"}
            payload = {
                "sequence_number": seq,
                "timestamp": ts,
                "actor_id": "OFFICER-SYSTEM",
                "role": "SYSTEM",
                "action": "RECORD_EVALUATION",
                "target_application_id": "APP-SQLITE-01",
                "details": details,
            }
            evt_h = AuditChainVerifier.compute_event_hash(prev_h, payload)
            cursor.execute("""
                INSERT INTO audit_log (event_id, sequence_number, timestamp, actor_id, role, action, target_application_id, details, previous_hash, event_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (evt_id, seq, ts, "OFFICER-SYSTEM", "SYSTEM", "RECORD_EVALUATION", "APP-SQLITE-01", json.dumps(details), prev_h, evt_h))
            prev_h = evt_h

        conn.commit()
        conn.close()

        report = AuditChainVerifier.verify_sqlite_db(temp_sqlite_db)
        assert report.is_valid is True
        assert report.total_events == 3

    @pytest.mark.unit
    def test_cli_verifier_execution(self, temp_audit_file):
        """Verify the CLI verifier runs cleanly and returns proper exit codes."""
        logger = HashChainedAuditLogger(log_file_path=temp_audit_file)
        logger.log_event(
            actor_id="REGULATOR-01",
            role="CHIEF_INSPECTOR",
            action="FINAL_SIGN_OFF",
            application_id="APP-TEST-CLI",
            details={"verdict": "VERIFIED"},
        )

        python_exe = sys.executable
        # 1. Valid test
        cmd = [python_exe, "-m", "app.audit.verifier", "--file", temp_audit_file, "--json"]
        proc = subprocess.run(cmd, cwd=str(backend_dir), capture_output=True, text=True)
        assert proc.returncode == 0
        parsed = json.loads(proc.stdout)
        assert parsed["is_valid"] is True
        assert parsed["total_events"] == 1
