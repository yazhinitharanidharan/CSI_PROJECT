import json
from decimal import Decimal

from backend.decision_engine.liquidity_firewall import (
    FirewallStatus,
    calculate_dynamic_protected_cash,
    evaluate_transaction,
    firewall_summary,
)


class State:
    deployable_cash = Decimal("1000")

    class Policy:
        minimum_reserve = Decimal("100")

    risk_policy = Policy()
    obligations = []
    receivables = []


def test_minimum_policy_reserve_is_always_protected():
    result = calculate_dynamic_protected_cash(State())
    assert result["protected_cash"] >= Decimal("100")


def test_future_obligations_increase_protected_cash():
    baseline = calculate_dynamic_protected_cash(State())
    protected = calculate_dynamic_protected_cash(State(), obligations=[{"amount": "200"}])
    assert protected["protected_cash"] > baseline["protected_cash"]


def test_mandatory_obligation_is_fully_protected():
    protected = calculate_dynamic_protected_cash(State(), obligations=[{"amount": "200", "mandatory": True}])
    assert protected["future_obligation_requirement"] == Decimal("200")


def test_receivable_uncertainty_increases_buffer():
    protected = calculate_dynamic_protected_cash(State(), receivables=[{"amount": "500", "uncertainty": "0.4"}])
    assert protected["receivable_uncertainty_buffer"] == Decimal("200.0")


def test_supplier_risk_increases_buffer():
    low = calculate_dynamic_protected_cash(State(), supplier_risks=[{"criticality_score": 10, "distress_score": 10, "disruption_probability": "0.1", "cascade_risk_score": 10}])
    high = calculate_dynamic_protected_cash(State(), supplier_risks=[{"criticality_score": 100, "distress_score": 100, "disruption_probability": "1", "cascade_risk_score": 100}])
    assert high["supplier_risk_buffer"] > low["supplier_risk_buffer"]


def test_reliable_financing_conservatively_reduces_pressure():
    without_financing = calculate_dynamic_protected_cash(State(), obligations=[{"amount": "500", "mandatory": True}])
    with_financing = calculate_dynamic_protected_cash(State(), obligations=[{"amount": "500", "mandatory": True}], financing_options=[{"eligible": True, "available_limit": "100", "reliability": "1"}])
    assert with_financing["financing_adjustment"] == Decimal("80.0")
    assert with_financing["protected_cash"] < without_financing["protected_cash"]


def test_unreliable_financing_is_not_guaranteed_cash():
    result = calculate_dynamic_protected_cash(State(), financing_options=[{"eligible": True, "available_limit": "1000", "reliability": "0.5"}])
    assert result["financing_adjustment"] == Decimal("0")


def test_safe_transaction_returns_safe():
    result = evaluate_transaction(State(), Decimal("100"))
    assert result.status == FirewallStatus.SAFE
    assert result.allowed is True


def test_transaction_below_boundary_is_blocked():
    result = evaluate_transaction(State(), Decimal("950"))
    assert result.status == FirewallStatus.BLOCKED
    assert result.allowed is False


def test_high_risk_but_safe_transaction_requires_human_approval():
    result = evaluate_transaction(State(), Decimal("100"), supplier_risks=[{"criticality_score": 90, "distress_score": 90, "disruption_probability": "0.9", "cascade_risk_score": 90}])
    assert result.status == FirewallStatus.HUMAN_APPROVAL
    assert result.human_approval_required is True


def test_critical_risk_is_classified_correctly():
    result = evaluate_transaction(State(), Decimal("100"), supplier_risks=[{"criticality_score": 100, "distress_score": 100, "disruption_probability": "1", "cascade_risk_score": 100}])
    assert result.risk_level == "CRITICAL"


def test_safety_margin_is_correct():
    result = evaluate_transaction(State(), Decimal("100"))
    assert result.safety_margin == Decimal("800")


def test_firewall_summary_is_json_serializable():
    result = evaluate_transaction(State(), Decimal("100"))
    summary = firewall_summary(result)
    assert summary["status"] == "SAFE"
    json.dumps(summary)
