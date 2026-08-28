"""
Financing engine for the LiquidityOS Decision Engine.

This module:
- Calculates financing interest.
- Calculates total financing cost.
- Checks financing eligibility.
- Compares financing options.
- Selects the best eligible financing option.
- Calculates the value of preserving internal liquidity.
- Determines whether external financing is preferable to using cash.

IMPORTANT:
    This module does not override the Liquidity Firewall,
    hard constraints, or the final optimizer.

    It only provides deterministic financing calculations
    and recommendations that the later decision engine can use.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from .models import FundingSource


class FinancingEligibility(str, Enum):
    """Possible financing eligibility states."""

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"


@dataclass(frozen=True)
class FinancingOption:
    """
    Represents one available financing option.

    Example:
        Bank loan, supplier financing facility, etc.
    """

    option_id: str
    funding_source: FundingSource

    annual_interest_rate: Decimal
    fixed_fee: Decimal

    available_limit: Decimal

    maturity_date: Optional[date] = None

    eligible: bool = True
    approval_required: bool = False

    def __post_init__(self) -> None:
        """Validate financing option data."""

        if not self.option_id:
            raise ValueError(
                "option_id cannot be empty."
            )

        if self.annual_interest_rate < Decimal("0"):
            raise ValueError(
                "annual_interest_rate cannot be negative."
            )

        if self.annual_interest_rate >= Decimal("1"):
            raise ValueError(
                "annual_interest_rate must be less than 1."
            )

        if self.fixed_fee < Decimal("0"):
            raise ValueError(
                "fixed_fee cannot be negative."
            )

        if self.available_limit < Decimal("0"):
            raise ValueError(
                "available_limit cannot be negative."
            )


@dataclass(frozen=True)
class FinancingEvaluation:
    """
    Result of evaluating a financing option.
    """

    option_id: str
    funding_source: FundingSource

    eligible: bool

    financing_amount: Decimal
    interest_cost: Decimal
    fixed_fee: Decimal
    total_cost: Decimal

    liquidity_preserved: Decimal

    effective_cost_rate: Decimal

    reason: str


def _validate_positive_amount(
    amount: Decimal,
    field_name: str,
) -> None:
    """Validate that an amount is greater than zero."""

    if amount <= Decimal("0"):
        raise ValueError(
            f"{field_name} must be greater than zero."
        )


def _validate_non_negative(
    value: Decimal,
    field_name: str,
) -> None:
    """Validate that a Decimal value is not negative."""

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} cannot be negative."
        )


def calculate_financing_interest(
    principal: Decimal,
    annual_interest_rate: Decimal,
    financing_days: int,
) -> Decimal:
    """
    Calculate simple financing interest.

    Formula:

        interest =
            principal
            × annual_interest_rate
            × financing_days / 365

    Example:

        ₹2,00,000
        × 9%
        × 30 / 365

    Args:
        principal:
            Amount being financed.

        annual_interest_rate:
            Annual interest rate expressed as a decimal.
            Example: 9% = Decimal("0.09").

        financing_days:
            Number of days for which financing is used.

    Returns:
        Financing interest as a Decimal.
    """

    _validate_positive_amount(
        principal,
        "principal",
    )

    _validate_non_negative(
        annual_interest_rate,
        "annual_interest_rate",
    )

    if annual_interest_rate >= Decimal("1"):
        raise ValueError(
            "annual_interest_rate must be less than 1."
        )

    if financing_days < 0:
        raise ValueError(
            "financing_days cannot be negative."
        )

    interest = (
        principal
        * annual_interest_rate
        * Decimal(financing_days)
        / Decimal("365")
    )

    return interest.quantize(
        Decimal("0.01")
    )


def calculate_financing_cost(
    principal: Decimal,
    annual_interest_rate: Decimal,
    financing_days: int,
    fixed_fee: Decimal = Decimal("0"),
) -> Decimal:
    """
    Calculate total financing cost.

    Formula:

        total financing cost =
            interest + fixed fee

    Args:
        principal:
            Amount being financed.

        annual_interest_rate:
            Annual financing rate as a decimal.

        financing_days:
            Number of financing days.

        fixed_fee:
            Fixed financing fee.

    Returns:
        Total financing cost as a Decimal.
    """

    _validate_non_negative(
        fixed_fee,
        "fixed_fee",
    )

    interest = calculate_financing_interest(
        principal=principal,
        annual_interest_rate=annual_interest_rate,
        financing_days=financing_days,
    )

    return (
        interest + fixed_fee
    ).quantize(Decimal("0.01"))


def is_financing_eligible(
    financing_amount: Decimal,
    option: FinancingOption,
    requested_date: Optional[date] = None,
) -> bool:
    """
    Determine whether a financing option can be used.

    An option is eligible when:

    1. The requested financing amount is positive.
    2. The option itself is marked eligible.
    3. The requested amount does not exceed available limit.
    4. If a maturity date exists, the requested date does not
       occur after the financing maturity date.

    Args:
        financing_amount:
            Amount requested from the financing facility.

        option:
            Financing option being evaluated.

        requested_date:
            Date on which financing is requested.

    Returns:
        True if the option is eligible, otherwise False.
    """

    _validate_positive_amount(
        financing_amount,
        "financing_amount",
    )

    if not option.eligible:
        return False

    if financing_amount > option.available_limit:
        return False

    if (
        requested_date is not None
        and option.maturity_date is not None
        and requested_date > option.maturity_date
    ):
        return False

    return True


def calculate_liquidity_value_preserved(
    financing_amount: Decimal,
    liquidity_value_rate: Decimal,
    financing_days: int,
) -> Decimal:
    """
    Estimate the financial value of preserving internal liquidity.

    Formula:

        liquidity value preserved =
            financing_amount
            × liquidity_value_rate
            × financing_days / 365

    The liquidity value rate represents the estimated annual
    economic value of keeping internal cash available.

    Args:
        financing_amount:
            Amount funded externally rather than using internal cash.

        liquidity_value_rate:
            Annual value of preserving liquidity, expressed as
            a decimal.

        financing_days:
            Number of days internal cash remains available.

    Returns:
        Estimated liquidity value preserved.
    """

    _validate_positive_amount(
        financing_amount,
        "financing_amount",
    )

    _validate_non_negative(
        liquidity_value_rate,
        "liquidity_value_rate",
    )

    if liquidity_value_rate >= Decimal("1"):
        raise ValueError(
            "liquidity_value_rate must be less than 1."
        )

    if financing_days < 0:
        raise ValueError(
            "financing_days cannot be negative."
        )

    value_preserved = (
        financing_amount
        * liquidity_value_rate
        * Decimal(financing_days)
        / Decimal("365")
    )

    return value_preserved.quantize(
        Decimal("0.01")
    )


def _calculate_effective_cost_rate(
    total_cost: Decimal,
    financing_amount: Decimal,
    financing_days: int,
) -> Decimal:
    """
    Calculate the effective annualized financing cost rate.

    This is used for comparing financing options with different
    costs and durations.

    Returns:
        Annualized effective cost rate as a decimal.
    """

    if financing_amount <= Decimal("0"):
        raise ValueError(
            "financing_amount must be greater than zero."
        )

    if financing_days <= 0:
        return (
            total_cost / financing_amount
        ).quantize(Decimal("0.0001"))

    effective_rate = (
        total_cost
        / financing_amount
        * Decimal("365")
        / Decimal(financing_days)
    )

    return effective_rate.quantize(
        Decimal("0.0001")
    )


def compare_financing_options(
    financing_amount: Decimal,
    financing_days: int,
    options: list[FinancingOption],
    liquidity_value_rate: Decimal = Decimal("0"),
    requested_date: Optional[date] = None,
) -> list[FinancingEvaluation]:
    """
    Evaluate and compare multiple financing options.

    Options that are not eligible are retained in the returned
    list with eligible=False so that the caller can explain
    why they were rejected.

    Args:
        financing_amount:
            Amount that needs to be financed.

        financing_days:
            Expected financing duration.

        options:
            Available financing options.

        liquidity_value_rate:
            Annual economic value of preserving internal cash.

        requested_date:
            Date on which financing is requested.

    Returns:
        Financing evaluations sorted by effective net cost,
        with eligible options ranked before ineligible options.
    """

    _validate_positive_amount(
        financing_amount,
        "financing_amount",
    )

    if financing_days < 0:
        raise ValueError(
            "financing_days cannot be negative."
        )

    evaluations: list[FinancingEvaluation] = []

    for option in options:
        eligible = is_financing_eligible(
            financing_amount=financing_amount,
            option=option,
            requested_date=requested_date,
        )

        if not eligible:
            evaluations.append(
                FinancingEvaluation(
                    option_id=option.option_id,
                    funding_source=option.funding_source,
                    eligible=False,
                    financing_amount=financing_amount,
                    interest_cost=Decimal("0.00"),
                    fixed_fee=option.fixed_fee,
                    total_cost=Decimal("0.00"),
                    liquidity_preserved=Decimal("0.00"),
                    effective_cost_rate=Decimal("0.0000"),
                    reason=(
                        "Financing option is not eligible "
                        "for the requested amount or date."
                    ),
                )
            )

            continue

        interest_cost = calculate_financing_interest(
            principal=financing_amount,
            annual_interest_rate=option.annual_interest_rate,
            financing_days=financing_days,
        )

        total_cost = calculate_financing_cost(
            principal=financing_amount,
            annual_interest_rate=option.annual_interest_rate,
            financing_days=financing_days,
            fixed_fee=option.fixed_fee,
        )

        liquidity_preserved = (
            calculate_liquidity_value_preserved(
                financing_amount=financing_amount,
                liquidity_value_rate=liquidity_value_rate,
                financing_days=financing_days,
            )
        )

        net_economic_cost = (
            total_cost - liquidity_preserved
        )

        effective_cost_rate = (
            _calculate_effective_cost_rate(
                total_cost=net_economic_cost,
                financing_amount=financing_amount,
                financing_days=financing_days,
            )
        )

        evaluations.append(
            FinancingEvaluation(
                option_id=option.option_id,
                funding_source=option.funding_source,
                eligible=True,
                financing_amount=financing_amount,
                interest_cost=interest_cost,
                fixed_fee=option.fixed_fee,
                total_cost=total_cost,
                liquidity_preserved=liquidity_preserved,
                effective_cost_rate=effective_cost_rate,
                reason=(
                    "Financing option is eligible and "
                    "has been evaluated for total cost "
                    "and liquidity preservation."
                ),
            )
        )

    evaluations.sort(
        key=lambda evaluation: (
            not evaluation.eligible,
            evaluation.effective_cost_rate,
            evaluation.total_cost,
        )
    )

    return evaluations


def select_best_financing_option(
    financing_amount: Decimal,
    financing_days: int,
    options: list[FinancingOption],
    liquidity_value_rate: Decimal = Decimal("0"),
    requested_date: Optional[date] = None,
) -> Optional[FinancingEvaluation]:
    """
    Select the best eligible financing option.

    The selection is deterministic.

    The option with the lowest effective economic cost is
    selected after considering the estimated value of
    preserving liquidity.

    Args:
        financing_amount:
            Amount that needs to be financed.

        financing_days:
            Expected financing duration.

        options:
            Available financing options.

        liquidity_value_rate:
            Annual economic value of preserving internal cash.

        requested_date:
            Financing request date.

    Returns:
        Best eligible FinancingEvaluation, or None if no
        financing option is eligible.
    """

    evaluations = compare_financing_options(
        financing_amount=financing_amount,
        financing_days=financing_days,
        options=options,
        liquidity_value_rate=liquidity_value_rate,
        requested_date=requested_date,
    )

    eligible_options = [
        evaluation
        for evaluation in evaluations
        if evaluation.eligible
    ]

    if not eligible_options:
        return None

    return min(
        eligible_options,
        key=lambda evaluation: (
            evaluation.effective_cost_rate,
            evaluation.total_cost,
            evaluation.option_id,
        ),
    )


def should_use_financing(
    financing_amount: Decimal,
    financing_cost: Decimal,
    liquidity_value_preserved: Decimal,
    available_cash_above_reserve: Decimal,
) -> bool:
    """
    Determine whether financing has an economic advantage over
    using internal cash, before final Firewall/optimizer checks.

    Financing is preferred when:

        liquidity value preserved - financing cost > 0

    OR

        internal cash is insufficient above the required reserve.

    This function is an input to the later decision process.
    It does not override hard constraints or the Liquidity Firewall.

    Args:
        financing_amount:
            Amount that needs to be funded.

        financing_cost:
            Total cost of using external financing.

        liquidity_value_preserved:
            Estimated economic value of keeping internal cash available.

        available_cash_above_reserve:
            Cash currently available above the protected reserve.

    Returns:
        True when financing should be considered preferable,
        otherwise False.
    """

    _validate_positive_amount(
        financing_amount,
        "financing_amount",
    )

    _validate_non_negative(
        financing_cost,
        "financing_cost",
    )

    _validate_non_negative(
        liquidity_value_preserved,
        "liquidity_value_preserved",
    )

    _validate_non_negative(
        available_cash_above_reserve,
        "available_cash_above_reserve",
    )

    if available_cash_above_reserve < financing_amount:
        return True

    return (
        liquidity_value_preserved
        > financing_cost
    )