import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class DocumentInventoryItem(BaseModel):
    filename: str
    file_path: str
    sha256_hash: str
    file_size_bytes: int


class CanonicalScenarioEntry(BaseModel):
    scenario_id: str
    institution_id: str
    application_id: str
    institution_name: str
    dataset_version: str = "v1.0-synthetic"
    source_directory: str
    application_metadata_path: str
    document_inventory: Dict[str, DocumentInventoryItem] = Field(default_factory=dict)
    ground_truth_path: Optional[str] = None
    expected_findings_path: Optional[str] = None
    applicable_rules: List[str] = Field(default_factory=list)
    expected_verification_methods: List[str] = Field(default_factory=list)


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class ScenarioRegistry:
    """
    Canonical Scenario Registry for AICTE SAKSHAM.
    Enforces unambiguous scenario resolution, input file hash verification,
    and conflict detection across dataset roots.
    """

    def __init__(self):
        self._registry: Dict[str, CanonicalScenarioEntry] = {}
        self._conflicts: List[Dict[str, Any]] = []

    def clear(self):
        self._registry.clear()
        self._conflicts.clear()

    def register(self, entry: CanonicalScenarioEntry, allow_override: bool = False):
        if entry.scenario_id in self._registry and not allow_override:
            existing = self._registry[entry.scenario_id]
            if existing.source_directory != entry.source_directory:
                conflict = {
                    "scenario_id": entry.scenario_id,
                    "existing_dir": existing.source_directory,
                    "conflicting_dir": entry.source_directory,
                    "reason": "Duplicate scenario ID in different dataset roots with divergent paths",
                }
                self._conflicts.append(conflict)
                raise ValueError(
                    f"Scenario conflict detected for '{entry.scenario_id}': "
                    f"Already registered at '{existing.source_directory}', "
                    f"conflicting at '{entry.source_directory}'."
                )
        self._registry[entry.scenario_id] = entry

    def get(self, scenario_id: str) -> Optional[CanonicalScenarioEntry]:
        return self._registry.get(scenario_id)

    def list_all(self) -> List[CanonicalScenarioEntry]:
        return list(self._registry.values())

    def get_conflicts(self) -> List[Dict[str, Any]]:
        return list(self._conflicts)

    def verify_scenario_inputs(self, scenario_id: str) -> Dict[str, Any]:
        """
        Verifies that actual files on disk match the registered document inventory hashes.
        Fails safely if any document is missing or corrupted.
        """
        entry = self.get(scenario_id)
        if not entry:
            return {
                "valid": False,
                "error": f"Scenario '{scenario_id}' is not registered in the canonical registry.",
            }

        src_dir = Path(entry.source_directory)
        if not src_dir.exists():
            return {
                "valid": False,
                "error": f"Source directory '{src_dir}' does not exist on disk.",
            }

        verified_docs = {}
        discrepancies = []

        for fname, inv_item in entry.document_inventory.items():
            fpath = src_dir / fname
            if not fpath.exists():
                discrepancies.append(f"Missing mandatory document: '{fname}'")
                continue

            actual_sha = compute_file_sha256(fpath)
            actual_size = fpath.stat().st_size
            match = (actual_sha == inv_item.sha256_hash)
            if not match:
                discrepancies.append(
                    f"Hash mismatch for '{fname}': expected {inv_item.sha256_hash[:12]}..., got {actual_sha[:12]}..."
                )

            verified_docs[fname] = {
                "filename": fname,
                "expected_sha256": inv_item.sha256_hash,
                "actual_sha256": actual_sha,
                "expected_size_bytes": inv_item.file_size_bytes,
                "actual_size_bytes": actual_size,
                "integrity_valid": match,
            }

        return {
            "valid": len(discrepancies) == 0,
            "scenario_id": scenario_id,
            "institution_id": entry.institution_id,
            "application_id": entry.application_id,
            "verified_documents": verified_docs,
            "discrepancies": discrepancies,
        }

    def discover_scenarios(self, directory: Path, dataset_version: str = "v1.0-synthetic") -> int:
        """
        Discovers and registers scenarios from a given dataset root.
        """
        if not directory.exists() or not directory.is_dir():
            return 0

        count = 0
        gt_file = directory / "ground_truth.json"
        expected_csv = directory / "expected_findings.csv"

        gt_data = {}
        if gt_file.exists():
            try:
                with open(gt_file, "r", encoding="utf-8") as f:
                    benchmarks = json.load(f).get("benchmarks", [])
                    gt_data = {b["application_id"]: b for b in benchmarks}
            except Exception:
                pass

        for sub in sorted(directory.iterdir()):
            if not sub.is_dir():
                continue

            meta_file = sub / "application_metadata.json"
            if not meta_file.exists():
                continue

            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                continue

            scenario_id = sub.name
            app_id = meta.get("application_id", f"APP-2024-{scenario_id}")
            inst_name = meta.get("institution_name", scenario_id)

            # Build document inventory with actual hashes
            inventory = {}
            for item in sub.iterdir():
                if item.is_file() and item.suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg"]:
                    inventory[item.name] = DocumentInventoryItem(
                        filename=item.name,
                        file_path=str(item.resolve()),
                        sha256_hash=compute_file_sha256(item),
                        file_size_bytes=item.stat().st_size,
                    )

            entry = CanonicalScenarioEntry(
                scenario_id=scenario_id,
                institution_id=scenario_id,
                application_id=app_id,
                institution_name=inst_name,
                dataset_version=dataset_version,
                source_directory=str(sub.resolve()),
                application_metadata_path=str(meta_file.resolve()),
                document_inventory=inventory,
                ground_truth_path=str(gt_file.resolve()) if gt_file.exists() else None,
                expected_findings_path=str(expected_csv.resolve()) if expected_csv.exists() else None,
            )

            try:
                self.register(entry)
                count += 1
            except ValueError as e:
                # Log conflict
                pass

        return count


# Singleton instance
canonical_registry = ScenarioRegistry()
