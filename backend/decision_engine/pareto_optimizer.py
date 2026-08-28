"""Pareto selection for plans that have already passed hard constraints."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from .models import Plan
from .scoring import calculate_plan_cost, calculate_plan_risk


def _decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _value(plan: Plan | Mapping[str, Any], name: str) -> Any:
    return plan.get(name) if isinstance(plan, Mapping) else getattr(plan, name, None)


def _feasible(plan: Plan | Mapping[str, Any]) -> bool:
    return bool(_value(plan, "feasible"))


def calculate_pareto_objectives(plan: Plan | Mapping[str, Any]) -> dict[str, Decimal]:
    """Cost/risk/exposure are minimized; liquidity is maximized."""
    if isinstance(plan, Plan):
        return {"cost": calculate_plan_cost(plan), "liquidity": plan.metrics.minimum_projected_cash, "supplier_risk": calculate_plan_risk(plan), "financing_exposure": plan.total_financing_draw}
    source = _value(plan, "objectives") or plan
    return {"cost": _decimal(source.get("cost", 0)), "liquidity": _decimal(source.get("liquidity", source.get("minimum_liquidity", 0))), "supplier_risk": _decimal(source.get("supplier_risk", 0)), "financing_exposure": _decimal(source.get("financing_exposure", 0))}


def dominates(plan_a: Plan | Mapping[str, Any], plan_b: Plan | Mapping[str, Any]) -> bool:
    """Return true only if A is no worse everywhere and better somewhere."""
    if not _feasible(plan_a):
        return False
    if not _feasible(plan_b):
        return True
    a, b = calculate_pareto_objectives(plan_a), calculate_pareto_objectives(plan_b)
    no_worse = a["cost"] <= b["cost"] and a["supplier_risk"] <= b["supplier_risk"] and a["financing_exposure"] <= b["financing_exposure"] and a["liquidity"] >= b["liquidity"]
    better = a["cost"] < b["cost"] or a["supplier_risk"] < b["supplier_risk"] or a["financing_exposure"] < b["financing_exposure"] or a["liquidity"] > b["liquidity"]
    return no_worse and better


def find_pareto_frontier(plans: Iterable[Plan | Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Filter infeasible and dominated plans, retaining deterministic input order."""
    candidates = [plan for plan in plans if _feasible(plan)]
    return [{"plan": plan, "objectives": calculate_pareto_objectives(plan)} for plan in candidates if not any(other is not plan and dominates(other, plan) for other in candidates)]


def rank_pareto_plans(frontier: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach explainable labels; no label implies mathematical global optimality."""
    items = [dict(item) for item in frontier]
    if not items:
        return []
    for item in items:
        objective = item["objectives"]
        item["normalized_score"] = sum((
            Decimal("1") if objective["cost"] == min(i["objectives"]["cost"] for i in items) else Decimal("0"),
            Decimal("1") if objective["liquidity"] == max(i["objectives"]["liquidity"] for i in items) else Decimal("0"),
            Decimal("1") if objective["supplier_risk"] == min(i["objectives"]["supplier_risk"] for i in items) else Decimal("0"),
            Decimal("1") if objective["financing_exposure"] == min(i["objectives"]["financing_exposure"] for i in items) else Decimal("0"),
        )) / Decimal("4")
        if objective["cost"] == min(i["objectives"]["cost"] for i in items):
            item["strategy"] = "COST OPTIMIZED"
        elif objective["liquidity"] == max(i["objectives"]["liquidity"] for i in items):
            item["strategy"] = "LIQUIDITY PROTECTED"
        elif objective["supplier_risk"] == min(i["objectives"]["supplier_risk"] for i in items):
            item["strategy"] = "SUPPLIER PROTECTED"
        else:
            item["strategy"] = "BALANCED"
    return sorted(items, key=lambda item: (-item["normalized_score"], item["strategy"]))


def select_preferred_pareto_plan(ranked_plans: Iterable[dict[str, Any]], risk_mode: str = "NORMAL") -> dict[str, Any] | None:
    """Apply risk policy only to the feasible Pareto frontier."""
    plans = list(ranked_plans)
    if not plans:
        return None
    if risk_mode.upper() == "LIQUIDITY_STRESS":
        return max(plans, key=lambda item: item["objectives"]["liquidity"])
    if risk_mode.upper() == "SUPPLIER_CRISIS":
        return min(plans, key=lambda item: item["objectives"]["supplier_risk"])
    return max(plans, key=lambda item: item["normalized_score"])
