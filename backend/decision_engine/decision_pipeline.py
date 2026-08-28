"""Authoritative orchestration of the existing Decision Engine components."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from .advanced_optimizer import monte_carlo_evaluate, optimize_allocations, risk_indicator
from .financing_engine import FinancingOption, select_best_financing_option
from .liquidity_firewall import FirewallStatus, evaluate_transaction, firewall_summary
from .pareto_optimizer import find_pareto_frontier, rank_pareto_plans, select_preferred_pareto_plan


def _read(item: Any, field: str, default: Any = None) -> Any:
    return item.get(field, default) if isinstance(item, Mapping) else getattr(item, field, default)


def _decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _jsonable(value: Any) -> Any:
    """Serialize at the API boundary without changing existing component APIs."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _transaction_amount(invoices: Sequence[Any], proposed_transaction: Any | None) -> Decimal:
    if proposed_transaction is not None:
        return _decimal(_read(proposed_transaction, "cash_impact", _read(proposed_transaction, "amount", proposed_transaction)))
    return sum((_decimal(_read(invoice, "amount", 0)) for invoice in invoices), Decimal("0"))


def _initial_financial_decision(amount: Decimal, financing_options: Sequence[FinancingOption], financing_days: int) -> Any:
    """Obtain the deterministic first-layer financing evaluation when possible."""
    eligible = [option for option in financing_options if option.eligible and option.available_limit > 0]
    if amount <= 0 or not eligible:
        return None
    return select_best_financing_option(min(amount, max(option.available_limit for option in eligible)), financing_days, eligible)


def _firewall_payload(result: Any) -> dict[str, Any]:
    summary = firewall_summary(result)
    return {
        "status": summary["status"],
        "allowed": summary["allowed"],
        "risk_level": summary["risk"]["level"],
        "risk_score": summary["risk"]["score"],
        "protected_cash": summary["liquidity"]["protected_cash"],
        "projected_cash": summary["liquidity"]["projected_cash"],
        "safety_margin": summary["liquidity"]["safety_margin"],
        "human_approval_required": summary["human_approval_required"],
        "reasons": summary["reasons"],
    }


def run_decision_pipeline(*, state: Any, forecast: Any, invoices: Sequence[Any], financing_options: Sequence[FinancingOption], proposed_transaction: Any | None = None, supplier_risks: Sequence[Any] = (), firewall_financing_options: Sequence[Any] = (), financing_days: int = 30, risk_mode: str = "NORMAL", iterations: int = 1000, seed: int | None = None, **optimizer_kwargs: Any) -> dict[str, Any]:
    """Run Finance -> Firewall -> LP -> Monte Carlo -> Pareto, in that order.

    The firewall is a terminal safety gate: neither blocked nor human-approval
    decisions enter the optimizer automatically.
    """
    amount = _transaction_amount(invoices, proposed_transaction)
    initial = _initial_financial_decision(amount, financing_options, financing_days)
    firewall_result = evaluate_transaction(
        state,
        proposed_transaction if proposed_transaction is not None else {"amount": amount},
        forecast=forecast,
        supplier_risks=supplier_risks,
        financing_options=firewall_financing_options,
    )
    firewall = _firewall_payload(firewall_result)

    if firewall_result.status == FirewallStatus.BLOCKED:
        return _jsonable({"initial_decision": initial, "firewall": firewall, "optimization": None, "risk": None, "pareto": {"strategy": None, "chart": []}, "final_decision": {"action": "BLOCKED", "reason": "Dynamic Liquidity Firewall blocked this transaction."}, "conclusion": {"headline": "Transaction blocked", "summary": "The proposed transaction breaches protected liquidity.", "risk": firewall_result.risk_level, "confidence": "HIGH", "survival_probability": None, "why": list(firewall_result.reasons)}})
    if firewall_result.status == FirewallStatus.HUMAN_APPROVAL:
        return _jsonable({"initial_decision": initial, "firewall": firewall, "optimization": None, "risk": None, "pareto": {"strategy": None, "chart": []}, "final_decision": {"action": "HUMAN_APPROVAL", "reason": "Dynamic Liquidity Firewall requires human approval."}, "conclusion": {"headline": "Human approval required", "summary": "The transaction is inside the liquidity boundary but risk requires escalation.", "risk": firewall_result.risk_level, "confidence": "MEDIUM", "survival_probability": None, "why": list(firewall_result.reasons)}})

    optimization = optimize_allocations(state=state, forecast=forecast, invoices=invoices, financing_options=financing_options, financing_days=financing_days, **optimizer_kwargs)
    public_optimization = {key: value for key, value in optimization.items() if key != "plan"}
    if not optimization["feasible"]:
        return _jsonable({"initial_decision": initial, "firewall": firewall, "optimization": public_optimization, "risk": None, "pareto": {"strategy": None, "chart": []}, "final_decision": {"action": "ESCALATE", "reason": optimization["explanation"]}, "conclusion": {"headline": "No feasible optimized plan", "summary": optimization["explanation"], "risk": "HIGH", "confidence": "LOW", "survival_probability": None, "why": [optimization["explanation"]]}})

    risk = monte_carlo_evaluate(optimization["plan"], state, forecast, iterations=iterations, seed=seed)
    # Only the optimizer's hard-constraint-feasible plan reaches Pareto.
    frontier = rank_pareto_plans(find_pareto_frontier([optimization["plan"]]))
    selected = select_preferred_pareto_plan(frontier, risk_mode)
    chart = [{"plan": item["strategy"].title(), "cost": item["objectives"]["cost"], "minimum_liquidity": item["objectives"]["liquidity"], "supplier_risk": item["objectives"]["supplier_risk"], "financing_exposure": item["objectives"]["financing_exposure"], "selected": item is selected} for item in frontier]
    confidence = "HIGH" if risk["risk_level"] == "LOW" else "MEDIUM"
    final = {"action": "PAY", "amount": amount, "financing": sum((item["amount"] for item in optimization["financing_allocations"]), Decimal("0")), "remaining_cash": optimization["remaining_cash"], "confidence": confidence, "reason": "Firewall approved the transaction; the optimized plan passed existing constraints."}
    return _jsonable({"initial_decision": initial, "firewall": firewall, "optimization": public_optimization, "risk": risk_indicator(risk), "pareto": {"strategy": selected["strategy"] if selected else None, "chart": chart}, "final_decision": final, "conclusion": {"headline": "Pay invoices using the approved plan", "summary": "The Dynamic Liquidity Firewall approved the decision and the existing optimizer found a feasible plan.", "risk": risk["risk_level"], "confidence": confidence, "survival_probability": risk["survival_probability"], "why": ["Dynamic protected liquidity is maintained", "Existing hard constraints passed", "Only feasible plans reached Pareto selection"]}})
