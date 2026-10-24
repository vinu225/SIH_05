import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    event_id: str
    sequence_number: int
    timestamp: str
    actor_id: str
    role: str  # "SCRUTINY_OFFICER", "SYSTEM_AUTOMATION", "ADMIN"
    action: str  # "EVALUATE_APH_RULE", "OFFICER_OVERRIDE", "VERIFY_ISSUER", "STORE_DOCUMENT"
    target_application_id: str
    details: Dict[str, Any]
    previous_hash: str
    event_hash: str


class HashChainedAuditLogger:
    """
    Append-only audit trail with SHA-256 event chaining for tamper detection.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, log_file_path: Optional[str] = None):
        if log_file_path is None:
            log_file_path = str(Path(__file__).parent.parent.parent / "data" / "audit_chain.json")
        self.log_path = Path(log_file_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.events: List[AuditEvent] = []
        self._load_chain()

    def _load_chain(self):
        if self.log_path.exists():
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.events = [AuditEvent(**item) for item in data]
            except Exception:
                self.events = []
        else:
            self.events = []

    def _save_chain(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump([e.model_dump() for e in self.events], f, indent=2)

    @staticmethod
    def _compute_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True)
        combined = f"{prev_hash}:{serialized}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    def log_event(
        self,
        actor_id: str,
        role: str,
        action: str,
        application_id: str,
        details: Dict[str, Any],
    ) -> AuditEvent:
        seq = len(self.events) + 1
        prev_hash = self.events[-1].event_hash if self.events else self.GENESIS_HASH
        timestamp = datetime.now().isoformat()

        payload = {
            "sequence_number": seq,
            "timestamp": timestamp,
            "actor_id": actor_id,
            "role": role,
            "action": action,
            "target_application_id": application_id,
            "details": details,
        }
        event_hash = self._compute_hash(prev_hash, payload)

        event = AuditEvent(
            event_id=f"EVT-{seq:05d}",
            sequence_number=seq,
            timestamp=timestamp,
            actor_id=actor_id,
            role=role,
            action=action,
            target_application_id=application_id,
            details=details,
            previous_hash=prev_hash,
            event_hash=event_hash,
        )
        self.events.append(event)
        self._save_chain()
        return event

    def verify_chain_integrity(self) -> Tuple[bool, Optional[str]]:
        """
        Recalculates the entire hash chain from genesis to the current event.
        Returns (is_valid, error_description).
        """
        if not self.events:
            return True, None

        prev_hash = self.GENESIS_HASH
        for idx, event in enumerate(self.events):
            if event.previous_hash != prev_hash:
                return False, f"Broken link at event #{event.sequence_number}: expected prev_hash {prev_hash}, got {event.previous_hash}"

            payload = {
                "sequence_number": event.sequence_number,
                "timestamp": event.timestamp,
                "actor_id": event.actor_id,
                "role": event.role,
                "action": event.action,
                "target_application_id": event.target_application_id,
                "details": event.details,
            }
            computed_hash = self._compute_hash(prev_hash, payload)
            if computed_hash != event.event_hash:
                return False, f"Tampered event #{event.sequence_number}: expected hash {computed_hash}, got {event.event_hash}"

            prev_hash = event.event_hash

        return True, None
