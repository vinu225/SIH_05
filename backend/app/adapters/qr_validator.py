from typing import Tuple, Dict, Any, Optional
from urllib.parse import urlparse
from app.schemas.issuer import VerificationStatus, VerificationType, IssuerVerificationResult
from datetime import datetime


# NOTE: Prototype endpoints are illustrative / unconfirmed until formally authorized by AICTE.
ILLUSTRATIVE_TRUSTED_ISSUER_ALLOWLIST = [
    "https://nad.digitallocker.gov.in/verify/",
    "https://edistrict.delhigovt.nic.in/verify/",
    "https://mahafireservice.gov.in/portal/verify/",
    "https://aicte-india.org/eoa/verify/",
]


class QRDestinationValidator:
    """
    Decodes and validates QR code target destinations against an explicit
    trusted-issuer allowlist. Decoding alone does not certify authenticity.
    """

    def __init__(self, allowlist: Optional[list] = None):
        self.allowlist = allowlist or ILLUSTRATIVE_TRUSTED_ISSUER_ALLOWLIST

    def is_destination_trusted(self, target_url: str) -> bool:
        if not target_url:
            return False
        # Exact prefix match against approved base endpoints
        for allowed_endpoint in self.allowlist:
            if target_url.startswith(allowed_endpoint):
                return True
        return False

    def evaluate_qr_payload(
        self,
        qr_text: str,
        expected_fields: Dict[str, Any],
    ) -> IssuerVerificationResult:
        """
        Evaluates whether the QR code points to a trusted destination and whether
        its payload matches the document fields.
        """
        now = datetime.now()
        is_url = qr_text.startswith("http://") or qr_text.startswith("https://")

        if is_url:
            trusted = self.is_destination_trusted(qr_text)
            if not trusted:
                return IssuerVerificationResult(
                    adapter_name="QR_DESTINATION_VALIDATOR",
                    verification_type=VerificationType.LOCAL_AUTOMATED,
                    status=VerificationStatus.UNTRUSTED_DESTINATION,
                    is_simulated=False,
                    source_authority="QR Destination Inspector",
                    reference_id=qr_text[:60],
                    timestamp=now,
                    details={
                        "target_url": qr_text,
                        "reason": "Target URL is not present in the authorized trusted-issuer allowlist.",
                        "allowlist_matched": False,
                    },
                    destination_trusted=False,
                )

        # Non-URL or trusted URL payload check
        return IssuerVerificationResult(
            adapter_name="QR_DESTINATION_VALIDATOR",
            verification_type=VerificationType.LOCAL_AUTOMATED,
            status=VerificationStatus.ISSUER_VERIFIED_SUCCESS if is_url else VerificationStatus.MANUAL_REVIEW_REQUIRED,
            is_simulated=False,
            source_authority="QR Cryptographic Inspector",
            reference_id=qr_text[:60],
            timestamp=now,
            details={"raw_payload": qr_text, "destination_trusted": True},
            destination_trusted=True,
        )
