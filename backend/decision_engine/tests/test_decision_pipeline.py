from datetime import date
from decimal import Decimal
import inspect
import json

import backend.decision_engine.decision_pipeline as pipeline


class State:
    deployable_cash = Decimal("1000")

    class Policy:
        minimum_reserve = Decimal("100")

    risk_policy = Policy()
    obligations = []
    receivables = []


def forecast():
    return {"reserve_requirement": Decimal("100"), "minimum_cash": Decimal("1000"), "reserve_breach": False, "days": [{"date": date(2026, 1, 1), "projected_cash": Decimal("1000"), "inflows": Decimal("0"), "outflows": Decimal("0")}]} 


def invoices(amount=Decimal("100")):
    return [{"invoice_id": "INV-1", "amount": amount, "due_date": date(2026, 1, 1)}]


def test_blocked_firewall_prevents_optimizer_execution(monkeypatch):
    monkeypatch.setattr(pipeline, "optimize_allocations", lambda **kwargs: (_ for _ in ()).throw(AssertionError("optimizer must not run")))
    result = pipeline.run_decision_pipeline(state=State(), forecast=forecast(), invoices=invoices(Decimal("950")), financing_options=[])
    assert result["firewall"]["status"] == "BLOCKED"
    assert result["optimization"] is None


def test_human_approval_prevents_automatic_execution(monkeypatch):
    monkeypatch.setattr(pipeline, "optimize_allocations", lambda **kwargs: (_ for _ in ()).throw(AssertionError("optimizer must not run")))
    risks = [{"criticality_score": 100, "distress_score": 100, "disruption_probability": "1", "cascade_risk_score": 100}]
    result = pipeline.run_decision_pipeline(state=State(), forecast=forecast(), invoices=invoices(), financing_options=[], supplier_risks=risks)
    assert result["firewall"]["status"] == "HUMAN_APPROVAL"
    assert result["final_decision"]["action"] == "HUMAN_APPROVAL"


def test_safe_decision_reaches_existing_optimizer():
    result = pipeline.run_decision_pipeline(state=State(), forecast=forecast(), invoices=invoices(), financing_options=[], iterations=5, seed=1)
    assert result["firewall"]["status"] == "SAFE"
    assert result["optimization"]["feasible"] is True
    assert result["final_decision"]["action"] == "PAY"


def test_unsafe_plan_cannot_reach_pareto(monkeypatch):
    monkeypatch.setattr(pipeline, "optimize_allocations", lambda **kwargs: {"feasible": False, "explanation": "constraints failed"})
    monkeypatch.setattr(pipeline, "find_pareto_frontier", lambda plans: (_ for _ in ()).throw(AssertionError("Pareto must not run")))
    result = pipeline.run_decision_pipeline(state=State(), forecast=forecast(), invoices=invoices(), financing_options=[])
    assert result["pareto"]["chart"] == []
    assert result["final_decision"]["action"] == "ESCALATE"


def test_final_response_is_json_serializable():
    result = pipeline.run_decision_pipeline(state=State(), forecast=forecast(), invoices=invoices(), financing_options=[], iterations=5, seed=1)
    json.dumps(result)


def test_pipeline_reuses_existing_components_instead_of_reimplementing_them():
    source = inspect.getsource(pipeline)
    assert "select_best_financing_option" in source
    assert "evaluate_transaction" in source
    assert "optimize_allocations" in source
    assert "monte_carlo_evaluate" in source
    assert "find_pareto_frontier" in source
    assert "linprog" not in source
