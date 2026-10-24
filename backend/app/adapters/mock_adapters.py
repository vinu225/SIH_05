from datetime import datetime
from typing import Dict, Any
from app.adapters.base import IIssuerAdapter
from app.schemas.issuer import (
    IssuerVerificationResult,
    VerificationType,
    VerificationStatus,
)


class DigiLockerMockAdapter(IIssuerAdapter):
    """
    Simulated Mock Adapter for DigiLocker National Academic Depository (NAD).
    Explicitly labeled as Simulated Verification.
    """

    @property
    def adapter_name(self) -> str:
        return "DIGILOCKER_NAD_MOCK"

    @property
    def is_simulated(self) -> bool:
        return True

    async def verify_document(
        self,
        document_type: str,
        reference_id: str,
        payload_data: Dict[str, Any],
    ) -> IssuerVerificationResult:
        # Simulated verification response
        return IssuerVerificationResult(
            adapter_name=self.adapter_name,
            verification_type=VerificationType.SIMULATED,
            status=VerificationStatus.SIMULATED_SUCCESS,
            is_simulated=True,
            source_authority="DigiLocker NAD (Simulated Gateway)",
            reference_id=reference_id,
            timestamp=datetime.now(),
            details={
                "mock_response": "MATCH_CONFIRMED",
                "issuer": "DigiLocker Ministry of Electronics & IT",
                "verification_notice": "THIS IS A SIMULATED VERIFICATION FOR PROTOTYPE TESTING ONLY.",
                "verified_fields": payload_data,
            },
            certificate_chain_valid=True,
            destination_trusted=True,
        )


class StateFireMockAdapter(IIssuerAdapter):
    """
    Simulated Mock Adapter for State Directorate of Fire & Emergency Services.
    Explicitly labeled as Simulated Verification.
    """

    @property
    def adapter_name(self) -> str:
        return "STATE_FIRE_NOC_MOCK"

    @property
    def is_simulated(self) -> bool:
        return True

    async def verify_document(
        self,
        document_type: str,
        reference_id: str,
        payload_data: Dict[str, Any],
    ) -> IssuerVerificationResult:
        return IssuerVerificationResult(
            adapter_name=self.adapter_name,
            verification_type=VerificationType.SIMULATED,
            status=VerificationStatus.SIMULATED_SUCCESS,
            is_simulated=True,
            source_authority="Directorate of Fire Services (Simulated Gateway)",
            reference_id=reference_id,
            timestamp=datetime.now(),
            details={
                "mock_response": "NOC_RECORD_FOUND",
                "clearance_number": reference_id,
                "verification_notice": "THIS IS A SIMULATED VERIFICATION FOR PROTOTYPE TESTING ONLY.",
            },
            certificate_chain_valid=True,
            destination_trusted=True,
        )
