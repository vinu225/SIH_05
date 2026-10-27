import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.copilot.config import copilot_config
from app.copilot.prompt_builder import prompt_builder
from app.copilot.client import ollama_client
from app.copilot.service import copilot_service, CopilotChatRequest
from app.db.database import LocalDatabaseManager
from app.audit.chained_logger import HashChainedAuditLogger


class TestPhase11OllamaCopilot:
    """
    Phase 11 Regression Test Suite:
    Validates the local Ollama Qwen Copilot read-only sidecar architecture.
    Ensures zero mutation to core database, zero modification to audit chain,
    and graceful offline degradation.
    """

    def test_copilot_config_defaults(self):
        """Verify Copilot configuration defaults and statutory disclaimer."""
        assert "http" in copilot_config.OLLAMA_BASE_URL
        assert copilot_config.STATUTORY_DISCLAIMER.startswith("[AICTE Decision-Support Advisory")
        assert "qwen3:8b" in copilot_config.PREFERRED_MODELS
        assert "qwen2.5:7b" in copilot_config.PREFERRED_MODELS
        assert copilot_config.TEMPERATURE <= 0.3

    def test_copilot_system_prompt_guardrails(self):
        """Verify prompt builder embeds mandatory statutory boundaries."""
        system_prompt = prompt_builder.get_system_prompt()
        assert "AICTE SAKSHAM Regulatory Copilot" in system_prompt
        assert "DO NOT have the statutory authority" in system_prompt
        assert copilot_config.STATUTORY_DISCLAIMER in system_prompt

    def test_copilot_user_prompt_context_packaging(self):
        """Verify prompt builder correctly packages APH rules, metadata, and findings."""
        scenario_data = {
            "application_id": "APP-TEST-INST-03",
            "institution_name": "Test Engineering Institute",
            "declared_intake": 360,
            "declared_land_area_acres": 5.0,
            "location_category": "RURAL",
        }
        findings_data = {
            "overall_status": "Discrepancy Found",
            "findings": [
                {
                    "assessment_pillar": "REGULATORY_COMPLIANCE",
                    "title": "Land Area Shortfall",
                    "outcome": "DISCREPANCY_FOUND",
                    "description": "Deed specifies 2.1 Acres vs 5.0 Acres declared.",
                    "evidence": {"extracted_value": "2.10 Acres"},
                }
            ],
        }

        user_prompt = prompt_builder.build_user_prompt(
            query="Why is 2.1 acres deficient?",
            scenario_data=scenario_data,
            findings_data=findings_data,
        )

        assert "STATUTORY APH 2024-2027 REGULATORY NORMS" in user_prompt
        assert "APP-TEST-INST-03" in user_prompt
        assert "Land Area Shortfall" in user_prompt
        assert "Why is 2.1 acres deficient?" in user_prompt

    def test_copilot_status_reporting(self):
        """Verify health check logic returns valid structure."""
        status = asyncio.run(copilot_service.get_status())
        assert "status" in status
        assert status["status"] in ["online", "offline", "degraded"]
        assert "ollama_url" in status

    def test_copilot_offline_graceful_handling(self):
        """Verify that when Ollama is unreachable, copilot returns a friendly advisory message without crashing."""
        with patch.object(ollama_client, "resolve_active_model", AsyncMock(return_value=None)):
            req = CopilotChatRequest(query="Explain land deficit norms", scenario_id="INST-01-COMPLIANT")
            response = asyncio.run(copilot_service.answer_query(req))
            assert response.success is False
            assert "Ollama Offline" in response.response
            assert copilot_config.STATUTORY_DISCLAIMER in response.response

    def test_copilot_zero_pipeline_mutation(self):
        """
        CRITICAL ARCHITECTURAL TEST:
        Verify copilot calls produce zero mutations on SQLite records and zero events in audit_chain.json.
        """
        db_mgr = LocalDatabaseManager()
        audit_log = HashChainedAuditLogger()
        events_before = len(audit_log.events)
        stats_before = db_mgr.get_stats()

        mock_answer = {
            "success": True,
            "response": (
                f"{copilot_config.STATUTORY_DISCLAIMER}\n\n"
                "Under APH 2024-2027 Chapter 1, Clause 1.3, the required land is 1.50 Acres for Urban engineering."
            ),
            "model": "qwen3:8b",
            "generation_time_seconds": 0.42,
        }

        with patch.object(ollama_client, "generate_response", AsyncMock(return_value=mock_answer)):
            req = CopilotChatRequest(
                query="What is the minimum land requirement?",
                scenario_id="INST-01-COMPLIANT",
            )
            resp = asyncio.run(copilot_service.answer_query(req))

            assert resp.success is True
            assert "Clause 1.3" in resp.response
            assert len(resp.citations) > 0

        # Verify zero audit side-effects
        events_after = len(audit_log.events)
        stats_after = db_mgr.get_stats()

        assert events_after == events_before, "Copilot must NEVER append events to the audit chain!"
        assert stats_after == stats_before, "Copilot must NEVER insert/modify relational SQLite tables!"
