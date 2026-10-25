import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class AuditVerificationReport(BaseModel):
    is_valid: bool
    total_events: int
    genesis_hash: str
    head_hash: Optional[str] = None
    tampered_event_id: Optional[str] = None
    tampered_sequence_number: Optional[int] = None
    tamper_reason: Optional[str] = None
    verification_details: List[str] = Field(default_factory=list)


class AuditChainVerifier:
    """
    Independent regulatory verification tool for AICTE audit trails.
    Traverses SHA-256 event chains, verifies block continuity, and detects
    tampering, omissions, or unauthorized modifications.
    """

    GENESIS_HASH = "0" * 64

    @staticmethod
    def compute_event_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True)
        combined = f"{prev_hash}:{serialized}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    @classmethod
    def verify_event_stream(cls, events: List[Dict[str, Any]]) -> AuditVerificationReport:
        """
        Verifies a list of serialized audit event dictionaries.
        """
        if not events:
            return AuditVerificationReport(
                is_valid=True,
                total_events=0,
                genesis_hash=cls.GENESIS_HASH,
                head_hash=None,
                verification_details=["Empty audit chain verified (zero events)."],
            )

        details: List[str] = []
        prev_hash = cls.GENESIS_HASH

        for idx, event in enumerate(events):
            seq = event.get("sequence_number")
            evt_id = event.get("event_id", f"EVT-{idx+1:05d}")
            expected_seq = idx + 1

            # 1. Sequence number continuity check
            if seq != expected_seq:
                return AuditVerificationReport(
                    is_valid=False,
                    total_events=len(events),
                    genesis_hash=cls.GENESIS_HASH,
                    head_hash=None,
                    tampered_event_id=evt_id,
                    tampered_sequence_number=seq,
                    tamper_reason=f"Sequence discontinuity: expected sequence {expected_seq}, but found {seq}.",
                    verification_details=details,
                )

            # 2. Previous hash linkage check
            event_prev_hash = event.get("previous_hash")
            if event_prev_hash != prev_hash:
                return AuditVerificationReport(
                    is_valid=False,
                    total_events=len(events),
                    genesis_hash=cls.GENESIS_HASH,
                    head_hash=None,
                    tampered_event_id=evt_id,
                    tampered_sequence_number=seq,
                    tamper_reason=f"Broken cryptographic link at event {evt_id}: expected previous hash '{prev_hash}', got '{event_prev_hash}'.",
                    verification_details=details,
                )

            # 3. Payload cryptographic hash recalculation
            payload = {
                "sequence_number": event.get("sequence_number"),
                "timestamp": event.get("timestamp"),
                "actor_id": event.get("actor_id"),
                "role": event.get("role"),
                "action": event.get("action"),
                "target_application_id": event.get("target_application_id"),
                "details": event.get("details", {}),
            }
            computed_hash = cls.compute_event_hash(prev_hash, payload)
            actual_hash = event.get("event_hash")

            if computed_hash != actual_hash:
                return AuditVerificationReport(
                    is_valid=False,
                    total_events=len(events),
                    genesis_hash=cls.GENESIS_HASH,
                    head_hash=None,
                    tampered_event_id=evt_id,
                    tampered_sequence_number=seq,
                    tamper_reason=f"Hash mismatch at event {evt_id}: computed SHA-256 '{computed_hash}' does not match stored hash '{actual_hash}'. Payload has been altered.",
                    verification_details=details,
                )

            details.append(f"Event #{seq} [{evt_id}] verified: hash={actual_hash[:16]}...")
            prev_hash = actual_hash

        return AuditVerificationReport(
            is_valid=True,
            total_events=len(events),
            genesis_hash=cls.GENESIS_HASH,
            head_hash=prev_hash,
            verification_details=details,
        )

    @classmethod
    def verify_json_file(cls, file_path: str) -> AuditVerificationReport:
        """Verifies audit events from a JSON file."""
        p = Path(file_path)
        if not p.exists():
            return AuditVerificationReport(
                is_valid=False,
                total_events=0,
                genesis_hash=cls.GENESIS_HASH,
                tamper_reason=f"Audit file not found: {file_path}",
            )
        try:
            with open(p, "r", encoding="utf-8") as f:
                events = json.load(f)
            if not isinstance(events, list):
                return AuditVerificationReport(
                    is_valid=False,
                    total_events=0,
                    genesis_hash=cls.GENESIS_HASH,
                    tamper_reason="Audit file does not contain a JSON list of events.",
                )
            return cls.verify_event_stream(events)
        except Exception as e:
            return AuditVerificationReport(
                is_valid=False,
                total_events=0,
                genesis_hash=cls.GENESIS_HASH,
                tamper_reason=f"Failed to read audit file: {str(e)}",
            )

    @classmethod
    def verify_sqlite_db(cls, db_path: str, table_name: str = "audit_log") -> AuditVerificationReport:
        """Verifies audit events from an SQLite database table."""
        p = Path(db_path)
        if not p.exists():
            return AuditVerificationReport(
                is_valid=False,
                total_events=0,
                genesis_hash=cls.GENESIS_HASH,
                tamper_reason=f"SQLite database file not found: {db_path}",
            )
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY sequence_number ASC")
            rows = cursor.fetchall()
            events = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("details"), str):
                    try:
                        item["details"] = json.loads(item["details"])
                    except Exception:
                        pass
                events.append(item)
            conn.close()
            return cls.verify_event_stream(events)
        except Exception as e:
            return AuditVerificationReport(
                is_valid=False,
                total_events=0,
                genesis_hash=cls.GENESIS_HASH,
                tamper_reason=f"Database query error: {str(e)}",
            )


def main():
    parser = argparse.ArgumentParser(
        description="AICTE SAKSHAM - Independent Audit Chain Verifier CLI"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to audit JSON file (e.g. data/audit_chain.json)")
    group.add_argument("--db", help="Path to SQLite database (e.g. data/aicte_scrutiny.db)")
    parser.add_argument("--table", default="audit_log", help="Table name for SQLite audit logs")
    parser.add_argument("--json", action="store_true", help="Output report as formatted JSON")

    args = parser.parse_args()

    if args.file:
        report = AuditChainVerifier.verify_json_file(args.file)
    else:
        report = AuditChainVerifier.verify_sqlite_db(args.db, table_name=args.table)

    if args.json:
        print(json.dumps(report.model_dump(), indent=2))
    else:
        print("=" * 60)
        print(" AICTE SAKSHAM INDEPENDENT AUDIT VERIFICATION REPORT")
        print("=" * 60)
        print(f"Status:        {'VERIFIED / VALID' if report.is_valid else 'TAMPERED / INVALID'}")
        print(f"Total Events:  {report.total_events}")
        print(f"Genesis Hash:  {report.genesis_hash}")
        print(f"Head Hash:     {report.head_hash or 'None'}")
        if not report.is_valid:
            print(f"Tampered Event: #{report.tampered_sequence_number} ({report.tampered_event_id})")
            print(f"Failure Reason: {report.tamper_reason}")
        print("=" * 60)

    sys.exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
