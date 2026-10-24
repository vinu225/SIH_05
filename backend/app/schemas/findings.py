from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class AssessmentPillar(str, Enum):
    AUTHENTICITY = "AUTHENTICITY"
    COMPLETENESS = "COMPLETENESS"
    REGULATORY_COMPLIANCE = "REGULATORY_COMPLIANCE"


class FindingOutcome(str, Enum):
    COMPLIANT = "Compliant"
    DISCREPANCY_FOUND = "Discrepancy Found"
    REQUIRED_EVIDENCE_MISSING = "Required Evidence Missing"
    UNABLE_TO_DETERMINE = "Unable to Determine"


class OfficerResolutionStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED = "ACCEPTED"
    OVERRIDDEN = "OVERRIDDEN"
    REFERRED_FOR_INSPECTION = "REFERRED_FOR_INSPECTION"


class NormalizedBoundingBox(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0, description="Normalized X coordinate (0.0 to 1.0 from left)")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized Y coordinate (0.0 to 1.0 from top)")
    width: float = Field(..., ge=0.0, le=1.0, description="Normalized width (0.0 to 1.0)")
    height: float = Field(..., ge=0.0, le=1.0, description="Normalized height (0.0 to 1.0)")


class FindingEvidence(BaseModel):
    source_document_id: str
    source_document_name: str
    page_number: int
    normalized_bbox: Optional[NormalizedBoundingBox] = None
    extracted_value: Any
    compared_against: Optional[Dict[str, Any]] = None
    discrepancy_magnitude: Optional[str] = None
    heatmap_overlay_url: Optional[str] = None


class ApplicableRuleReference(BaseModel):
    rule_id: str
    version: str
    aph_edition: str = "AICTE Approval Process Handbook 2024-2027"
    clause_reference: str
    statutory_basis: str


class ConfidenceOrUncertainty(BaseModel):
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    uncertainty_notes: Optional[str] = None


class OfficerResolution(BaseModel):
    status: OfficerResolutionStatus = OfficerResolutionStatus.PENDING_REVIEW
    officer_id: Optional[str] = None
    override_reason: Optional[str] = None
    timestamp: Optional[datetime] = None


class FindingRecord(BaseModel):
    finding_id: str
    assessment_pillar: AssessmentPillar
    outcome: FindingOutcome
    title: str
    description: str
    applicable_rule: ApplicableRuleReference
    evidence: FindingEvidence
    confidence_or_uncertainty: ConfidenceOrUncertainty
    officer_resolution: OfficerResolution = Field(default_factory=OfficerResolution)
