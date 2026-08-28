from datetime import date
from decimal import Decimal
import json

from backend.decision_engine.advanced_optimizer import (
    monte_carlo_evaluate,
    optimize_decision,
    optimize_allocations,
)
from backend.decision_engine.financing_engine import FinancingOption
from backend.decision_engine.models import FundingSource


class State:
    deployable_cash = Decimal("150")


def safe_forecast():
    return {
        "reserve_requirement": Decimal("100"),
        "minimum_cash": Decimal("150"),
        "reserve_breach": False,
        "days": [{"date": date(2026, 1, 1), "projected_cash": Decimal("150"), "inflows": Decimal("0"), "outflows": Decimal("0")}],
    }


def invoice():
    return [{"invoice_id": "INV-1", "amount": Decimal("100"), "due_date": date(2026, 1, 1)}]


def option(limit=Decimal("75")):
    return FinancingOption("BANK-1", FundingSource.BANK, Decimal("0.10"), Decimal("0"), limit)


def test_lp_finds_feasible_solution_and_respects_reserve_and_limit():
    result = optimize_allocations(state=State(), forecast=safe_forecast(), invoices=invoice(), financing_options=[option()])
    assert result["feasible"] is True
    assert result["remaining_cash"] >= Decimal("100")
    assert result["financing_allocations"][0]["amount"] <= Decimal("75")


def test_lp_rejects_insufficient_financing_limit():
    result = optimize_allocations(state=State(), forecast=safe_forecast(), invoices=invoice(), financing_options=[option(Decimal("25"))])
    assert result["feasible"] is False


def test_monte_carlo_returns_requested_scenarios_and_risk_level():
    result = optimize_allocations(state=State(), forecast=safe_forecast(), invoices=invoice(), financing_options=[option()])
    risk = monte_carlo_evaluate(result["plan"], State(), safe_forecast(), iterations=20, seed=7)
    assert risk["iterations"] == 20
    assert Decimal("0") <= risk["survival_probability"] <= Decimal("1")
    assert risk["risk_level"] in {"LOW", "MEDIUM", "HIGH"}


def test_pipeline_selects_a_frontend_json_safe_pareto_plan():
    result = optimize_decision(state=State(), forecast=safe_forecast(), invoices=invoice(), financing_options=[option()], iterations=5, seed=1)
    assert result["pareto"]["selected_plan"] is not None
    assert result["final_decision"]["action"] == "PAY"
    json.dumps(result)
