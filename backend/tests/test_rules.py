import pytest
from datetime import date
from app.rules.evaluator import APHRuleEvaluator
from app.schemas.findings import FindingOutcome


def test_aph_fsr_ug_engineering():
    evaluator = APHRuleEvaluator()
    # 240 students, 12 faculty -> ratio 1:20 -> exactly compliant
    res = evaluator.evaluate_fsr("TEST-01", "ENGINEERING_AND_TECHNOLOGY", "UG", 240, 12)
    assert res.outcome == FindingOutcome.COMPLIANT

    # 240 students, 10 faculty -> ratio 1:24 -> deficit of 2 faculty
    res_def = evaluator.evaluate_fsr("TEST-02", "ENGINEERING_AND_TECHNOLOGY", "UG", 240, 10)
    assert res_def.outcome == FindingOutcome.DISCREPANCY_FOUND
    assert "Shortfall of 2 faculty" in res_def.evidence.discrepancy_magnitude


def test_aph_cadre_ratio():
    evaluator = APHRuleEvaluator()
    # 0 Professors, 14 Assistant Professors -> Deficit
    res = evaluator.evaluate_cadre_ratio("TEST-03", 0, 0, 14)
    assert res.outcome == FindingOutcome.DISCREPANCY_FOUND
    assert "0 Professors" in res.title


def test_aph_land_discrepancy_math():
    evaluator = APHRuleEvaluator()
    # Declared 5.0 acres vs 2.1 acres documented -> 2.9 acres discrepancy
    res = evaluator.evaluate_land_consistency("TEST-04", 5.0, 2.1)
    assert res.outcome == FindingOutcome.DISCREPANCY_FOUND
    assert "2.9 Acres Variance" in res.title
    assert "2.90 Acres discrepancy" in res.evidence.discrepancy_magnitude
