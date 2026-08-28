"""
Discount calculation engine for the LiquidityOS Decision Engine.

This module calculates:
- Early-payment discount value
- Discount period
- Annualized discount return
- Discount eligibility
- Evaluation of an early-payment action

This module does NOT make the final payment decision.
The deterministic optimizer and Liquidity Firewall will later decide
whether capturing the discount is actually feasible and preferable.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional


@dataclass(frozen=True)
class DiscountEvaluation:
    """
    Result of evaluating an invoice's early-payment discount.

    This object contains only discount-related calculations.
    """

    eligible: bool
    discount_value: Decimal
    discount_days: int
    annualized_return: Decimal
    reason: str


def _validate_money(
    value: Decimal,
    field_name: str,
) -> None:
    """
    Validate that a monetary value is non-negative.
    """

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} cannot be negative."
        )


def _validate_discount_rate(
    discount_rate: Decimal,
) -> None:
    """
    Validate that the discount rate is between 0 and 1.

    Example:
        2% = Decimal("0.02")
    """

    if discount_rate < Decimal("0"):
        raise ValueError(
            "discount_rate cannot be negative."
        )

    if discount_rate >= Decimal("1"):
        raise ValueError(
            "discount_rate must be less than 1."
        )


def calculate_discount_value(
    invoice_amount: Decimal,
    discount_rate: Decimal,
) -> Decimal:
    """
    Calculate the monetary value of an early-payment discount.

    Formula:
        discount_value = invoice_amount × discount_rate

    Example:
        ₹200,000 × 0.02 = ₹4,000

    Args:
        invoice_amount:
            Total invoice amount.

        discount_rate:
            Discount expressed as a decimal.
            Example: 2% = Decimal("0.02").

    Returns:
        Discount value as a Decimal.
    """

    _validate_money(invoice_amount, "invoice_amount")
    _validate_discount_rate(discount_rate)

    return (
        invoice_amount * discount_rate
    ).quantize(Decimal("0.01"))


def calculate_discount_days(
    early_payment_date: date,
    maturity_date: date,
) -> int:
    """
    Calculate the number of days between early payment and maturity.

    Args:
        early_payment_date:
            Date on which the invoice is paid early.

        maturity_date:
            Invoice due/maturity date.

    Returns:
        Number of days between the two dates.

    Raises:
        ValueError:
            If early payment is not before maturity.
    """

    if early_payment_date >= maturity_date:
        raise ValueError(
            "early_payment_date must be before maturity_date."
        )

    return (
        maturity_date - early_payment_date
    ).days


def calculate_annualized_discount_return(
    discount_rate: Decimal,
    discount_days: int,
) -> Decimal:
    """
    Calculate the annualized return from taking an early-payment discount.

    Formula from the project specification:

        annualized_return =
            (discount_rate / (1 - discount_rate))
            × (365 / discount_days)

    The returned value is expressed as a decimal.

    Example:
        A 2% discount taken 9 days before maturity produces
        an annualized return of approximately 82.71%.

    Args:
        discount_rate:
            Discount expressed as a decimal.
            Example: 2% = Decimal("0.02").

        discount_days:
            Number of days payment is accelerated.

    Returns:
        Annualized discount return as a Decimal.

    Raises:
        ValueError:
            If discount_days is zero or negative.
    """

    _validate_discount_rate(discount_rate)

    if discount_days <= 0:
        raise ValueError(
            "discount_days must be greater than zero."
        )

    annualized_return = (
        discount_rate
        / (Decimal("1") - discount_rate)
    ) * (
        Decimal("365") / Decimal(discount_days)
    )

    return annualized_return.quantize(
        Decimal("0.0001")
    )


def is_discount_eligible(
    invoice_amount: Decimal,
    discount_rate: Decimal,
    discount_deadline: Optional[date],
    payment_date: date,
    maturity_date: date,
) -> bool:
    """
    Determine whether an invoice qualifies for an early-payment discount.

    An invoice is discount-eligible when:

    1. The invoice amount is positive.
    2. The discount rate is positive.
    3. A discount deadline exists.
    4. The payment date is on or before the discount deadline.
    5. The payment date is before maturity.
    6. The discount deadline is before maturity.

    Args:
        invoice_amount:
            Invoice amount.

        discount_rate:
            Early-payment discount rate.

        discount_deadline:
            Last date on which the discount can be obtained.

        payment_date:
            Proposed payment date.

        maturity_date:
            Invoice due date.

    Returns:
        True if the discount can be obtained, otherwise False.
    """

    _validate_money(invoice_amount, "invoice_amount")
    _validate_discount_rate(discount_rate)

    if invoice_amount <= Decimal("0"):
        return False

    if discount_rate <= Decimal("0"):
        return False

    if discount_deadline is None:
        return False

    if discount_deadline >= maturity_date:
        return False

    if payment_date > discount_deadline:
        return False

    if payment_date >= maturity_date:
        return False

    return True


def evaluate_discount_action(
    invoice_amount: Decimal,
    discount_rate: Decimal,
    discount_deadline: Optional[date],
    payment_date: date,
    maturity_date: date,
) -> DiscountEvaluation:
    """
    Evaluate the discount opportunity for a proposed payment date.

    This function combines the individual discount calculations into
    one structured result.

    It does NOT determine whether the company should make the payment.
    It only determines the financial attractiveness of the discount
    itself.

    Args:
        invoice_amount:
            Invoice amount.

        discount_rate:
            Discount expressed as a decimal.

        discount_deadline:
            Last date for obtaining the discount.

        payment_date:
            Proposed payment date.

        maturity_date:
            Invoice due date.

    Returns:
        DiscountEvaluation containing eligibility, savings,
        discount period and annualized return.
    """

    _validate_money(invoice_amount, "invoice_amount")
    _validate_discount_rate(discount_rate)

    eligible = is_discount_eligible(
        invoice_amount=invoice_amount,
        discount_rate=discount_rate,
        discount_deadline=discount_deadline,
        payment_date=payment_date,
        maturity_date=maturity_date,
    )

    if not eligible:
        return DiscountEvaluation(
            eligible=False,
            discount_value=Decimal("0.00"),
            discount_days=0,
            annualized_return=Decimal("0.0000"),
            reason=(
                "Invoice is not eligible for the "
                "early-payment discount on the proposed date."
            ),
        )

    discount_days = calculate_discount_days(
        early_payment_date=payment_date,
        maturity_date=maturity_date,
    )

    discount_value = calculate_discount_value(
        invoice_amount=invoice_amount,
        discount_rate=discount_rate,
    )

    annualized_return = calculate_annualized_discount_return(
        discount_rate=discount_rate,
        discount_days=discount_days,
    )

    return DiscountEvaluation(
        eligible=True,
        discount_value=discount_value,
        discount_days=discount_days,
        annualized_return=annualized_return,
        reason=(
            "Invoice is eligible for the early-payment discount."
        ),
    )