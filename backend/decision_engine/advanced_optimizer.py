"""Constraint-first LP allocation, Monte Carlo validation, and orchestration.

The deterministic financing engine remains the first financing decision layer.
This module consumes its evaluations; it does not reproduce its formulae.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date
from decimal import Decimal
from random import Random
from enum import Enum
from typing import Any, Mapping, Sequence

from scipy.optimize import linprog

from .constraints import ConstraintResult, is_plan_feasible, validate_plan
from .financing_engine import FinancingOption, compare_financing_options, select_best_financing_option
from .models import ActionType, FinancingDecision, PaymentDecision, Plan, PlanMetrics
from .pareto_optimizer import find_pareto_frontier, rank_pareto_plans, select_preferred_pareto_plan


@dataclass(frozen=True)
class MonteCarloConfig:
    """Configurable uncertainty and risk thresholds."""
    inflow_variation: Decimal = Decimal("0.10")
    outflow_variation: Decimal = Decimal("0.10")
    low_risk_threshold: Decimal = Decimal("0.95")
    medium_risk_threshold: Decimal = Decimal("0.90")


def _decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _read(item: Any, field: str, default: Any = None) -> Any:
    return item.get(field, default) if isinstance(item, Mapping) else getattr(item, field, default)


def _invoices(invoices: Sequence[Any]) -> list[dict[str, Any]]:
    records = []
    for invoice in invoices:
        invoice_id, amount, due_date = _read(invoice, "invoice_id"), _read(invoice, "amount"), _read(invoice, "due_date")
        if not invoice_id or amount is None or not isinstance(due_date, date):
            raise ValueError("Each invoice needs invoice_id, amount, and a date due_date.")
        records.append({"invoice_id": str(invoice_id), "amount": _decimal(amount), "due_date": due_date, "payment_status": _read(invoice, "payment_status", _read(invoice, "status", "unpaid")), "permissible_delay_days": _read(invoice, "permissible_delay_days", 0)})
    return records


def _statuses(results: Sequence[ConstraintResult]) -> list[dict[str, Any]]:
    return [{"constraint": r.constraint, "valid": r.valid, "reason": r.reason} for r in results]


def _failure(reason: str, constraint: str, *, initial: Any = None, state: Any = None, forecast: Any = None) -> dict[str, Any]:
    cash = _decimal(_read(state, "deployable_cash", 0))
    minimum = _decimal(_read(forecast, "minimum_cash", 0))
    return {"feasible": False, "objective_value": None, "allocations": [], "financing_allocations": [], "remaining_cash": cash, "minimum_liquidity": minimum, "financing_cost": Decimal("0"), "constraint_status": [{"constraint": constraint, "valid": False, "reason": reason}], "initial_financing_decision": initial, "explanation": reason}


def optimize_allocations(*, state: Any, forecast: Any, invoices: Sequence[Any], financing_options: Sequence[FinancingOption], financing_days: int = 30, mandatory_obligations: Sequence[Any] = (), critical_supplier_invoice_ids: Sequence[str] = (), existing_payments: Sequence[Any] = ()) -> dict[str, Any]:
    """Use LP to allocate external funding, then recheck existing constraints.

    Invoice settlement is fixed by the supplied records. Each LP variable is a
    financing draw. Bounds come from FinancingOption.available_limit; the LP
    requires enough draw to retain the reserve, then minimizes established
    financing-engine per-unit cost estimates.
    """
    records = _invoices(invoices)
    reserve, base_minimum = _decimal(_read(forecast, "reserve_requirement")), _decimal(_read(forecast, "minimum_cash"))
    deployable = _decimal(_read(state, "deployable_cash"))
    total_due = sum((record["amount"] for record in records), Decimal("0"))
    if bool(_read(forecast, "reserve_breach")) or base_minimum < reserve:
        return _failure("Base forecast breaches the Liquidity Firewall.", "firewall", state=state, forecast=forecast)
    eligible = [option for option in financing_options if option.eligible and option.available_limit > 0]
    required = max(Decimal("0"), total_due - (deployable - reserve))
    initial = None
    if eligible and required:
        initial = select_best_financing_option(min(required, max(option.available_limit for option in eligible)), financing_days, eligible)
    if required > sum((option.available_limit for option in eligible), Decimal("0")):
        return _failure("Eligible financing limits cannot preserve the required reserve.", "financing_limit", initial=initial, state=state, forecast=forecast)
    if not required:
        draws = [Decimal("0") for _ in eligible]
        objective = Decimal("0")
    elif not eligible:
        return _failure("No eligible financing source is available.", "financing_eligibility", initial=initial, state=state, forecast=forecast)
    else:
        coefficients = []
        for option in eligible:
            sample = min(option.available_limit, Decimal("10000"))
            evaluation = compare_financing_options(sample, financing_days, [option])[0]
            coefficients.append(float(evaluation.total_cost / sample))
        lp = linprog(c=coefficients, A_ub=[[-1.0] * len(eligible)], b_ub=[-float(required)], bounds=[(0, float(option.available_limit)) for option in eligible], method="highs")
        if not lp.success:
            return _failure("No feasible LP allocation was found.", "lp", initial=initial, state=state, forecast=forecast)
        draws, objective = [Decimal(str(value)).quantize(Decimal("0.01")) for value in lp.x], Decimal(str(lp.fun)).quantize(Decimal("0.0001"))

    financing, financing_allocations = [], []
    for option, draw in zip(eligible, draws):
        if draw <= 0:
            continue
        evaluation = compare_financing_options(draw, financing_days, [option])[0]
        financing.append(FinancingDecision(financing_option_id=option.option_id, funding_source=option.funding_source, amount=draw, interest_cost=evaluation.interest_cost, fixed_fee=evaluation.fixed_fee, financing_cost=evaluation.total_cost, remaining_limit=option.available_limit - draw, approval_required=option.approval_required))
        financing_allocations.append({"option_id": option.option_id, "funding_source": option.funding_source.value, "amount": draw, "cost": evaluation.total_cost})
    financed = sum(draws, Decimal("0"))
    remaining = deployable - total_due + financed
    minimum = min(base_minimum, remaining)
    total_cost = sum((decision.financing_cost for decision in financing), Decimal("0"))
    plan = Plan(plan_id="advanced-lp", payment_decisions=tuple(PaymentDecision(invoice_id=r["invoice_id"], action_type=ActionType.PAY_MATURITY, scheduled_date=r["due_date"], amount=r["amount"], liquidity_impact=r["amount"]) for r in records), financing_decisions=tuple(financing), retained_cash=max(remaining, Decimal("0")), metrics=PlanMetrics(total_cost=total_cost, financing_cost=total_cost, minimum_projected_cash=max(minimum, Decimal("0")), retained_cash=max(remaining, Decimal("0")), liquidity_reserve=reserve))
    validations = validate_plan(plan, invoices=records, existing_payments=existing_payments, mandatory_obligations=mandatory_obligations, critical_supplier_invoice_ids=critical_supplier_invoice_ids, forecast_result=forecast, initial_deployable_cash=deployable, financing_limits={o.option_id: o.available_limit for o in eligible}, eligible_financing_sources={o.funding_source for o in eligible})
    reserve_ok = remaining >= reserve
    feasible = reserve_ok and is_plan_feasible(validations)
    return {"feasible": feasible, "objective_value": objective, "allocations": [{"invoice_id": r["invoice_id"], "amount": r["amount"]} for r in records], "financing_allocations": financing_allocations, "remaining_cash": remaining, "minimum_liquidity": minimum, "financing_cost": total_cost, "constraint_status": _statuses(validations) + [{"constraint": "optimizer_reserve", "valid": reserve_ok, "reason": "Remaining cash respects reserve." if reserve_ok else "Remaining cash breaches reserve."}], "initial_financing_decision": initial, "plan": plan, "explanation": "LP result was revalidated by existing hard constraints and the Liquidity Firewall."}


def monte_carlo_evaluate(plan: Plan, state: Any, forecast: Any, *, iterations: int = 1000, seed: int | None = None, config: MonteCarloConfig | None = None) -> dict[str, Any]:
    """Stress forecast inflows/outflows; deterministic constraints are never altered."""
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero.")
    config, random = config or MonteCarloConfig(), Random(seed)
    reserve = _decimal(_read(forecast, "reserve_requirement"))
    direct_cash = plan.total_payment_amount - plan.total_financing_draw
    minima, successful = [], 0
    for _ in range(iterations):
        cash, minimum = _decimal(_read(state, "deployable_cash")) - direct_cash, _decimal(_read(state, "deployable_cash")) - direct_cash
        for day in _read(forecast, "days", []):
            inflow_factor = Decimal(str(1 + random.uniform(-float(config.inflow_variation), float(config.inflow_variation))))
            outflow_factor = Decimal(str(1 + random.uniform(-float(config.outflow_variation), float(config.outflow_variation))))
            cash += _decimal(_read(day, "inflows", 0)) * inflow_factor - _decimal(_read(day, "outflows", 0)) * outflow_factor
            minimum = min(minimum, cash)
        minima.append(minimum)
        successful += minimum >= reserve
    minima.sort()
    probability = Decimal(successful) / Decimal(iterations)
    level = "LOW" if probability >= config.low_risk_threshold else "MEDIUM" if probability >= config.medium_risk_threshold else "HIGH"
    percentile = lambda q: minima[int((len(minima) - 1) * q)]
    return {"iterations": iterations, "successful_scenarios": successful, "failed_scenarios": iterations - successful, "survival_probability": probability, "minimum_cash": minima[0], "p05_minimum_cash": percentile(Decimal("0.05")), "p50_minimum_cash": percentile(Decimal("0.50")), "reserve_requirement": reserve, "safety_margin": percentile(Decimal("0.05")) - reserve, "risk_level": level}


def risk_indicator(risk: Mapping[str, Any]) -> dict[str, Any]:
    return {"survival_probability": risk["survival_probability"], "risk_level": risk["risk_level"], "scenarios_tested": risk["iterations"], "scenarios_survived": risk["successful_scenarios"], "minimum_cash": risk["minimum_cash"], "reserve_requirement": risk["reserve_requirement"], "safety_margin": risk["safety_margin"]}


def _jsonable(value: Any) -> Any:
    """Convert internal financial/model objects to a compact JSON-safe value."""
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


def optimize_decision(*, state: Any, forecast: Any, invoices: Sequence[Any], financing_options: Sequence[FinancingOption], risk_mode: str = "NORMAL", iterations: int = 1000, seed: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Financing decision -> LP -> Monte Carlo -> Pareto frontend response."""
    lp = optimize_allocations(state=state, forecast=forecast, invoices=invoices, financing_options=financing_options, **kwargs)
    public_lp = {key: value for key, value in lp.items() if key != "plan"}
    if not lp["feasible"]:
        return _jsonable({"initial_decision": lp.get("initial_financing_decision"), "lp_result": public_lp, "risk": None, "pareto": {"frontier": [], "selected_plan": None, "strategy": None, "chart": []}, "final_decision": {"action": "ESCALATE", "confidence": "LOW", "reason": lp["explanation"]}, "conclusion": {"headline": "Escalate for review", "summary": lp["explanation"], "risk": "HIGH", "confidence": "LOW", "why": [lp["explanation"]]}})
    risk = monte_carlo_evaluate(lp["plan"], state, forecast, iterations=iterations, seed=seed)
    frontier = rank_pareto_plans(find_pareto_frontier([lp["plan"]]))
    selected = select_preferred_pareto_plan(frontier, risk_mode)
    chart = [{"plan": item["strategy"].title(), "cost": item["objectives"]["cost"], "minimum_liquidity": item["objectives"]["liquidity"], "supplier_risk": item["objectives"]["supplier_risk"], "financing_exposure": item["objectives"]["financing_exposure"], "selected": item is selected} for item in frontier]
    final = {"action": "PAY", "amount": sum((x["amount"] for x in lp["allocations"]), Decimal("0")), "financing": sum((x["amount"] for x in lp["financing_allocations"]), Decimal("0")), "remaining_cash": lp["remaining_cash"], "confidence": "HIGH" if risk["risk_level"] == "LOW" else "MEDIUM", "reason": "Plan maintained hard constraints and the Liquidity Firewall before risk validation."}
    return _jsonable({"initial_decision": lp.get("initial_financing_decision"), "lp_result": public_lp, "risk": risk_indicator(risk), "pareto": {"frontier": [{"strategy": item["strategy"], "objectives": item["objectives"]} for item in frontier], "selected_plan": {"strategy": selected["strategy"], "objectives": selected["objectives"]} if selected else None, "strategy": selected["strategy"] if selected else None, "chart": chart}, "final_decision": final, "conclusion": {"headline": "Pay invoices using optimized financing", "summary": "Best available balance of cost, liquidity, supplier risk, and financing exposure.", "risk": risk["risk_level"], "confidence": final["confidence"], "survival_probability": risk["survival_probability"], "why": ["Maintains required reserve", "Passed hard constraints", f"Survives {risk['survival_probability'] * Decimal('100')}% of seeded simulations"]}})
