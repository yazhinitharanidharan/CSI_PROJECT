"""
Invoice priority engine for the LiquidityOS Decision Engine.

This module:
- Calculates invoice urgency.
- Calculates deterministic invoice priority scores.
- Ranks invoices.
- Builds a heap-based priority queue.
- Re-ranks invoices when financial conditions change.

IMPORTANT:
    The priority engine only determines the order in which invoices
    should be considered.

    It does NOT make the final payment or financing decision.

    Final decisions will later be made after applying:
    - hard constraints
    - Liquidity Firewall
    - mandatory obligations
    - candidate-plan evaluation
    - optimization
"""

from dataclasses import dataclass
from decimal import Decimal
import heapq
from typing import Optional


@dataclass(frozen=True)
class InvoicePriorityInput:
    """
    Input data required to calculate an invoice priority.

    Financial values must be supplied as Decimal values.

    Supplier-risk values can be supplied by the Supplier Risk Adapter.
    """

    invoice_id: str

    # Financial factors
    discount_value: Decimal = Decimal("0")
    financing_cost: Decimal = Decimal("0")
    penalty_risk: Decimal = Decimal("0")

    # Supplier factors
    supplier_criticality: Decimal = Decimal("0")
    supplier_liquidity_need: Decimal = Decimal("0")

    # Invoice timing
    urgency: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        """Validate invoice priority input values."""

        if not self.invoice_id:
            raise ValueError(
                "invoice_id cannot be empty."
            )

        non_negative_fields = (
            "discount_value",
            "financing_cost",
            "penalty_risk",
            "supplier_criticality",
            "supplier_liquidity_need",
            "urgency",
        )

        for field_name in non_negative_fields:
            value = getattr(self, field_name)

            if value < Decimal("0"):
                raise ValueError(
                    f"{field_name} cannot be negative."
                )

        if self.penalty_risk > Decimal("1"):
            raise ValueError(
                "penalty_risk must be between 0 and 1."
            )

        if self.supplier_criticality > Decimal("100"):
            raise ValueError(
                "supplier_criticality must be between 0 and 100."
            )

        if self.supplier_liquidity_need > Decimal("100"):
            raise ValueError(
                "supplier_liquidity_need must be between 0 and 100."
            )

        if self.urgency > Decimal("100"):
            raise ValueError(
                "urgency must be between 0 and 100."
            )


@dataclass(frozen=True)
class PriorityWeights:
    """
    Configurable weights used by the deterministic priority formula.

    The weights allow the team to tune the importance of each factor
    without changing the calculation logic.
    """

    discount: Decimal = Decimal("1")
    financing_cost: Decimal = Decimal("1")
    penalty_risk: Decimal = Decimal("1")
    supplier_criticality: Decimal = Decimal("1")
    supplier_liquidity_need: Decimal = Decimal("1")
    urgency: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        """Validate priority weights."""

        fields = (
            "discount",
            "financing_cost",
            "penalty_risk",
            "supplier_criticality",
            "supplier_liquidity_need",
            "urgency",
        )

        for field_name in fields:
            value = getattr(self, field_name)

            if value < Decimal("0"):
                raise ValueError(
                    f"{field_name} weight cannot be negative."
                )


@dataclass(frozen=True)
class InvoicePriority:
    """
    Calculated priority information for one invoice.
    """

    invoice_id: str
    urgency: Decimal
    priority_score: Decimal
    factors: dict[str, Decimal]


