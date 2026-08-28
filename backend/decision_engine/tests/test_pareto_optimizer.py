from decimal import Decimal

from backend.decision_engine.pareto_optimizer import (
    dominates,
    find_pareto_frontier,
    rank_pareto_plans,
    select_preferred_pareto_plan,
)


def candidate(name, cost, liquidity, risk, exposure, feasible=True):
    return {"name": name, "feasible": feasible, "cost": Decimal(cost), "liquidity": Decimal(liquidity), "supplier_risk": Decimal(risk), "financing_exposure": Decimal(exposure)}


def test_dominance_treats_liquidity_as_a_maximized_objective():
    better = candidate("better", "10", "100", "2", "5")
    worse = candidate("worse", "10", "90", "2", "5")
    assert dominates(better, worse)
    assert not dominates(worse, better)


def test_frontier_removes_dominated_and_infeasible_candidates():
    best = candidate("best", "10", "100", "2", "5")
    dominated = candidate("dominated", "12", "90", "3", "6")
    infeasible = candidate("bad", "1", "1000", "0", "0", False)
    frontier = find_pareto_frontier([best, dominated, infeasible])
    assert [item["plan"]["name"] for item in frontier] == ["best"]


def test_policy_selects_liquidity_protected_plan():
    frontier = find_pareto_frontier([candidate("cost", "5", "80", "5", "10"), candidate("liquid", "8", "120", "4", "8")])
    selected = select_preferred_pareto_plan(rank_pareto_plans(frontier), "LIQUIDITY_STRESS")
    assert selected["plan"]["name"] == "liquid"
