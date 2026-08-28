"""
Models for the LiquidityOS decision engine.

These models represent candidate actions, final decisions,
plans, and plan evaluation metrics.

The models do not make financial decisions.
The deterministic decision engine will make those decisions
in later phases.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class ActionType(str, Enum):
    """Types of actions that can be considered for an invoice."""

    PAY_MATURITY = "pay_maturity"
    PAY = "pay_maturity"
    DEFER = "defer"
    FINANCE = "finance"
    RETAIN = "retain"
    ESCALATE = "escalate"


class FundingSource(str, Enum):
    """Sources that can be used to fund an invoice."""

    CASH = "cash"
    BANK = "bank"
    SUPPLIER_FINANCE = "supplier_finance"
    SUPPLIER = "supplier_finance"


@dataclass(frozen=True)
class Action:
    """
    Represents one possible action for an invoice.

    An Action is only a candidate. It is not necessarily selected.
    """

    invoice_id: str
    action_type: ActionType
    scheduled_date: date
    amount: Decimal

    funding_source: Optional[FundingSource] = None
    financing_option_id: Optional[str] = None

    discount_value: Decimal = Decimal("0")
    annualized_discount_return: Decimal = Decimal("0")
    penalty_cost: Decimal = Decimal("0")
    financing_cost: Decimal = Decimal("0")
    supplier_risk_cost: Decimal = Decimal("0")

    priority_score: Decimal = Decimal("0")

    feasible: bool = True

    rejection_reasons: tuple[str, ...] = field(default_factory=tuple)

    explanation_factors: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the basic action data."""

        if not self.invoice_id:
            raise ValueError("invoice_id cannot be empty.")

        if self.amount <= Decimal("0"):
            raise ValueError("amount must be greater than zero.")

        if self.discount_value < Decimal("0"):
            raise ValueError("discount_value cannot be negative.")

        if self.annualized_discount_return < Decimal("0"):
            raise ValueError(
                "annualized_discount_return cannot be negative."
            )

        if self.penalty_cost < Decimal("0"):
            raise ValueError("penalty_cost cannot be negative.")

        if self.financing_cost < Decimal("0"):
            raise ValueError("financing_cost cannot be negative.")

        if self.supplier_risk_cost < Decimal("0"):
            raise ValueError("supplier_risk_cost cannot be negative.")

    @property
    def net_cost(self) -> Decimal:
        """
        Return the estimated net cost of this candidate action.

        Discount savings reduce the overall cost.
        """

        return (
            self.financing_cost
            + self.penalty_cost
            + self.supplier_risk_cost
            - self.discount_value
        )