def calculate_urgency(
    days_until_due: int,
    permissible_delay_days: int = 0,
) -> Decimal:
    """
    Calculate a normalized urgency score between 0 and 100.

    The closer an invoice is to its due date, the higher its urgency.

    An overdue invoice receives maximum urgency.

    Args:
        days_until_due:
            Number of days until the invoice due date.
            Negative values indicate that the invoice is overdue.

        permissible_delay_days:
            Number of additional days the invoice can be delayed.

    Returns:
        Urgency score between 0 and 100.
    """

    if permissible_delay_days < 0:
        raise ValueError(
            "permissible_delay_days cannot be negative."
        )

    # Already due or overdue.
    if days_until_due <= 0:
        return Decimal("100.0000")

    # No contractual delay period.
    #
    # Urgency increases as the invoice approaches maturity.
    if permissible_delay_days == 0:

        if days_until_due >= 30:
            return Decimal("10.0000")

        urgency = (
            Decimal("100")
            - (
                Decimal(days_until_due)
                / Decimal("30")
                * Decimal("90")
            )
        )

        return max(
            Decimal("10.0000"),
            urgency.quantize(Decimal("0.0001")),
        )

    # When permissible delay exists, urgency considers the complete
    # window from today until the end of the permissible delay period.
    total_window = (
        days_until_due
        + permissible_delay_days
    )

    urgency = (
        Decimal("100")
        * (
            Decimal("1")
            - (
                Decimal(days_until_due)
                / Decimal(total_window)
            )
        )
    )

    return max(
        Decimal("0"),
        min(
            urgency,
            Decimal("100"),
        ),
    ).quantize(Decimal("0.0001"))


def calculate_priority_score(
    discount_value: Decimal,
    financing_cost: Decimal,
    penalty_risk: Decimal,
    supplier_criticality: Decimal,
    supplier_liquidity_need: Decimal,
    urgency: Decimal,
    weights: Optional[PriorityWeights] = None,
) -> Decimal:
    """
    Calculate the deterministic invoice priority score.

    Formula:

        PriorityScore =
            wd × DiscountValue
            - wf × FinancingCost
            - wp × PenaltyRisk
            + ws × SupplierCriticality
            + wl × SupplierLiquidityNeed
            + wu × Urgency

    Higher scores mean the invoice should be considered earlier.

    Args:
        discount_value:
            Monetary value of an available early-payment discount.

        financing_cost:
            Expected financing cost.

        penalty_risk:
            Normalized penalty risk between 0 and 1.

        supplier_criticality:
            Supplier criticality score between 0 and 100.

        supplier_liquidity_need:
            Supplier liquidity-need score between 0 and 100.

            In the current MVP integration, this value may be derived
            from the Supplier Intelligence Agent's distress_score by
            the Supplier Risk Adapter.

        urgency:
            Invoice urgency score between 0 and 100.

        weights:
            Optional configurable priority weights.

    Returns:
        Deterministic priority score.
    """

    if weights is None:
        weights = PriorityWeights()

    if discount_value < Decimal("0"):
        raise ValueError(
            "discount_value cannot be negative."
        )

    if financing_cost < Decimal("0"):
        raise ValueError(
            "financing_cost cannot be negative."
        )

    if not Decimal("0") <= penalty_risk <= Decimal("1"):
        raise ValueError(
            "penalty_risk must be between 0 and 1."
        )

    if not Decimal("0") <= supplier_criticality <= Decimal("100"):
        raise ValueError(
            "supplier_criticality must be between 0 and 100."
        )

    if not Decimal("0") <= supplier_liquidity_need <= Decimal("100"):
        raise ValueError(
            "supplier_liquidity_need must be between 0 and 100."
        )

    if not Decimal("0") <= urgency <= Decimal("100"):
        raise ValueError(
            "urgency must be between 0 and 100."
        )

    score = (
        weights.discount * discount_value
        - weights.financing_cost * financing_cost
        - weights.penalty_risk * penalty_risk
        + weights.supplier_criticality * supplier_criticality
        + weights.supplier_liquidity_need * supplier_liquidity_need
        + weights.urgency * urgency
    )

    return score.quantize(
        Decimal("0.0001")
    )


