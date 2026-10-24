import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


DB_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "aicte_scrutiny.db"


class LocalDatabaseManager:
    """
    Manages local relational SQLite database for the AICTE Scrutiny Platform.
    Stores institutions, documents, APH rules, 3-pillar findings, and SHA-256 chained audit logs.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_FILE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Institutions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS institutions (
                institution_id TEXT PRIMARY KEY,
                application_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                program_category TEXT NOT NULL,
                declared_land_acres REAL NOT NULL,
                total_approved_students INTEGER NOT NULL,
                expected_status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Documents Table (Hash-Verified Vault Metadata)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                institution_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                dhash TEXT,
                upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (institution_id) REFERENCES institutions (institution_id)
            );
            """)

            # 3. APH Rules Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS aph_rules (
                rule_id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                aph_edition TEXT NOT NULL,
                clause_reference TEXT NOT NULL,
                handbook_page_no INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                parameters_json TEXT NOT NULL
            );
            """)

            # 4. Findings Table (3-Pillar Explainable Findings)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                finding_id TEXT PRIMARY KEY,
                institution_id TEXT NOT NULL,
                assessment_pillar TEXT NOT NULL,
                outcome TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                rule_id TEXT,
                clause_reference TEXT,
                source_document_name TEXT,
                extracted_value TEXT,
                discrepancy_magnitude TEXT,
                confidence_score REAL,
                officer_decision TEXT DEFAULT 'PENDING_REVIEW',
                officer_id TEXT,
                officer_reason TEXT,
                officer_timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (institution_id) REFERENCES institutions (institution_id)
            );
            """)

            # 5. Audit Events Table (Cryptographically Chained)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                sequence_number INTEGER UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                role TEXT NOT NULL,
                action TEXT NOT NULL,
                target_application_id TEXT NOT NULL,
                details_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL
            );
            """)

            conn.commit()

    def seed_initial_data(self, scenarios_dir: Path, rules_file: Path):
        """Pre-seeds the SQLite database from synthetic scenarios and APH rules."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Seed Rules
            if rules_file.exists():
                with open(rules_file, "r", encoding="utf-8") as f:
                    rules_data = json.load(f).get("rules", [])
                for r in rules_data:
                    cursor.execute("""
                    INSERT OR REPLACE INTO aph_rules (
                        rule_id, version, status, aph_edition, clause_reference,
                        handbook_page_no, title, description, parameters_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r["rule_id"], r["version"], r["status"], r["aph_edition"],
                        r["clause_reference"], r.get("handbook_page_no"), r["title"],
                        r["description"], json.dumps(r.get("parameters", {}))
                    ))

            # Seed Institutions & Documents
            if scenarios_dir.exists():
                gt_path = scenarios_dir / "ground_truth.json"
                if gt_path.exists():
                    with open(gt_path, "r", encoding="utf-8") as f:
                        benchmarks = json.load(f).get("benchmarks", [])
                    for b in benchmarks:
                        inst_id = b["application_id"].replace("APP-2024-", "")
                        cursor.execute("""
                        INSERT OR REPLACE INTO institutions (
                            institution_id, application_id, name, program_category,
                            declared_land_acres, total_approved_students, expected_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            inst_id, b["application_id"], b["institution_name"],
                            "ENGINEERING_AND_TECHNOLOGY", b.get("declared_land_acres", 4.0),
                            b.get("total_approved_students", 240), b.get("expected_status")
                        ))

                        # Seed Documents for this institution
                        inst_folder = scenarios_dir / inst_id
                        if inst_folder.exists():
                            for doc_file in inst_folder.glob("*.pdf"):
                                with open(doc_file, "rb") as df:
                                    content = df.read()
                                sha256 = hashlib.sha256(content).hexdigest()
                                doc_id = f"DOC-{inst_id}-{doc_file.stem}"
                                cursor.execute("""
                                INSERT OR REPLACE INTO documents (
                                    document_id, institution_id, document_type,
                                    filename, file_path, sha256_hash
                                ) VALUES (?, ?, ?, ?, ?, ?)
                                """, (
                                    doc_id, inst_id, doc_file.stem,
                                    doc_file.name, str(doc_file), sha256
                                ))

            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM institutions")
            institutions_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM documents")
            documents_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM aph_rules")
            rules_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM findings")
            findings_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM audit_events")
            audit_count = c.fetchone()[0]

        return {
            "institutions": institutions_count,
            "documents": documents_count,
            "aph_rules": rules_count,
            "findings": findings_count,
            "audit_events": audit_count,
        }

    def record_finding(self, institution_id: str, finding_dict: Dict[str, Any]):
        with self.get_connection() as conn:
            c = conn.cursor()
            evidence = finding_dict.get("evidence", {})
            rule = finding_dict.get("applicable_rule", {})

            c.execute("""
            INSERT OR REPLACE INTO findings (
                finding_id, institution_id, assessment_pillar, outcome,
                title, description, rule_id, clause_reference,
                source_document_name, extracted_value, discrepancy_magnitude,
                confidence_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                finding_dict["finding_id"],
                institution_id,
                finding_dict["assessment_pillar"],
                finding_dict["outcome"],
                finding_dict["title"],
                finding_dict["description"],
                rule.get("rule_id"),
                rule.get("clause_reference"),
                evidence.get("source_document_name"),
                str(evidence.get("extracted_value")),
                evidence.get("discrepancy_magnitude"),
                finding_dict.get("confidence_or_uncertainty", {}).get("confidence_score", 1.0),
            ))
            conn.commit()

    def update_officer_decision(self, finding_id: str, decision: str, officer_id: str, reason: Optional[str] = None):
        with self.get_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute("""
            UPDATE findings
            SET officer_decision = ?, officer_id = ?, officer_reason = ?, officer_timestamp = ?
            WHERE finding_id = ?
            """, (decision, officer_id, reason, now, finding_id))
            conn.commit()

    def get_findings_for_institution(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM findings WHERE institution_id = ?", (institution_id,))
            rows = c.fetchall()
            return [dict(row) for row in rows]

    def insert_document(self, document_id: str, institution_id: str, document_type: str, filename: str, file_path: str, sha256_hash: str, dhash: Optional[str] = None):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            INSERT OR REPLACE INTO documents (
                document_id, institution_id, document_type, filename, file_path, sha256_hash, dhash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (document_id, institution_id, document_type, filename, file_path, sha256_hash, dhash))
            conn.commit()