@dataclass(frozen=True)
class PaymentDecision:
    """
    Represents the final payment decision for an invoice.

    This object is created only after the deterministic decision
    engine has evaluated candidate actions and constraints.
    """

    invoice_id: str
    action_type: ActionType
    scheduled_date: date
    amount: Decimal

    funding_source: Optional[FundingSource] = None

    discount_value: Decimal = Decimal("0")
    penalty_avoided: Decimal = Decimal("0")
    financing_cost: Decimal = Decimal("0")
    discount_savings: Decimal = Decimal("0")
    penalty_cost: Decimal = Decimal("0")
    supplier_risk_cost: Decimal = Decimal("0")
    liquidity_impact: Decimal = Decimal("0")

    priority_score: Decimal = Decimal("0")
    supplier_risk_impact: Decimal = Decimal("0")

    approval_required: bool = False

    rationale: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the payment decision."""

        if not self.invoice_id:
            raise ValueError("invoice_id cannot be empty.")

        if self.amount <= Decimal("0"):
            raise ValueError("amount must be greater than zero.")

        if self.discount_value < Decimal("0"):
            raise ValueError("discount_value cannot be negative.")

        if self.penalty_avoided < Decimal("0"):
            raise ValueError("penalty_avoided cannot be negative.")

        if self.financing_cost < Decimal("0"):
            raise ValueError("financing_cost cannot be negative.")

        if self.discount_savings < Decimal("0"):
            raise ValueError("discount_savings cannot be negative.")

        if self.penalty_cost < Decimal("0"):
            raise ValueError("penalty_cost cannot be negative.")

        if self.supplier_risk_cost < Decimal("0"):
            raise ValueError("supplier_risk_cost cannot be negative.")

    @property
    def net_financial_benefit(self) -> Decimal:
        """
        Return the direct financial benefit of the payment decision.
        """

        return (
            self.discount_value
            + self.penalty_avoided
            - self.financing_cost
        )


@dataclass(frozen=True)
class FinancingDecision:
    """
    Represents a financing decision selected by the engine.

    It records how much financing is used, its cost, remaining
    facility capacity, and risk exposure.
    """

    financing_option_id: str
    funding_source: FundingSource

    amount: Decimal
    scheduled_date: Optional[date] = None

    interest_cost: Decimal = Decimal("0")
    fixed_fee: Decimal = Decimal("0")
    financing_cost: Decimal = Decimal("0")

    remaining_limit: Decimal = Decimal("0")
    risk_exposure: Decimal = Decimal("0")

    approval_required: bool = False

    rationale: dict[str, Any] = field(default_factory=dict)

    @property
    def total_financing_cost(self) -> Decimal:
        """Backward-compatible total financing cost."""
        return self.financing_cost

    remaining_limit: Decimal = Decimal("0")
    risk_exposure: Decimal = Decimal("0")

    approval_required: bool = False

    rationale: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate financing decision data."""

        if not self.financing_option_id:
            raise ValueError(
                "financing_option_id cannot be empty."
            )

        if self.amount <= Decimal("0"):
            raise ValueError("amount must be greater than zero.")

        if self.interest_cost < Decimal("0"):
            raise ValueError("interest_cost cannot be negative.")

        if self.fixed_fee < Decimal("0"):
            raise ValueError("fixed_fee cannot be negative.")

        if self.financing_cost < Decimal("0"):
            raise ValueError(
                "financing_cost cannot be negative."
            )

        if self.remaining_limit < Decimal("0"):
            raise ValueError("remaining_limit cannot be negative.")

        if self.risk_exposure < Decimal("0"):
            raise ValueError("risk_exposure cannot be negative.")


@dataclass(frozen=True)
class PlanMetrics:
    """
    Financial and risk metrics used to evaluate a complete plan.
    """

    total_cost: Decimal = Decimal("0")

    financing_cost: Decimal = Decimal("0")
    late_payment_penalty: Decimal = Decimal("0")
    discount_savings: Decimal = Decimal("0")

    supplier_risk_cost: Decimal = Decimal("0")
    liquidity_shortfall_cost: Decimal = Decimal("0")
    financial_exposure_cost: Decimal = Decimal("0")
    decision_instability_cost: Decimal = Decimal("0")

    minimum_projected_cash: Decimal = Decimal("0")
    retained_cash: Decimal = Decimal("0")
    liquidity_reserve: Decimal = Decimal("0")

    shortfall_probability: Decimal = Decimal("0")
    supplier_risk_score: Decimal = Decimal("0")

    liquidity_survival_horizon_days: int = 0
    reserve_violations: int = 0

    def __post_init__(self) -> None:
        """Validate plan metrics."""

        monetary_fields = (
            "total_cost",
            "financing_cost",
            "late_payment_penalty",
            "discount_savings",
            "supplier_risk_cost",
            "liquidity_shortfall_cost",
            "financial_exposure_cost",
            "decision_instability_cost",
            "minimum_projected_cash",
            "retained_cash",
            "liquidity_reserve",
        )

        for field_name in monetary_fields:
            value = getattr(self, field_name)

            if value < Decimal("0"):
                raise ValueError(
                    f"{field_name} cannot be negative."
                )

        if not Decimal("0") <= self.shortfall_probability <= Decimal("1"):
            raise ValueError(
                "shortfall_probability must be between 0 and 1."
            )

        if self.supplier_risk_score < Decimal("0"):
            raise ValueError(
                "supplier_risk_score cannot be negative."
            )

        if self.liquidity_survival_horizon_days < 0:
            raise ValueError(
                "liquidity_survival_horizon_days cannot be negative."
            )

        if self.reserve_violations < 0:
            raise ValueError(
                "reserve_violations cannot be negative."
            )

    @property
    def calculated_total_cost(self) -> Decimal:
        """
        Calculate risk-adjusted total cost from its components.
        """

        return (
            self.financing_cost
            + self.late_payment_penalty
            + self.supplier_risk_cost
            + self.liquidity_shortfall_cost
            + self.financial_exposure_cost
            + self.decision_instability_cost
            - self.discount_savings
        )

    @property
    def reserve_buffer(self) -> Decimal:
        """Return cash available above the required liquidity reserve."""

        return (
            self.minimum_projected_cash
            - self.liquidity_reserve
        )


