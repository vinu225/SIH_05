from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import date


class RuleApplicability(BaseModel):
    program_category: str  # e.g. "ENGINEERING_AND_TECHNOLOGY", "MANAGEMENT", "ALL"
    level: str  # e.g. "UG", "PG", "DIPLOMA", "ALL"


class APHRuleModel(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    status: str = "ACTIVE"
    aph_edition: str = "AICTE Approval Process Handbook 2024-2027"
    clause_reference: str
    handbook_page_no: Optional[int] = None
    title: str
    description: str
    applicability: RuleApplicability
    effective_from: date
    effective_until: Optional[date] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
