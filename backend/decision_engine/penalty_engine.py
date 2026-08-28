"""
Late-payment penalty engine for the LiquidityOS Decision Engine.

This module calculates:
- Number of late days
- Late-payment penalty
- Penalty risk

This module does NOT decide whether an invoice should be delayed.
It only calculates the financial and risk consequences of delay.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PenaltyEvaluation:
    """
    Result of evaluating the late-payment consequences of an invoice.
    """

    late_days: int
    penalty_amount: Decimal
    penalty_risk: Decimal
    past_absolute_deadline: bool
    reason: str


def calculate_late_days(
    due_date: date,
    payment_date: date,
) -> int:
    """
    Calculate the number of days a payment is late.

    If payment occurs on or before the due date, the result is zero.

    Formula:
        late_days = max(payment_date - due_date, 0)

    Args:
        due_date:
            Contractual invoice due date.

        payment_date:
            Actual or proposed payment date.

    Returns:
        Number of late days.
    """

    if payment_date <= due_date:
        return 0

    return (payment_date - due_date).days


def calculate_late_penalty(
    invoice_amount: Decimal,
    penalty_rate: Decimal,
    late_days: int,
) -> Decimal:
    """
    Calculate the monetary late-payment penalty.

    The penalty is calculated using a simple daily-rate model:

        penalty = invoice_amount × penalty_rate × late_days

    Args:
        invoice_amount:
            Total invoice amount.

        penalty_rate:
            Daily penalty rate expressed as a decimal.
            Example:
                0.1% per day = Decimal("0.001")

        late_days:
            Number of days payment is late.

    Returns:
        Late-payment penalty as a Decimal.

    Raises:
        ValueError:
            If monetary values or late_days are invalid.
    """

    if invoice_amount < Decimal("0"):
        raise ValueError(
            "invoice_amount cannot be negative."
        )

    if penalty_rate < Decimal("0"):
        raise ValueError(
            "penalty_rate cannot be negative."
        )

    if late_days < 0:
        raise ValueError(
            "late_days cannot be negative."
        )

    penalty = (
        invoice_amount
        * penalty_rate
        * Decimal(late_days)
    )

    return penalty.quantize(Decimal("0.01"))


def calculate_penalty_risk(
    late_days: int,
    permissible_delay_days: int,
    penalty_amount: Decimal,
    invoice_amount: Decimal,
) -> Decimal:
    """
    Calculate a normalized penalty-risk score between 0 and 1.

    The score combines:
    - How far the payment has been delayed relative to
      the permissible delay period.
    - The penalty amount relative to the invoice amount.

    Risk interpretation:

        0.00 → no meaningful penalty risk
        1.00 → very high penalty risk

    Args:
        late_days:
            Number of days payment is late.

        permissible_delay_days:
            Maximum delay permitted by the invoice/contract.

        penalty_amount:
            Calculated monetary penalty.

        invoice_amount:
            Original invoice amount.

    Returns:
        Penalty-risk score between Decimal("0") and Decimal("1").
    """

    if late_days < 0:
        raise ValueError(
            "late_days cannot be negative."
        )

    if permissible_delay_days < 0:
        raise ValueError(
            "permissible_delay_days cannot be negative."
        )

    if penalty_amount < Decimal("0"):
        raise ValueError(
            "penalty_amount cannot be negative."
        )

    if invoice_amount <= Decimal("0"):
        raise ValueError(
            "invoice_amount must be greater than zero."
        )

    if late_days == 0:
        return Decimal("0.0000")

    # Delay risk.
    #
    # If no delay is contractually permitted, any late payment
    # creates maximum delay risk.
    if permissible_delay_days == 0:
        delay_risk = Decimal("1")
    else:
        delay_risk = (
            Decimal(late_days)
            / Decimal(permissible_delay_days)
        )

        delay_risk = min(
            delay_risk,
            Decimal("1"),
        )

    # Financial penalty risk.
    penalty_ratio = (
        penalty_amount / invoice_amount
    )

    penalty_ratio = min(
        penalty_ratio,
        Decimal("1"),
    )

    # Combine timing risk and financial penalty exposure.
    risk = (
        (delay_risk * Decimal("0.6"))
        + (penalty_ratio * Decimal("0.4"))
    )

    return min(
        risk,
        Decimal("1"),
    ).quantize(Decimal("0.0001"))


def evaluate_penalty_action(
    invoice_amount: Decimal,
    due_date: date,
    payment_date: date,
    penalty_rate: Decimal,
    permissible_delay_days: int,
) -> PenaltyEvaluation:
    """
    Evaluate the penalty consequences of a proposed payment date.

    This function combines late-day calculation, penalty calculation,
    and penalty-risk calculation.

    Args:
        invoice_amount:
            Total invoice amount.

        due_date:
            Invoice due date.

        payment_date:
            Proposed payment date.

        penalty_rate:
            Daily penalty rate expressed as a decimal.

        permissible_delay_days:
            Maximum contractually permissible delay.

    Returns:
        PenaltyEvaluation containing the calculated penalty,
        risk and deadline status.
    """

    late_days = calculate_late_days(
        due_date=due_date,
        payment_date=payment_date,
    )

    penalty_amount = calculate_late_penalty(
        invoice_amount=invoice_amount,
        penalty_rate=penalty_rate,
        late_days=late_days,
    )

    penalty_risk = calculate_penalty_risk(
        late_days=late_days,
        permissible_delay_days=permissible_delay_days,
        penalty_amount=penalty_amount,
        invoice_amount=invoice_amount,
    )

    past_absolute_deadline = (
        late_days > permissible_delay_days
    )

    if late_days == 0:
        reason = "Payment is on time; no late-payment penalty applies."

    elif past_absolute_deadline:
        reason = (
            "Payment exceeds the permissible delay period "
            "and has passed the absolute deadline."
        )

    else:
        reason = (
            "Payment is late but remains within the "
            "permissible delay period."
        )

    return PenaltyEvaluation(
        late_days=late_days,
        penalty_amount=penalty_amount,
        penalty_risk=penalty_risk,
        past_absolute_deadline=past_absolute_deadline,
        reason=reason,
    )