@dataclass(frozen=True)
class Plan:
    """
    Represents a complete capital-allocation strategy.

    A plan contains payment decisions, financing decisions,
    retained cash, metrics, constraint results and explanations.
    """

    plan_id: str

    payment_decisions: tuple[PaymentDecision, ...] = field(
        default_factory=tuple
    )

    financing_decisions: tuple[FinancingDecision, ...] = field(
        default_factory=tuple
    )

    retained_cash: Decimal = Decimal("0")

    metrics: PlanMetrics = field(
        default_factory=PlanMetrics
    )

    feasible: bool = True

    hard_constraint_violations: tuple[str, ...] = field(
        default_factory=tuple
    )

    soft_penalties: dict[str, Decimal] = field(
        default_factory=dict
    )

    explanation_factors: dict[str, Any] = field(
        default_factory=dict
    )

    rejected_alternatives: tuple[dict[str, Any], ...] = field(
        default_factory=tuple
    )

    approval_required: bool = False

    emergency_liquidity_mode: bool = False

    def __post_init__(self) -> None:
        """Validate the complete plan."""

        if not self.plan_id:
            raise ValueError("plan_id cannot be empty.")

        if self.retained_cash < Decimal("0"):
            raise ValueError(
                "retained_cash cannot be negative."
            )

        for name, value in self.soft_penalties.items():
            if value < Decimal("0"):
                raise ValueError(
                    f"Soft penalty '{name}' cannot be negative."
                )

        if self.hard_constraint_violations and self.feasible:
            raise ValueError(
                "A plan with hard constraint violations "
                "cannot be marked feasible."
            )

    @property
    def total_payment_amount(self) -> Decimal:
        """Return the total amount of payments in the plan."""

        return sum(
            (
                decision.amount
                for decision in self.payment_decisions
            ),
            Decimal("0"),
        )

    @property
    def total_financing_draw(self) -> Decimal:
        """Return the total financing drawn by the plan."""

        return sum(
            (
                decision.amount
                for decision in self.financing_decisions
            ),
            Decimal("0"),
        )

    @property
    def total_discount_savings(self) -> Decimal:
        """Return total discount savings captured."""

        return sum(
            (
                decision.discount_value
                for decision in self.payment_decisions
            ),
            Decimal("0"),
        )

    @property
    def total_financing_cost(self) -> Decimal:
        """Return total financing cost."""

        return sum(
            (
                decision.total_financing_cost
                for decision in self.financing_decisions
            ),
            Decimal("0"),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-compatible representation of the plan.

        Monetary Decimal values are converted to strings to preserve
        financial precision.
        """

        return {
            "plan_id": self.plan_id,
            "feasible": self.feasible,
            "emergency_liquidity_mode": (
                self.emergency_liquidity_mode
            ),
            "approval_required": self.approval_required,
            "retained_cash": str(self.retained_cash),
            "total_payment_amount": str(
                self.total_payment_amount
            ),
            "total_financing_draw": str(
                self.total_financing_draw
            ),
            "total_discount_savings": str(
                self.total_discount_savings
            ),
            "total_financing_cost": str(
                self.total_financing_cost
            ),
            "metrics": {
                "total_cost": str(self.metrics.total_cost),
                "financing_cost": str(
                    self.metrics.financing_cost
                ),
                "late_payment_penalty": str(
                    self.metrics.late_payment_penalty
                ),
                "discount_savings": str(
                    self.metrics.discount_savings
                ),
                "minimum_projected_cash": str(
                    self.metrics.minimum_projected_cash
                ),
                "liquidity_reserve": str(
                    self.metrics.liquidity_reserve
                ),
                "shortfall_probability": str(
                    self.metrics.shortfall_probability
                ),
                "supplier_risk_score": str(
                    self.metrics.supplier_risk_score
                ),
                "liquidity_survival_horizon_days": (
                    self.metrics.liquidity_survival_horizon_days
                ),
                "reserve_violations": (
                    self.metrics.reserve_violations
                ),
            },
            "hard_constraint_violations": list(
                self.hard_constraint_violations
            ),
            "explanation_factors": self.explanation_factors,
        }