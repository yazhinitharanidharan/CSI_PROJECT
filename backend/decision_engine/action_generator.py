"""
Candidate action generator for the LiquidityOS decision engine.

This module generates possible actions for an invoice.

IMPORTANT:
    This module does NOT choose the best action.
    It only generates candidate actions.

The deterministic optimizer and Liquidity Firewall will later
evaluate which candidate is actually feasible and preferable.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from .models import Action, ActionType, FundingSource


@dataclass(frozen=True)
class InvoiceInput:
    """
    Minimal invoice information required to generate candidate actions.

    This is a temporary input abstraction for the decision engine.
    It can later be replaced by the project's shared Invoice model
    when the backend integration is completed.
    """

    invoice_id: str
    amount: Decimal
    invoice_date: date
    due_date: date

    discount_deadline: Optional[date] = None
    discount_rate: Decimal = Decimal("0")

    verified: bool = True

    permissible_delay_days: int = 0

    bank_financing_available: bool = False
    supplier_financing_available: bool = False

    bank_financing_option_id: Optional[str] = None
    supplier_financing_option_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate the invoice data."""

        if not self.invoice_id:
            raise ValueError("invoice_id cannot be empty.")

        if self.amount <= Decimal("0"):
            raise ValueError(
                "invoice amount must be greater than zero."
            )

        if self.due_date < self.invoice_date:
            raise ValueError(
                "due_date cannot be earlier than invoice_date."
            )

        if self.discount_rate < Decimal("0"):
            raise ValueError(
                "discount_rate cannot be negative."
            )

        if self.discount_rate >= Decimal("1"):
            raise ValueError(
                "discount_rate must be less than 1."
            )

        if self.discount_deadline is not None:
            if self.discount_deadline < self.invoice_date:
                raise ValueError(
                    "discount_deadline cannot be earlier "
                    "than invoice_date."
                )

        if self.permissible_delay_days < 0:
            raise ValueError(
                "permissible_delay_days cannot be negative."
            )


def _create_action(
    invoice: InvoiceInput,
    action_type: ActionType,
    scheduled_date: date,
    amount: Optional[Decimal] = None,
    funding_source: Optional[FundingSource] = None,
    financing_option_id: Optional[str] = None,
) -> Action:
    """
    Create a validated Action object.

    This helper keeps action construction consistent across
    all candidate action types.
    """

    return Action(
        invoice_id=invoice.invoice_id,
        action_type=action_type,
        scheduled_date=scheduled_date,
        amount=amount if amount is not None else invoice.amount,
        funding_source=funding_source,
        financing_option_id=financing_option_id,
    )


def generate_invoice_actions(
    invoice: InvoiceInput,
) -> list[Action]:
    """
    Generate candidate actions for a single invoice.

    The generator considers:

        PAY_NOW
        PAY_EARLY
        PAY_MATURITY
        DELAY
        BANK_FINANCE
        SUPPLIER_FINANCE
        RETAIN_CASH

    The returned actions are candidates only. No hard constraints,
    Liquidity Firewall checks, or optimization decisions are made here.

    Args:
        invoice:
            Invoice information used to generate the candidates.

    Returns:
        A list of candidate Action objects.

    Raises:
        ValueError:
            If the invoice is invalid.
    """

    if not isinstance(invoice, InvoiceInput):
        raise TypeError(
            "invoice must be an InvoiceInput instance."
        )

    actions: list[Action] = []

    # ---------------------------------------------------------------
    # 1. PAY_NOW
    # ---------------------------------------------------------------

    actions.append(
        _create_action(
            invoice=invoice,
            action_type=ActionType.PAY,
            scheduled_date=invoice.invoice_date,
            funding_source=FundingSource.CASH,
        )
    )

    # ---------------------------------------------------------------
    # 2. PAY_EARLY
    # ---------------------------------------------------------------

    if (
        invoice.discount_deadline is not None
        and invoice.discount_deadline >= invoice.invoice_date
        and invoice.discount_deadline < invoice.due_date
        and invoice.discount_rate > Decimal("0")
    ):
        actions.append(
            _create_action(
                invoice=invoice,
                action_type=ActionType.PAY,
                scheduled_date=invoice.discount_deadline,
                funding_source=FundingSource.CASH,
            )
        )

    # ---------------------------------------------------------------
    # 3. PAY_MATURITY
    # ---------------------------------------------------------------

    actions.append(
        _create_action(
            invoice=invoice,
            action_type=ActionType.PAY,
            scheduled_date=invoice.due_date,
            funding_source=FundingSource.CASH,
        )
    )

    # ---------------------------------------------------------------
    # 4. DELAY
    # ---------------------------------------------------------------

    if invoice.permissible_delay_days > 0:
        delay_date = (
            invoice.due_date
            + __import__("datetime").timedelta(
                days=invoice.permissible_delay_days
            )
        )

        actions.append(
            _create_action(
                invoice=invoice,
                action_type=ActionType.DEFER,
                scheduled_date=delay_date,
                funding_source=None,
            )
        )

    # ---------------------------------------------------------------
    # 5. BANK_FINANCE
    # ---------------------------------------------------------------

    if invoice.bank_financing_available:
        actions.append(
            _create_action(
                invoice=invoice,
                action_type=ActionType.FINANCE,
                scheduled_date=invoice.due_date,
                funding_source=FundingSource.BANK,
                financing_option_id=invoice.bank_financing_option_id,
            )
        )

    # ---------------------------------------------------------------
    # 6. SUPPLIER_FINANCE
    # ---------------------------------------------------------------

    if invoice.supplier_financing_available:
        actions.append(
            _create_action(
                invoice=invoice,
                action_type=ActionType.FINANCE,
                scheduled_date=invoice.due_date,
                funding_source=FundingSource.SUPPLIER_FINANCE,
                financing_option_id=(
                    invoice.supplier_financing_option_id
                ),
            )
        )

    # ---------------------------------------------------------------
    # 7. RETAIN_CASH
    # ---------------------------------------------------------------

    actions.append(
        _create_action(
            invoice=invoice,
            action_type=ActionType.RETAIN,
            scheduled_date=invoice.due_date,
            amount=Decimal("0"),
            funding_source=None,
        )
    )

    return actions