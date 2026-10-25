import pytest
import json
import urllib.request
import urllib.error
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.scenarios.resolver import dataset_resolver

BASE_URL = "http://localhost:8000"


class TestPhase4UploadAndHardening:
    """
    Phase 4 Regression Test Suite:
    Verifies secure document upload handler, file extension whitelisting,
    path-traversal protection on uploads, and 404 error responses.
    """

    def test_upload_rejects_unsupported_extension(self):
        """Verify upload endpoint rejects unauthorized file types (e.g., .exe)."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="scenario_id"\r\n\r\n'
            f"INST-01-COMPLIANT\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="malicious.exe"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
            f"MZ_FAKE_BINARY\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/documents/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(req, timeout=5)
        assert excinfo.value.code == 400
        assert "unsupported format" in excinfo.value.read().decode("utf-8").lower()

    def test_upload_rejects_path_traversal(self):
        """Verify upload endpoint rejects path-traversal in scenario_id."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="scenario_id"\r\n\r\n'
            f"../../etc/passwd\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="sample.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
            f"%PDF-1.4 test bytes\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/documents/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(req, timeout=5)
        assert excinfo.value.code == 400

    def test_upload_valid_supplemental_document(self):
        """Verify upload endpoint safely accepts valid PDF and computes SHA-256."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        sample_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="scenario_id"\r\n\r\n'
            f"INST-01-COMPLIANT\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document_type"\r\n\r\n'
            f"RECTIFIED_CLEARANCE_PROOF\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="Supplemental_Evidence.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + sample_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/documents/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data["status"] == "success"
            assert data["filename"] == "Supplemental_Evidence.pdf"
            assert "sha256" in data
            assert len(data["sha256"]) == 64

    def test_evaluate_nonexistent_scenario_404(self):
        """Verify evaluating a non-existent scenario returns HTTP 404."""
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/evaluate/INST-NON-EXISTENT-9999",
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(req, timeout=5)
        assert excinfo.value.code == 404
