import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.scenarios.registry import ScenarioRegistry, CanonicalScenarioEntry, canonical_registry


SAFE_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
SAFE_FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


class PathTraversalError(HTTPException):
    def __init__(self, detail: str = "Invalid path or malicious traversal attempt detected."):
        super().__init__(status_code=400, detail=detail)


class DatasetResolver:
    """
    Centralized Dataset & Path Resolver for AICTE SAKSHAM.
    Enforces safe directory resolution, environment-driven overrides,
    and strict path traversal prevention across all routes.
    """

    def __init__(self, registry: Optional[ScenarioRegistry] = None):
        self.registry = registry or canonical_registry
        self._roots: List[Path] = []
        self._active_root: Optional[Path] = None
        self._active_version: str = "v1.0-synthetic"
        self._initialize_roots()

    def _initialize_roots(self):
        self._roots = []
        # 1. Environment variable override
        env_dir = os.getenv("AICTE_DATASET_DIR")
        if env_dir:
            p = Path(env_dir).resolve()
            if p.exists() and p.is_dir():
                self._roots.append(p)

        # 2. Workspace physical test dataset (test_data/aicte_institutions)
        workspace_test_data = Path(__file__).resolve().parent.parent.parent.parent / "test_data" / "aicte_institutions"
        if workspace_test_data.exists() and workspace_test_data.is_dir():
            self._roots.append(workspace_test_data.resolve())

        # 3. Fallback: backend synthetic scenarios directory
        backend_scenarios = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic_scenarios"
        if backend_scenarios.exists() and backend_scenarios.is_dir():
            self._roots.append(backend_scenarios.resolve())

        # Set active root and discover
        if self._roots:
            self._active_root = self._roots[0]
            self.refresh_registry()

    @property
    def active_root(self) -> Path:
        if not self._active_root:
            raise RuntimeError("No valid dataset root directory found.")
        return self._active_root

    @property
    def available_roots(self) -> List[Path]:
        return list(self._roots)

    def refresh_registry(self):
        """Scans candidate roots in precedence order, populating the canonical registry."""
        self.registry.clear()
        for root in self._roots:
            self.registry.discover_scenarios(root, dataset_version=self._active_version)

    def sanitize_identifier(self, identifier: str) -> str:
        """Validates that a scenario or institution ID does not contain path traversal characters."""
        if not identifier or not SAFE_IDENTIFIER_REGEX.match(identifier):
            raise PathTraversalError(f"Security error: Invalid scenario identifier '{identifier}'.")
        return identifier

    def sanitize_filename(self, filename: str) -> str:
        """Validates that a document filename is well-formed and prevents directory escapes."""
        if not filename or not SAFE_FILENAME_REGEX.match(filename) or ".." in filename or "/" in filename or "\\" in filename:
            raise PathTraversalError(f"Security error: Invalid filename or path traversal detected in '{filename}'.")
        return filename

    def resolve_scenario_path(self, scenario_id: str) -> Path:
        """
        Resolves the absolute path for a scenario directory across configured roots.
        Fails safely if the directory does not exist or escapes allowed roots.
        """
        clean_id = self.sanitize_identifier(scenario_id)

        # Check registry first for canonical location
        entry = self.registry.get(clean_id)
        if entry:
            resolved_path = Path(entry.source_directory).resolve()
            # Verify resolved path is strictly within one of the approved roots
            if any(self._is_subpath(resolved_path, root) for root in self._roots):
                if resolved_path.exists() and resolved_path.is_dir():
                    return resolved_path

        # Direct search across roots if not in registry
        for root in self._roots:
            candidate = (root / clean_id).resolve()
            if self._is_subpath(candidate, root) and candidate.exists() and candidate.is_dir():
                return candidate

        raise HTTPException(status_code=404, detail=f"Scenario '{clean_id}' not found in any registered dataset root.")

    def resolve_document_path(self, scenario_id: str, doc_name: str) -> Path:
        """
        Resolves the absolute path for a document within a scenario.
        Strictly prevents directory traversal.
        """
        scenario_path = self.resolve_scenario_path(scenario_id)
        clean_filename = self.sanitize_filename(doc_name)
        file_path = (scenario_path / clean_filename).resolve()

        if not self._is_subpath(file_path, scenario_path):
            raise PathTraversalError("Security error: Document path escapes scenario directory boundaries.")

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail=f"Document '{clean_filename}' not found for scenario '{scenario_id}'.")

        return file_path

    def _is_subpath(self, child: Path, parent: Path) -> bool:
        """Returns True if child is strictly inside parent directory."""
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """Returns standard metadata for all registered scenarios."""
        entries = self.registry.list_all()
        results = []
        for e in entries:
            results.append({
                "scenario_id": e.scenario_id,
                "application_id": e.application_id,
                "institution_name": e.institution_name,
                "dataset_version": e.dataset_version,
                "document_count": len(e.document_inventory),
                "source_directory": str(e.source_directory),
            })
        return results

    def get_diagnostic_info(self) -> Dict[str, Any]:
        return {
            "active_root": str(self._active_root) if self._active_root else None,
            "available_roots": [str(r) for r in self._roots],
            "total_registered_scenarios": len(self.registry.list_all()),
            "dataset_version": self._active_version,
            "conflicts_detected": len(self.registry.get_conflicts()),
        }


# Global singleton resolver
dataset_resolver = DatasetResolver()
