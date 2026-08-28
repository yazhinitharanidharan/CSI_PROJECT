"""
Deterministic scoring engine for the LiquidityOS Decision Engine.

Purpose:
    Convert the financial consequences of candidate actions and plans
    into deterministic, comparable scores.

Important:
    - This module does NOT override hard constraints.
    - constraints.py decides whether a plan is feasible.
    - This module scores feasible candidates.
    - Higher score means better economic outcome.
    - Decimal is used for monetary calculations.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from .models import Action, Plan, PlanMetrics


# ---------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ScoringWeights:
    """
    Weights used for risk-adjusted scoring.

    A weight of 1 means the component is used directly.
    Higher weights make that component more important.

    These are Decision Engine policy values, not LLM decisions.
    """

    financing_cost: Decimal = Decimal("1.0")
    late_penalty: Decimal = Decimal("1.0")
    supplier_risk: Decimal = Decimal("1.0")
    liquidity_risk: Decimal = Decimal("1.0")
    financing_exposure: Decimal = Decimal("1.0")
    decision_instability: Decimal = Decimal("1.0")

    def __post_init__(self) -> None:
        """Validate scoring weights."""

        for name in (
            "financing_cost",
            "late_penalty",
            "supplier_risk",
            "liquidity_risk",
            "financing_exposure",
            "decision_instability",
        ):
            value = getattr(self, name)

            if value < Decimal("0"):
                raise ValueError(
                    f"{name} weight cannot be negative."
                )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _decimal(value: Any, field_name: str) -> Decimal:
    """
    Safely convert a numeric value to Decimal.

    Float values are first converted through str() to avoid
    binary floating-point artifacts.
    """

    if isinstance(value, Decimal):
        return value

    if isinstance(value, float):
        return Decimal(str(value))

    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(
            f"{field_name} must be a valid numeric value."
        ) from exc


def _non_negative(value: Decimal, field_name: str) -> None:
    """Ensure a value is not negative."""

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} cannot be negative."
        )


def _read_value(
    obj: Any,
    field_name: str,
    default: Any = None,
) -> Any:
    """Read a value from either an object or a dictionary."""

    if isinstance(obj, Mapping):
        return obj.get(field_name, default)

    return getattr(
        obj,
        field_name,
        default,
    )


# ---------------------------------------------------------------------
# ACTION SCORING
# ---------------------------------------------------------------------

def calculate_action_cost(
    action: Action,
    liquidity_risk: Decimal = Decimal("0"),
    financing_exposure: Decimal = Decimal("0"),
    weights: Optional[ScoringWeights] = None,
) -> Decimal:
    """
    Calculate the risk-adjusted cost of an action.

    Formula:

        ActionCost =
            FinancingCost
            - DiscountSavings
            + LatePenalty
            + SupplierRisk
            + LiquidityRisk
            + FinancingExposure

    Lower cost is better.

    Args:
        action:
            Existing Action model.

        liquidity_risk:
            Monetary equivalent of liquidity risk.

        financing_exposure:
            Monetary financing exposure.

        weights:
            Optional scoring weights.

    Returns:
        Risk-adjusted action cost.
    """

    if weights is None:
        weights = ScoringWeights()

    liquidity_risk = _decimal(
        liquidity_risk,
        "liquidity_risk",
    )

    financing_exposure = _decimal(
        financing_exposure,
        "financing_exposure",
    )

    _non_negative(
        liquidity_risk,
        "liquidity_risk",
    )

    _non_negative(
        financing_exposure,
        "financing_exposure",
    )

    cost = (
        weights.financing_cost
        * action.financing_cost
        - action.discount_value
        + weights.late_penalty
        * action.penalty_cost
        + weights.supplier_risk
        * action.supplier_risk_cost
        + weights.liquidity_risk
        * liquidity_risk
        + weights.financing_exposure
        * financing_exposure
    )

    return cost.quantize(
        Decimal("0.0001")
    )


def calculate_action_benefit(
    action: Action,
    penalty_avoided: Decimal = Decimal("0"),
    liquidity_value_preserved: Decimal = Decimal("0"),
) -> Decimal:
    """
    Calculate the direct financial benefit of an action.

    Formula:

        ActionBenefit =
            DiscountSavings
            + PenaltyAvoided
            + LiquidityValuePreserved

    Higher benefit is better.
    """

    penalty_avoided = _decimal(
        penalty_avoided,
        "penalty_avoided",
    )

    liquidity_value_preserved = _decimal(
        liquidity_value_preserved,
        "liquidity_value_preserved",
    )

    _non_negative(
        penalty_avoided,
        "penalty_avoided",
    )

    _non_negative(
        liquidity_value_preserved,
        "liquidity_value_preserved",
    )

    benefit = (
        action.discount_value
        + penalty_avoided
        + liquidity_value_preserved
    )

    return benefit.quantize(
        Decimal("0.0001")
    )


def calculate_action_risk(
    action: Action,
    liquidity_risk: Decimal = Decimal("0"),
    financing_exposure: Decimal = Decimal("0"),
) -> Decimal:
    """
    Calculate the total risk associated with an action.

    Formula:

        ActionRisk =
            SupplierRisk
            + LiquidityRisk
            + FinancingExposure

    Financing cost and penalty remain separate cost components.
    """

    liquidity_risk = _decimal(
        liquidity_risk,
        "liquidity_risk",
    )

    financing_exposure = _decimal(
        financing_exposure,
        "financing_exposure",
    )

    _non_negative(
        liquidity_risk,
        "liquidity_risk",
    )

    _non_negative(
        financing_exposure,
        "financing_exposure",
    )

    risk = (
        action.supplier_risk_cost
        + liquidity_risk
        + financing_exposure
    )

    return risk.quantize(
        Decimal("0.0001")
    )


def calculate_action_score(
    action: Action,
    liquidity_risk: Decimal = Decimal("0"),
    financing_exposure: Decimal = Decimal("0"),
    penalty_avoided: Decimal = Decimal("0"),
    liquidity_value_preserved: Decimal = Decimal("0"),
    weights: Optional[ScoringWeights] = None,
) -> Decimal:
    """
    Calculate the final score of a candidate action.

    Formula:

        ActionScore =
            ActionBenefit
            - ActionCost

    Higher score is better.
    """

    benefit = calculate_action_benefit(
        action=action,
        penalty_avoided=penalty_avoided,
        liquidity_value_preserved=liquidity_value_preserved,
    )

    cost = calculate_action_cost(
        action=action,
        liquidity_risk=liquidity_risk,
        financing_exposure=financing_exposure,
        weights=weights,
    )

    return (
        benefit - cost
    ).quantize(
        Decimal("0.0001")
    )


# ---------------------------------------------------------------------
# PLAN SCORING
# ---------------------------------------------------------------------

def calculate_plan_cost(
    plan: Plan,
    liquidity_shortfall_cost: Optional[Decimal] = None,
    financial_exposure_cost: Optional[Decimal] = None,
    decision_instability_cost: Optional[Decimal] = None,
    weights: Optional[ScoringWeights] = None,
) -> Decimal:
    """
    Calculate the complete risk-adjusted cost of a plan.

    Formula:

        PlanCost =
            FinancingCost
            + LatePaymentPenalty
            - DiscountSavings
            + SupplierRiskCost
            + LiquidityShortfallCost
            + FinancialExposureCost
            + DecisionInstabilityCost

    Lower cost is better.
    """

    if weights is None:
        weights = ScoringWeights()

    metrics = plan.metrics

    liquidity_shortfall_cost = (
        metrics.liquidity_shortfall_cost
        if liquidity_shortfall_cost is None
        else _decimal(
            liquidity_shortfall_cost,
            "liquidity_shortfall_cost",
        )
    )

    financial_exposure_cost = (
        metrics.financial_exposure_cost
        if financial_exposure_cost is None
        else _decimal(
            financial_exposure_cost,
            "financial_exposure_cost",
        )
    )

    decision_instability_cost = (
        metrics.decision_instability_cost
        if decision_instability_cost is None
        else _decimal(
            decision_instability_cost,
            "decision_instability_cost",
        )
    )

    _non_negative(
        liquidity_shortfall_cost,
        "liquidity_shortfall_cost",
    )

    _non_negative(
        financial_exposure_cost,
        "financial_exposure_cost",
    )

    _non_negative(
        decision_instability_cost,
        "decision_instability_cost",
    )

    cost = (
        weights.financing_cost
        * metrics.financing_cost
        + weights.late_penalty
        * metrics.late_payment_penalty
        - metrics.discount_savings
        + weights.supplier_risk
        * metrics.supplier_risk_cost
        + weights.liquidity_risk
        * liquidity_shortfall_cost
        + weights.financing_exposure
        * financial_exposure_cost
        + weights.decision_instability
        * decision_instability_cost
    )

    return cost.quantize(
        Decimal("0.0001")
    )


def calculate_plan_savings(
    plan: Plan,
) -> Decimal:
    """
    Calculate total discount savings generated by the plan.

    Formula:

        PlanSavings = TotalDiscountSavings
    """

    return plan.total_discount_savings.quantize(
        Decimal("0.0001")
    )


def calculate_plan_risk(
    plan: Plan,
    liquidity_shortfall_cost: Optional[Decimal] = None,
    financial_exposure_cost: Optional[Decimal] = None,
) -> Decimal:
    """
    Calculate total risk exposure of a plan.

    Formula:

        PlanRisk =
            SupplierRiskCost
            + LiquidityShortfallCost
            + FinancialExposureCost
            + FinancingRiskExposure
    """

    metrics = plan.metrics

    if liquidity_shortfall_cost is None:
        liquidity_shortfall_cost = (
            metrics.liquidity_shortfall_cost
        )

    if financial_exposure_cost is None:
        financial_exposure_cost = (
            metrics.financial_exposure_cost
        )

    liquidity_shortfall_cost = _decimal(
        liquidity_shortfall_cost,
        "liquidity_shortfall_cost",
    )

    financial_exposure_cost = _decimal(
        financial_exposure_cost,
        "financial_exposure_cost",
    )

    _non_negative(
        liquidity_shortfall_cost,
        "liquidity_shortfall_cost",
    )

    _non_negative(
        financial_exposure_cost,
        "financial_exposure_cost",
    )

    financing_exposure = sum(
        (
            decision.risk_exposure
            for decision in plan.financing_decisions
        ),
        Decimal("0"),
    )

    risk = (
        metrics.supplier_risk_cost
        + liquidity_shortfall_cost
        + financial_exposure_cost
        + financing_exposure
    )

    return risk.quantize(
        Decimal("0.0001")
    )


def calculate_plan_liquidity(
    plan: Plan,
    forecast_result: Any,
) -> dict[str, Any]:
    """
    Calculate liquidity metrics using the finalized ForecastResult.

    ForecastResult:

        days
        minimum_cash
        reserve_requirement
        reserve_breach
        survival_horizon_days
        forecast_horizon_days
        forecast_confidence
        scenario_id
        scenario_name

    ForecastDay:

        date
        projected_cash
        inflows
        outflows

    Reserve breach is defined as:

        projected_cash < reserve_requirement
    """

    days = _read_value(
        forecast_result,
        "days",
    )

    if not days:
        raise ValueError(
            "ForecastResult.days cannot be empty."
        )

    reserve_requirement = _decimal(
        _read_value(
            forecast_result,
            "reserve_requirement",
        ),
        "reserve_requirement",
    )

    minimum_cash = _decimal(
        _read_value(
            forecast_result,
            "minimum_cash",
        ),
        "minimum_cash",
    )

    reported_breach = bool(
        _read_value(
            forecast_result,
            "reserve_breach",
            False,
        )
    )

    minimum_projected_cash = None
    total_inflows = Decimal("0")
    total_outflows = Decimal("0")

    breach_days: list[dict[str, str]] = []

    for day in days:

        projected_cash = _decimal(
            _read_value(
                day,
                "projected_cash",
            ),
            "projected_cash",
        )

        inflows = _decimal(
            _read_value(
                day,
                "inflows",
                Decimal("0"),
            ),
            "inflows",
        )

        outflows = _decimal(
            _read_value(
                day,
                "outflows",
                Decimal("0"),
            ),
            "outflows",
        )

        _non_negative(
            inflows,
            "forecast inflows",
        )

        _non_negative(
            outflows,
            "forecast outflows",
        )

        if (
            minimum_projected_cash is None
            or projected_cash < minimum_projected_cash
        ):
            minimum_projected_cash = projected_cash

        total_inflows += inflows
        total_outflows += outflows

        if projected_cash < reserve_requirement:
            breach_days.append(
                {
                    "date": str(
                        _read_value(day, "date")
                    ),
                    "projected_cash": str(
                        projected_cash
                    ),
                    "reserve_requirement": str(
                        reserve_requirement
                    ),
                }
            )

    calculated_breach = bool(
        breach_days
    )

    if reported_breach != calculated_breach:
        raise ValueError(
            "ForecastResult.reserve_breach does not match "
            "the ForecastDay values."
        )

    liquidity_buffer = (
        minimum_projected_cash
        - reserve_requirement
    )

    return {
        "minimum_cash": minimum_cash,
        "minimum_projected_cash": minimum_projected_cash,
        "reserve_requirement": reserve_requirement,
        "liquidity_buffer": liquidity_buffer,
        "reserve_breach": calculated_breach,
        "breach_days": breach_days,
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "survival_horizon_days": _read_value(
            forecast_result,
            "survival_horizon_days",
        ),
        "forecast_horizon_days": _read_value(
            forecast_result,
            "forecast_horizon_days",
        ),
        "forecast_confidence": _read_value(
            forecast_result,
            "forecast_confidence",
        ),
        "scenario_id": _read_value(
            forecast_result,
            "scenario_id",
        ),
        "scenario_name": _read_value(
            forecast_result,
            "scenario_name",
        ),
        "retained_cash": plan.retained_cash,
    }


def calculate_plan_score(
    plan: Plan,
    weights: Optional[ScoringWeights] = None,
) -> Decimal:
    """
    Calculate the final deterministic plan score.

    Formula:

        PlanScore = -PlanCost

    Therefore:

        lower cost → higher score
        higher cost → lower score

    The optimizer can therefore use max(score) to select the best
    feasible plan.
    """

    plan_cost = calculate_plan_cost(
        plan=plan,
        weights=weights,
    )

    return (
        -plan_cost
    ).quantize(
        Decimal("0.0001")
    )


def evaluate_plan(
    plan: Plan,
    forecast_result: Optional[Any] = None,
    weights: Optional[ScoringWeights] = None,
) -> PlanMetrics:
    """
    Evaluate a complete plan and return updated PlanMetrics.

    This combines:

        financing cost
        late-payment penalty
        discount savings
        supplier risk
        liquidity shortfall
        financial exposure
        decision instability
        projected liquidity

    The function does not determine feasibility.

    Hard-constraint validation remains the responsibility of
    constraints.py.
    """

    if weights is None:
        weights = ScoringWeights()

    old_metrics = plan.metrics

    liquidity_data: dict[str, Any] = {}

    if forecast_result is not None:
        liquidity_data = calculate_plan_liquidity(
            plan=plan,
            forecast_result=forecast_result,
        )

    financing_cost = plan.total_financing_cost

    late_payment_penalty = (
        old_metrics.late_payment_penalty
    )

    discount_savings = (
        plan.total_discount_savings
    )

    supplier_risk_cost = (
        old_metrics.supplier_risk_cost
    )

    liquidity_shortfall_cost = (
        old_metrics.liquidity_shortfall_cost
    )

    financial_exposure_cost = (
        old_metrics.financial_exposure_cost
    )

    decision_instability_cost = (
        old_metrics.decision_instability_cost
    )

    if liquidity_data.get("reserve_breach", False):

        minimum_cash = liquidity_data[
            "minimum_projected_cash"
        ]

        reserve = liquidity_data[
            "reserve_requirement"
        ]

        shortfall = max(
            reserve - minimum_cash,
            Decimal("0"),
        )

        liquidity_shortfall_cost = shortfall

    total_cost = (
        weights.financing_cost
        * financing_cost
        + weights.late_penalty
        * late_payment_penalty
        - discount_savings
        + weights.supplier_risk
        * supplier_risk_cost
        + weights.liquidity_risk
        * liquidity_shortfall_cost
        + weights.financing_exposure
        * financial_exposure_cost
        + weights.decision_instability
        * decision_instability_cost
    )

    return PlanMetrics(
        total_cost=total_cost.quantize(
            Decimal("0.0001")
        ),
        financing_cost=financing_cost.quantize(
            Decimal("0.0001")
        ),
        late_payment_penalty=late_payment_penalty.quantize(
            Decimal("0.0001")
        ),
        discount_savings=discount_savings.quantize(
            Decimal("0.0001")
        ),
        supplier_risk_cost=supplier_risk_cost.quantize(
            Decimal("0.0001")
        ),
        liquidity_shortfall_cost=liquidity_shortfall_cost.quantize(
            Decimal("0.0001")
        ),
        financial_exposure_cost=financial_exposure_cost.quantize(
            Decimal("0.0001")
        ),
        decision_instability_cost=decision_instability_cost.quantize(
            Decimal("0.0001")
        ),
        minimum_projected_cash=(
            liquidity_data.get(
                "minimum_projected_cash",
                old_metrics.minimum_projected_cash,
            )
        ),
        retained_cash=plan.retained_cash,
        liquidity_reserve=(
            liquidity_data.get(
                "reserve_requirement",
                old_metrics.liquidity_reserve,
            )
        ),
        shortfall_probability=(
            old_metrics.shortfall_probability
        ),
        supplier_risk_score=(
            old_metrics.supplier_risk_score
        ),
        liquidity_survival_horizon_days=int(
            liquidity_data.get(
                "survival_horizon_days",
                old_metrics.liquidity_survival_horizon_days,
            )
        ),
        reserve_violations=int(
            liquidity_data.get(
                "reserve_violations",
                len(
                    liquidity_data.get(
                        "breach_days",
                        [],
                    )
                ),
            )
        ),
    )