def rank_invoices(
    invoices: list[InvoicePriorityInput],
    weights: Optional[PriorityWeights] = None,
) -> list[InvoicePriority]:
    """
    Calculate and rank invoices by priority score.

    Higher-priority invoices appear first.

    Args:
        invoices:
            List of invoice priority inputs.

        weights:
            Optional priority weights.

    Returns:
        List of InvoicePriority objects sorted from highest
        priority to lowest priority.
    """

    priorities: list[InvoicePriority] = []

    for invoice in invoices:

        score = calculate_priority_score(
            discount_value=invoice.discount_value,
            financing_cost=invoice.financing_cost,
            penalty_risk=invoice.penalty_risk,
            supplier_criticality=invoice.supplier_criticality,
            supplier_liquidity_need=invoice.supplier_liquidity_need,
            urgency=invoice.urgency,
            weights=weights,
        )

        priorities.append(
            InvoicePriority(
                invoice_id=invoice.invoice_id,
                urgency=invoice.urgency,
                priority_score=score,
                factors={
                    "discount_value": invoice.discount_value,
                    "financing_cost": invoice.financing_cost,
                    "penalty_risk": invoice.penalty_risk,
                    "supplier_criticality": (
                        invoice.supplier_criticality
                    ),
                    "supplier_liquidity_need": (
                        invoice.supplier_liquidity_need
                    ),
                    "urgency": invoice.urgency,
                },
            )
        )

    # Sort from highest score to lowest score.
    #
    # invoice_id provides deterministic ordering when two invoices
    # have exactly the same score.
    priorities.sort(
        key=lambda item: (
            -item.priority_score,
            -item.urgency,
            item.invoice_id,
        )
    )

    return priorities


def build_priority_queue(
    invoices: list[InvoicePriorityInput],
    weights: Optional[PriorityWeights] = None,
) -> list[tuple[Decimal, str, InvoicePriority]]:
    """
    Build a heap-based priority queue.

    Python's heapq is a min-heap. Therefore, the priority score is
    stored as a negative value so that the invoice with the highest
    actual score is removed first.

    Tuple structure:

        (-priority_score, invoice_id, InvoicePriority)

    The invoice ID acts as a deterministic tie-breaker.

    Args:
        invoices:
            List of invoice priority inputs.

        weights:
            Optional priority weights.

    Returns:
        Heap containing invoice priorities.
    """

    priorities = rank_invoices(
        invoices=invoices,
        weights=weights,
    )

    priority_queue: list[
        tuple[Decimal, str, InvoicePriority]
    ] = []

    for priority in priorities:

        heapq.heappush(
            priority_queue,
            (
                -priority.priority_score,
                priority.invoice_id,
                priority,
            ),
        )

    return priority_queue


def pop_highest_priority(
    priority_queue: list[
        tuple[Decimal, str, InvoicePriority]
    ],
) -> Optional[InvoicePriority]:
    """
    Remove and return the highest-priority invoice.

    This operation uses heapq.heappop(), giving O(log n)
    heap-removal complexity.

    Args:
        priority_queue:
            Heap created by build_priority_queue().

    Returns:
        Highest-priority invoice, or None if the heap is empty.
    """

    if not priority_queue:
        return None

    _, _, priority = heapq.heappop(
        priority_queue
    )

    return priority


def re_rank_invoices(
    invoices: list[InvoicePriorityInput],
    weights: Optional[PriorityWeights] = None,
) -> list[tuple[Decimal, str, InvoicePriority]]:
    """
    Recalculate invoice priorities and rebuild the priority queue.

    Re-ranking can be triggered when financial conditions change,
    for example:

        - receivable delays
        - supplier-risk changes
        - discount changes
        - financing-cost changes
        - invoice urgency changes

    Args:
        invoices:
            Updated invoice priority inputs.

        weights:
            Optional priority weights.

    Returns:
        Newly constructed heap containing updated invoice priorities.
    """

    return build_priority_queue(
        invoices=invoices,
        weights=weights,
    )