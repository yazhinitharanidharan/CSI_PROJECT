"""
Tests for the Decision Engine hard-constraint layer.

These tests verify that:
    - valid inputs pass
    - invalid inputs are rejected
    - duplicate payments are rejected
    - payment-window violations are rejected
    - financing-limit violations are rejected
    - financing eligibility is enforced
    - maximum delays are enforced
    - mandatory obligations are protected
    - critical supplier coverage is enforced
    - cash-flow violations are detected
    - Liquidity Firewall violations are detected

Run with:

    python -m pytest backend/decision_engine/tests/test_constraints.py -v
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.decision_engine.constraints import (
    ConstraintResult,
    is_plan_feasible,
    validate_cash_flow,
    validate_critical_supplier_coverage,
    validate_duplicate_payment,
    validate_firewall,
    validate_financing_eligibility,
    validate_financing_limit,
    validate_invoice,
    validate_mandatory_obligations,
    validate_maximum_delay,
    validate_payment_window,
)

from backend.decision_engine.models import (
    Action,
    ActionType,
    FinancingDecision,
    FundingSource,
    PaymentDecision,
    Plan,
    PlanMetrics,
)


# ---------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------

def make_invoice(
    invoice_id: str = "INV-001",
    amount: Decimal = Decimal("100000"),
    due_date: date = date(2026, 9, 10),
    payment_status: str = "unpaid",
    permissible_delay_days: int = 5,
) -> dict:
    """
    Create a simple invoice dictionary for constraint testing.

    This is test data only. It does not create a new production model.
    """

    return {
        "invoice_id": invoice_id,
        "amount": amount,
        "due_date": due_date,
        "payment_status": payment_status,
        "permissible_delay_days": permissible_delay_days,
    }


def make_forecast(
    projected_cash: Decimal = Decimal("200000"),
    reserve_requirement: Decimal = Decimal("100000"),
    reserve_breach: bool = False,
) -> dict:
    """
    Create a minimal ForecastResult-compatible test object.
    """

    return {
        "days": [
            {
                "date": date(2026, 9, 1),
                "projected_cash": projected_cash,
                "inflows": Decimal("100000"),
                "outflows": Decimal("50000"),
            }
        ],
        "minimum_cash": projected_cash,
        "reserve_requirement": reserve_requirement,
        "reserve_breach": reserve_breach,
        "survival_horizon_days": 1,
        "forecast_horizon_days": 1,
        "forecast_confidence": Decimal("1.0"),
        "scenario_id": "base",
        "scenario_name": "Base",
    }


def make_plan(
    invoice_id: str = "INV-001",
    payment_date: date = date(2026, 9, 10),
) -> Plan:
    """
    Create a minimal Plan using the existing project models.
    """

    payment = PaymentDecision(
        invoice_id=invoice_id,
        action_type=ActionType.PAY_MATURITY,
        scheduled_date=payment_date,
        amount=Decimal("100000"),
        discount_savings=Decimal("0"),
        penalty_cost=Decimal("0"),
        supplier_risk_cost=Decimal("0"),
        liquidity_impact=Decimal("100000"),
    )

    metrics = PlanMetrics()

    return Plan(
        plan_id="PLAN-001",
        payment_decisions=[payment],
        financing_decisions=[],
        metrics=metrics,
    )


# ---------------------------------------------------------------------
# 1. Invoice validation
# ---------------------------------------------------------------------

def test_validate_invoice_accepts_valid_invoice() -> None:
    """A valid unpaid invoice should pass."""

    invoice = make_invoice()

    result = validate_invoice(invoice)

    assert isinstance(result, ConstraintResult)
    assert result.valid is True


def test_validate_invoice_rejects_zero_amount() -> None:
    """An invoice with zero amount must be rejected."""

    invoice = make_invoice(
        amount=Decimal("0")
    )

    result = validate_invoice(invoice)

    assert result.valid is False


# ---------------------------------------------------------------------
# 2. Duplicate payment
# ---------------------------------------------------------------------

def test_duplicate_payment_is_rejected() -> None:
    """An invoice with an existing payment must be rejected."""

    invoice = make_invoice()

    existing_payments = [
        {
            "invoice_id": "INV-001",
            "status": "paid",
        }
    ]

    result = validate_duplicate_payment(
        invoice,
        existing_payments,
    )

    assert result.valid is False


def test_duplicate_payment_passes_when_none_exists() -> None:
    """An invoice without an existing payment should pass."""

    invoice = make_invoice()

    result = validate_duplicate_payment(
        invoice,
        [],
    )

    assert result.valid is True


# ---------------------------------------------------------------------
# 3. Payment window
# ---------------------------------------------------------------------

def test_payment_window_accepts_valid_payment_date() -> None:
    """Payment on the due date should be accepted."""

    invoice = make_invoice()

    result = validate_payment_window(
        invoice,
        date(2026, 9, 10),
    )

    assert result.valid is True


def test_payment_window_rejects_payment_after_due_date() -> None:
    """Payment after the due date should fail when no later
    maturity/absolute deadline is supplied.
    """

    invoice = make_invoice(
        permissible_delay_days=0
    )

    result = validate_payment_window(
        invoice,
        date(2026, 9, 15),
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# 4. Financing limit
# ---------------------------------------------------------------------

def test_financing_limit_accepts_amount_within_limit() -> None:
    """Financing below the available limit should pass."""

    decision = FinancingDecision(
        financing_option_id="BANK-001",
        funding_source=FundingSource.BANK,
        amount=Decimal("50000"),
        financing_cost=Decimal("1000"),
        risk_exposure=Decimal("500"),
    )

    result = validate_financing_limit(
        decision,
        Decimal("100000"),
    )

    assert result.valid is True


def test_financing_limit_rejects_amount_above_limit() -> None:
    """Financing above the available limit must fail."""

    decision = FinancingDecision(
        financing_option_id="BANK-001",
        funding_source=FundingSource.BANK,
        amount=Decimal("150000"),
        financing_cost=Decimal("3000"),
        risk_exposure=Decimal("1500"),
    )

    result = validate_financing_limit(
        decision,
        Decimal("100000"),
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# 5. Financing eligibility
# ---------------------------------------------------------------------

def test_financing_eligibility_accepts_eligible_bank() -> None:
    """An eligible bank financing source should pass."""

    decision = FinancingDecision(
        financing_option_id="BANK-001",
        funding_source=FundingSource.BANK,
        amount=Decimal("50000"),
    )

    result = validate_financing_eligibility(
        decision,
        {
            FundingSource.BANK,
        },
    )

    assert result.valid is True


def test_financing_eligibility_rejects_ineligible_source() -> None:
    """A financing source outside the allowed set must fail."""

    decision = FinancingDecision(
        financing_option_id="BANK-001",
        funding_source=FundingSource.BANK,
        amount=Decimal("50000"),
    )

    result = validate_financing_eligibility(
        decision,
        {
            FundingSource.SUPPLIER,
        },
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# 6. Maximum delay
# ---------------------------------------------------------------------

def test_maximum_delay_accepts_permitted_delay() -> None:
    """Payment within the permissible delay should pass."""

    invoice = make_invoice(
        permissible_delay_days=5
    )

    result = validate_maximum_delay(
        invoice,
        date(2026, 9, 15),
    )

    assert result.valid is True


def test_maximum_delay_rejects_excessive_delay() -> None:
    """Payment beyond the permissible delay must fail."""

    invoice = make_invoice(
        permissible_delay_days=5
    )

    result = validate_maximum_delay(
        invoice,
        date(2026, 9, 20),
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# 7. Mandatory obligations
# ---------------------------------------------------------------------

def test_mandatory_obligation_is_covered() -> None:
    """A mandatory obligation included in the plan should pass."""

    plan = make_plan(
        invoice_id="OBL-001"
    )

    obligations = [
        {
            "obligation_id": "OBL-001",
            "mandatory": True,
            "paid": False,
        }
    ]

    result = validate_mandatory_obligations(
        plan,
        obligations,
    )

    assert result.valid is True


def test_missing_mandatory_obligation_is_rejected() -> None:
    """A mandatory obligation missing from the plan must fail."""

    plan = make_plan(
        invoice_id="INV-001"
    )

    obligations = [
        {
            "obligation_id": "OBL-999",
            "mandatory": True,
            "paid": False,
        }
    ]

    result = validate_mandatory_obligations(
        plan,
        obligations,
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# 8. Critical supplier coverage
# ---------------------------------------------------------------------

def test_critical_supplier_invoice_is_covered() -> None:
    """Covered critical supplier invoice should pass."""

    plan = make_plan(
        invoice_id="CRITICAL-001"
    )

    result = validate_critical_supplier_coverage(
        plan,
        ["CRITICAL-001"],
    )

    assert result.valid is True


def test_missing_critical_supplier_invoice_is_rejected() -> None:
    """Uncovered critical supplier invoice must fail."""

    plan = make_plan(
        invoice_id="INV-001"
    )

    result = validate_critical_supplier_coverage(
        plan,
        ["CRITICAL-999"],
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# 9. Cash flow
# ---------------------------------------------------------------------

def test_cash_flow_passes_when_plan_is_funded() -> None:
    """A funded plan with sufficient forecast liquidity should pass."""

    plan = make_plan()

    forecast = make_forecast(
        projected_cash=Decimal("200000"),
        reserve_requirement=Decimal("100000"),
        reserve_breach=False,
    )

    result = validate_cash_flow(
        plan=plan,
        initial_deployable_cash=Decimal("200000"),
        forecast_result=forecast,
    )

    assert result.valid is True


def test_cash_flow_rejects_insufficient_cash() -> None:
    """A plan requiring more funding than available must fail."""

    plan = make_plan()

    forecast = make_forecast(
        projected_cash=Decimal("200000"),
        reserve_requirement=Decimal("100000"),
        reserve_breach=False,
    )

    result = validate_cash_flow(
        plan=plan,
        initial_deployable_cash=Decimal("50000"),
        forecast_result=forecast,
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# 10. Liquidity Firewall
# ---------------------------------------------------------------------

def test_firewall_passes_above_reserve() -> None:
    """Projected cash above reserve should pass."""

    plan = make_plan()

    forecast = make_forecast(
        projected_cash=Decimal("150000"),
        reserve_requirement=Decimal("100000"),
        reserve_breach=False,
    )

    result = validate_firewall(
        plan,
        forecast,
    )

    assert result.valid is True


def test_firewall_rejects_below_reserve() -> None:
    """Projected cash below reserve must fail."""

    plan = make_plan()

    forecast = make_forecast(
        projected_cash=Decimal("80000"),
        reserve_requirement=Decimal("100000"),
        reserve_breach=True,
    )

    result = validate_firewall(
        plan,
        forecast,
    )

    assert result.valid is False


def test_firewall_does_not_use_zero_as_reserve_threshold() -> None:
    """
    Demonstrate the agreed semantics:

        80,000 projected cash
        100,000 reserve

    is a Firewall violation even though cash is still positive.
    """

    plan = make_plan()

    forecast = make_forecast(
        projected_cash=Decimal("80000"),
        reserve_requirement=Decimal("100000"),
        reserve_breach=True,
    )

    result = validate_firewall(
        plan,
        forecast,
    )

    assert result.valid is False


# ---------------------------------------------------------------------
# Feasibility helper
# ---------------------------------------------------------------------

def test_is_plan_feasible_when_all_constraints_pass() -> None:
    """All passing constraints should make the plan feasible."""

    results = [
        ConstraintResult(
            valid=True,
            constraint="test_one",
            reason="Passed",
            details={},
        ),
        ConstraintResult(
            valid=True,
            constraint="test_two",
            reason="Passed",
            details={},
        ),
    ]

    assert is_plan_feasible(results) is True


def test_is_plan_feasible_when_one_constraint_fails() -> None:
    """One failed hard constraint must make the plan infeasible."""

    results = [
        ConstraintResult(
            valid=True,
            constraint="test_one",
            reason="Passed",
            details={},
        ),
        ConstraintResult(
            valid=False,
            constraint="firewall",
            reason="Reserve breached",
            details={},
        ),
    ]

    assert is_plan_feasible(results) is False