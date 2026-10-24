from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class VerificationType(str, Enum):
    REAL_AUTHORIZED = "REAL_AUTHORIZED"
    SIMULATED = "SIMULATED"
    LOCAL_AUTOMATED = "LOCAL_AUTOMATED"


class VerificationStatus(str, Enum):
    ISSUER_VERIFIED_SUCCESS = "Issuer Verification Successful"
    SIMULATED_SUCCESS = "Simulated Verification (Mock Adapter)"
    DISCREPANCY_DETECTED = "Discrepancy Detected with Issuer Records"
    VERIFICATION_UNAVAILABLE = "Verification Unavailable (No Authorized Gateway)"
    UNTRUSTED_DESTINATION = "Untrusted Issuer Destination"
    MANUAL_REVIEW_REQUIRED = "Requires Officer Review"


class IssuerVerificationResult(BaseModel):
    adapter_name: str
    verification_type: VerificationType
    status: VerificationStatus
    is_simulated: bool
    source_authority: str
    reference_id: Optional[str] = None
    timestamp: datetime
    details: Dict[str, Any]
    certificate_chain_valid: Optional[bool] = None
    destination_trusted: Optional[bool] = None
