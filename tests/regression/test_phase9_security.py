import json
import pytest
import urllib.request
import urllib.error
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.auth.security import UserRole, Permission, ROLE_PERMISSIONS

BASE_URL = "http://localhost:8000"


class TestPhase9Security:
    """Regression test suite for Phase 9 Role-Based Authorization & Data Protection."""

    @pytest.mark.unit
    def test_role_permissions_matrix(self):
        """Verify role permissions hierarchy conforms to AICTE scrutiny governance."""
        assert Permission.VIEW_FINDINGS in ROLE_PERMISSIONS[UserRole.PUBLIC_VIEWER]
        assert Permission.OFFICER_OVERRIDE not in ROLE_PERMISSIONS[UserRole.PUBLIC_VIEWER]
        assert Permission.UPLOAD_DOCUMENT not in ROLE_PERMISSIONS[UserRole.PUBLIC_VIEWER]

        assert Permission.OFFICER_OVERRIDE in ROLE_PERMISSIONS[UserRole.SCRUTINY_OFFICER]
        assert Permission.UPLOAD_DOCUMENT in ROLE_PERMISSIONS[UserRole.SCRUTINY_OFFICER]
        assert Permission.CHIEF_SIGN_OFF not in ROLE_PERMISSIONS[UserRole.SCRUTINY_OFFICER]

        assert Permission.CHIEF_SIGN_OFF in ROLE_PERMISSIONS[UserRole.CHIEF_INSPECTOR]
        assert Permission.VERIFY_AUDIT_CHAIN in ROLE_PERMISSIONS[UserRole.CHIEF_INSPECTOR]

    @pytest.mark.integration
    def test_auth_me_default_role(self):
        """Verify default development session resolves to SCRUTINY_OFFICER."""
        req = urllib.request.Request(f"{BASE_URL}/api/v1/auth/me")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["role"] == "SCRUTINY_OFFICER"
            assert "OFFICER_OVERRIDE" in data["permissions"]

    @pytest.mark.integration
    def test_auth_me_public_viewer(self):
        """Verify explicit header switches session to PUBLIC_VIEWER."""
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"X-API-Role": "PUBLIC_VIEWER", "X-User-ID": "GUEST-001"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["role"] == "PUBLIC_VIEWER"
            assert data["user_id"] == "GUEST-001"
            assert data["permissions"] == ["VIEW_FINDINGS"]

    @pytest.mark.integration
    def test_officer_override_denied_for_public_viewer(self):
        """Verify PUBLIC_VIEWER cannot record officer decisions / overrides (403 Forbidden)."""
        payload = json.dumps({
            "finding_id": "FIND-LAND-DEFICIT-01",
            "decision": "OVERRIDDEN",
            "officer_id": "PUBLIC_ATTEMPT",
            "reason": "Attempting unauthorized override",
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/officer/decision",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Role": "PUBLIC_VIEWER",
            },
            method="POST",
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)

        assert exc_info.value.code == 403
        err_body = json.loads(exc_info.value.read().decode())
        assert "lacks required permission 'OFFICER_OVERRIDE'" in err_body["detail"]

    @pytest.mark.integration
    def test_officer_override_allowed_for_scrutiny_officer(self):
        """Verify authorized SCRUTINY_OFFICER can record decisions and get audit receipt."""
        payload = json.dumps({
            "finding_id": "FIND-TEST-009",
            "decision": "ACCEPTED",
            "officer_id": "OFFICER-REG-409",
            "reason": "Verified municipal title clearance documents on record.",
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/officer/decision",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Role": "SCRUTINY_OFFICER",
                "X-Badge-ID": "AICTE-OFFICER-409",
            },
            method="POST",
        )

        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "recorded"
            assert data["role"] == "SCRUTINY_OFFICER"
            assert data["officer_id"] == "OFFICER-REG-409"
            assert "event_id" in data

    @pytest.mark.integration
    def test_invalid_role_rejected(self):
        """Verify unknown/malicious role header returns 401 Unauthorized."""
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"X-API-Role": "SUPER_ADMIN_HACK"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)

        assert exc_info.value.code == 401
        err_body = json.loads(exc_info.value.read().decode())
        assert "Invalid user role" in err_body["detail"]
