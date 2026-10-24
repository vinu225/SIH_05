from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.issuer import IssuerVerificationResult


class IIssuerAdapter(ABC):
    """
    Common Issuer Verification Interface decoupling external / mock verification
    mechanisms from application core logic.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_simulated(self) -> bool:
        pass

    @abstractmethod
    async def verify_document(
        self,
        document_type: str,
        reference_id: str,
        payload_data: Dict[str, Any],
    ) -> IssuerVerificationResult:
        pass
