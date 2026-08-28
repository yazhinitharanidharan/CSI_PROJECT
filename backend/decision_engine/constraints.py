"""
Hard-constraint validation for the LiquidityOS Decision Engine.

This module is responsible for determining whether an invoice,
candidate action, or complete plan violates a hard constraint.

Hard constraints are NEVER silently ignored.

The module does not optimize plans and does not select the final
financial decision. It only determines feasibility.

Existing project models are reused:
    - Action
    - Plan
    - PaymentDecision
    - FinancingDecision

Forecast data is consumed using the finalized ForecastResult /
ForecastDay interface from the Forecast Engine. No duplicate forecast
model is created here.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from .models import (
    Action,
    FinancingDecision,
    FundingSource,
    PaymentDecision,
    Plan,
)


# ---------------------------------------------------------------------
# Constraint result
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ConstraintResult:
    """
    Result of one hard-constraint validation.

    Attributes:
        valid:
            True when the constraint is satisfied.

        constraint:
            Name of the constraint being checked.

        reason:
            Human-readable explanation.

        details:
            Additional structured information useful for debugging
            and later explainability.
    """

    valid: bool
    constraint: str
    reason: str
    details: dict[str, Any]


# ---------------------------------------------------------------------
# Generic data helpers
# ---------------------------------------------------------------------

def _read_value(
    obj: Any,
    field_name: str,
    *,
    required: bool = True,
) -> Any:
    """
    Read a field from either a dataclass/object or a dictionary.

    This allows the constraint engine to consume existing project
    models without creating duplicate versions.

    Args:
        obj:
            Object or mapping containing the requested field.

        field_name:
            Field name to retrieve.

        required:
            If True, missing fields raise ValueError.

    Returns:
        Field value.

    Raises:
        ValueError:
            If a required field is missing.
    """

    if isinstance(obj, Mapping):
        if field_name in obj:
            return obj[field_name]

    elif hasattr(obj, field_name):
        return getattr(obj, field_name)

    if required:
        raise ValueError(
            f"Required field '{field_name}' is missing."
        )

    return None


def _decimal(
    value: Any,
    field_name: str,
) -> Decimal:
    """
    Convert a numeric value safely to Decimal.

    Strings and Decimal values are preferred for financial precision.
    """

    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, float):
        # Convert through string rather than Decimal(float) so that
        # binary floating-point artifacts are not introduced.
        result = Decimal(str(value))
    else:
        try:
            result = Decimal(str(value))
        except Exception as exc:
            raise ValueError(
                f"{field_name} must be a valid numeric value."
            ) from exc

    return result


def _success(
    constraint: str,
    reason: str,
    **details: Any,
) -> ConstraintResult:
    """Create a successful constraint result."""

    return ConstraintResult(
        valid=True,
        constraint=constraint,
        reason=reason,
        details=details,
    )


def _failure(
    constraint: str,
    reason: str,
    **details: Any,
) -> ConstraintResult:
    """Create a failed constraint result."""

    return ConstraintResult(
        valid=False,
        constraint=constraint,
        reason=reason,
        details=details,
    )


# ---------------------------------------------------------------------
# 1. Invoice validation
# ---------------------------------------------------------------------

def validate_invoice(
    invoice: Any,
) -> ConstraintResult:
    """
    Validate the basic integrity of an invoice.

    The function checks fields when they are available in the
    existing invoice representation.

    Required:
        invoice_id
        amount

    Optional fields are validated when present:
        due_date
        payment_status
        mandatory

    Returns:
        ConstraintResult.
    """

    try:
        invoice_id = _read_value(
            invoice,
            "invoice_id",
        )

        amount = _decimal(
            _read_value(invoice, "amount"),
            "amount",
        )

        if not invoice_id:
            return _failure(
                "invoice",
                "Invoice ID cannot be empty.",
            )

        if amount <= Decimal("0"):
            return _failure(
                "invoice",
                "Invoice amount must be greater than zero.",
                invoice_id=invoice_id,
                amount=str(amount),
            )

        due_date = _read_value(
            invoice,
            "due_date",
            required=False,
        )

        if due_date is not None and not isinstance(due_date, date):
            return _failure(
                "invoice",
                "Invoice due_date must be a date.",
                invoice_id=invoice_id,
            )

        payment_status = _read_value(
            invoice,
            "payment_status",
            required=False,
        )

        if payment_status is not None:
            normalized_status = str(payment_status).lower()

            if normalized_status in {
                "paid",
                "settled",
                "completed",
            }:
                return _failure(
                    "invoice",
                    "Invoice has already been paid.",
                    invoice_id=invoice_id,
                    payment_status=normalized_status,
                )

        return _success(
            "invoice",
            "Invoice passed basic validation.",
            invoice_id=invoice_id,
            amount=str(amount),
        )

    except ValueError as exc:
        return _failure(
            "invoice",
            str(exc),
        )


# ---------------------------------------------------------------------
# 2. Duplicate-payment validation
# ---------------------------------------------------------------------

def validate_duplicate_payment(
    invoice: Any,
    existing_payments: Sequence[Any] = (),
) -> ConstraintResult:
    """
    Prevent a payment from being created for an invoice that has
    already been paid.

    Existing payment records may be dictionaries or objects.

    The invoice ID is matched against:
        invoice_id

    """

    try:
        invoice_id = _read_value(
            invoice,
            "invoice_id",
        )

        invoice_status = _read_value(
            invoice,
            "payment_status",
            required=False,
        )

        if invoice_status is not None:
            if str(invoice_status).lower() in {
                "paid",
                "settled",
                "completed",
            }:
                return _failure(
                    "duplicate_payment",
                    "Invoice is already marked as paid.",
                    invoice_id=invoice_id,
                )

        for payment in existing_payments:
            payment_invoice_id = _read_value(
                payment,
                "invoice_id",
                required=False,
            )

            if payment_invoice_id != invoice_id:
                continue

            payment_status = _read_value(
                payment,
                "status",
                required=False,
            )

            if payment_status is None:
                payment_status = _read_value(
                    payment,
                    "payment_status",
                    required=False,
                )

            # If no status exists, the matching record is treated as
            # an existing payment to avoid silently allowing duplicates.
            if payment_status is None:
                return _failure(
                    "duplicate_payment",
                    "An existing payment record was found for the invoice.",
                    invoice_id=invoice_id,
                )

            if str(payment_status).lower() in {
                "paid",
                "pending",
                "processing",
                "completed",
                "scheduled",
            }:
                return _failure(
                    "duplicate_payment",
                    "A payment already exists for the invoice.",
                    invoice_id=invoice_id,
                    payment_status=str(payment_status),
                )

        return _success(
            "duplicate_payment",
            "No duplicate payment was detected.",
            invoice_id=invoice_id,
        )

    except ValueError as exc:
        return _failure(
            "duplicate_payment",
            str(exc),
        )


# ---------------------------------------------------------------------
# 3. Payment-window validation
# ---------------------------------------------------------------------

def validate_payment_window(
    invoice: Any,
    payment_date: date,
) -> ConstraintResult:
    """
    Validate whether a proposed payment date is within the invoice's
    permitted payment window.

    Supported optional invoice fields:

        earliest_payment_date
        payment_start_date
        discount_deadline
        due_date
        maturity_date
        absolute_deadline

    The function does not invent a payment window when the project
    data does not provide one.
    """

    try:
        invoice_id = _read_value(
            invoice,
            "invoice_id",
        )

        if not isinstance(payment_date, date):
            return _failure(
                "payment_window",
                "payment_date must be a date.",
                invoice_id=invoice_id,
            )

        earliest_date = _read_value(
            invoice,
            "earliest_payment_date",
            required=False,
        )

        if earliest_date is None:
            earliest_date = _read_value(
                invoice,
                "payment_start_date",
                required=False,
            )

        if earliest_date is not None:
            if payment_date < earliest_date:
                return _failure(
                    "payment_window",
                    "Payment occurs before the permitted payment window.",
                    invoice_id=invoice_id,
                    payment_date=str(payment_date),
                    earliest_payment_date=str(earliest_date),
                )

        deadline = _read_value(
            invoice,
            "absolute_deadline",
            required=False,
        )

        if deadline is None:
            deadline = _read_value(
                invoice,
                "maturity_date",
                required=False,
            )

        if deadline is None:
            deadline = _read_value(
                invoice,
                "due_date",
                required=False,
            )

        if deadline is not None and payment_date > deadline:
            return _failure(
                "payment_window",
                "Payment occurs after the invoice deadline.",
                invoice_id=invoice_id,
                payment_date=str(payment_date),
                deadline=str(deadline),
            )

        return _success(
            "payment_window",
            "Payment date is within the available payment window.",
            invoice_id=invoice_id,
            payment_date=str(payment_date),
        )

    except ValueError as exc:
        return _failure(
            "payment_window",
            str(exc),
        )


# ---------------------------------------------------------------------
# 4. Financing-limit validation
# ---------------------------------------------------------------------

def validate_financing_limit(
    financing_decision: FinancingDecision,
    available_limit: Decimal,
) -> ConstraintResult:
    """
    Ensure a financing decision does not exceed the available facility
    limit.

    Args:
        financing_decision:
            Existing project FinancingDecision model.

        available_limit:
            Remaining financing capacity.

    Returns:
        ConstraintResult.
    """

    amount = financing_decision.amount
    limit = _decimal(
        available_limit,
        "available_limit",
    )

    if limit < Decimal("0"):
        return _failure(
            "financing_limit",
            "Available financing limit cannot be negative.",
            available_limit=str(limit),
        )

    if amount > limit:
        return _failure(
            "financing_limit",
            "Financing amount exceeds the available financing limit.",
            financing_option_id=(
                financing_decision.financing_option_id
            ),
            requested_amount=str(amount),
            available_limit=str(limit),
        )

    return _success(
        "financing_limit",
        "Financing amount is within the available limit.",
        requested_amount=str(amount),
        available_limit=str(limit),
    )


# ---------------------------------------------------------------------
# 5. Financing-eligibility validation
# ---------------------------------------------------------------------

def validate_financing_eligibility(
    financing_decision: FinancingDecision,
    eligible_sources: Optional[set[FundingSource]] = None,
) -> ConstraintResult:
    """
    Validate that the selected financing source is eligible.

    Args:
        financing_decision:
            Existing FinancingDecision model.

        eligible_sources:
            Optional set of financing sources currently allowed by
            the financing engine.

    Returns:
        ConstraintResult.
    """

    source = financing_decision.funding_source

    if source == FundingSource.CASH:
        return _failure(
            "financing_eligibility",
            "Cash is not an external financing source.",
            funding_source=source.value,
        )

    if eligible_sources is not None:
        if source not in eligible_sources:
            return _failure(
                "financing_eligibility",
                "Selected financing source is not currently eligible.",
                funding_source=source.value,
            )

    return _success(
        "financing_eligibility",
        "Selected financing source is eligible.",
        funding_source=source.value,
    )


# ---------------------------------------------------------------------
# 6. Maximum-delay validation
# ---------------------------------------------------------------------

def validate_maximum_delay(
    invoice: Any,
    payment_date: date,
) -> ConstraintResult:
    """
    Validate the maximum permissible delay for an invoice.

    Supported fields:

        due_date
        maturity_date
        permissible_delay_days
        maximum_delay_days
        absolute_deadline

    If an absolute deadline is explicitly supplied, it takes
    precedence over calculated delay.
    """

    try:
        invoice_id = _read_value(
            invoice,
            "invoice_id",
        )

        due_date = _read_value(
            invoice,
            "due_date",
            required=False,
        )

        if due_date is None:
            due_date = _read_value(
                invoice,
                "maturity_date",
                required=False,
            )

        if due_date is None:
            return _failure(
                "maximum_delay",
                "Invoice does not provide a due/maturity date.",
                invoice_id=invoice_id,
            )

        if not isinstance(due_date, date):
            return _failure(
                "maximum_delay",
                "Invoice due date must be a date.",
                invoice_id=invoice_id,
            )

        absolute_deadline = _read_value(
            invoice,
            "absolute_deadline",
            required=False,
        )

        if absolute_deadline is not None:
            if payment_date > absolute_deadline:
                return _failure(
                    "maximum_delay",
                    "Payment exceeds the absolute deadline.",
                    invoice_id=invoice_id,
                    payment_date=str(payment_date),
                    absolute_deadline=str(absolute_deadline),
                )

            return _success(
                "maximum_delay",
                "Payment is within the absolute deadline.",
                invoice_id=invoice_id,
            )

        permissible_delay = _read_value(
            invoice,
            "permissible_delay_days",
            required=False,
        )

        if permissible_delay is None:
            permissible_delay = _read_value(
                invoice,
                "maximum_delay_days",
                required=False,
            )

        if permissible_delay is None:
            return _failure(
                "maximum_delay",
                "No permissible-delay or absolute-deadline field is available.",
                invoice_id=invoice_id,
            )

        permissible_delay = int(permissible_delay)

        if permissible_delay < 0:
            return _failure(
                "maximum_delay",
                "Permissible delay cannot be negative.",
                invoice_id=invoice_id,
            )

        late_days = max(
            (payment_date - due_date).days,
            0,
        )

        if late_days > permissible_delay:
            return _failure(
                "maximum_delay",
                "Payment exceeds the maximum permissible delay.",
                invoice_id=invoice_id,
                late_days=late_days,
                permissible_delay_days=permissible_delay,
            )

        return _success(
            "maximum_delay",
            "Payment is within the maximum permissible delay.",
            invoice_id=invoice_id,
            late_days=late_days,
        )

    except (ValueError, TypeError) as exc:
        return _failure(
            "maximum_delay",
            str(exc),
        )


# ---------------------------------------------------------------------
# 7. Mandatory-obligation validation
# ---------------------------------------------------------------------

def validate_mandatory_obligations(
    plan: Plan,
    mandatory_obligations: Sequence[Any],
) -> ConstraintResult:
    """
    Ensure every mandatory obligation has been covered by the plan.

    Expected obligation fields:

        obligation_id
        amount
        due_date

    Optional:

        mandatory
        paid
        payment_status

    An obligation is considered covered when a payment decision in
    the plan references the same obligation/invoice identifier.

    This function does not invent obligation records.
    """

    covered_ids: set[str] = set()

    for decision in plan.payment_decisions:
        covered_ids.add(decision.invoice_id)

    missing: list[str] = []

    for obligation in mandatory_obligations:
        mandatory = _read_value(
            obligation,
            "mandatory",
            required=False,
        )

        # If mandatory is explicitly false, it is not a hard
        # obligation for this validation.
        if mandatory is False:
            continue

        obligation_id = _read_value(
            obligation,
            "obligation_id",
            required=False,
        )

        if obligation_id is None:
            obligation_id = _read_value(
                obligation,
                "invoice_id",
                required=False,
            )

        if obligation_id is None:
            return _failure(
                "mandatory_obligations",
                "Mandatory obligation is missing its identifier.",
            )

        paid = _read_value(
            obligation,
            "paid",
            required=False,
        )

        if paid is True:
            continue

        payment_status = _read_value(
            obligation,
            "payment_status",
            required=False,
        )

        if payment_status is not None:
            if str(payment_status).lower() in {
                "paid",
                "settled",
                "completed",
            }:
                continue

        if str(obligation_id) not in covered_ids:
            missing.append(str(obligation_id))

    if missing:
        return _failure(
            "mandatory_obligations",
            "One or more mandatory obligations are not covered.",
            missing_obligations=missing,
        )

    return _success(
        "mandatory_obligations",
        "All mandatory obligations are covered.",
    )


# ---------------------------------------------------------------------
# 8. Critical-supplier coverage validation
# ---------------------------------------------------------------------

def validate_critical_supplier_coverage(
    plan: Plan,
    critical_supplier_invoice_ids: Sequence[str],
) -> ConstraintResult:
    """
    Ensure invoices belonging to critical suppliers are covered.

    The Decision Engine owns the policy defining which suppliers are
    considered critical.

    This function intentionally does NOT hard-code a threshold such
    as criticality_score >= 75.

    The caller supplies the already-identified critical supplier
    invoice IDs.
    """

    covered_ids = {
        decision.invoice_id
        for decision in plan.payment_decisions
    }

    missing = [
        invoice_id
        for invoice_id in critical_supplier_invoice_ids
        if invoice_id not in covered_ids
    ]

    if missing:
        return _failure(
            "critical_supplier_coverage",
            "Critical supplier obligations are not fully covered.",
            missing_invoice_ids=missing,
        )

    return _success(
        "critical_supplier_coverage",
        "All required critical supplier obligations are covered.",
    )


# ---------------------------------------------------------------------
# 9. Cash-flow validation
# ---------------------------------------------------------------------

def validate_cash_flow(
    plan: Plan,
    initial_deployable_cash: Decimal,
    forecast_result: Any,
) -> ConstraintResult:
    """
    Validate that the plan does not require more cash than is
    available while considering the forecasted cash position.

    ForecastResult must follow the team's finalized interface:

        days
        minimum_cash
        reserve_requirement
        reserve_breach
        survival_horizon_days
        ...

    ForecastDay contains:

        date
        projected_cash
        inflows
        outflows

    This function does not create a second forecast representation.
    """

    try:
        starting_cash = _decimal(
            initial_deployable_cash,
            "initial_deployable_cash",
        )

        if starting_cash < Decimal("0"):
            return _failure(
                "cash_flow",
                "Initial deployable cash cannot be negative.",
            )

        total_cash_required = plan.total_payment_amount

        if total_cash_required > starting_cash + plan.total_financing_draw:
            return _failure(
                "cash_flow",
                "Plan requires more direct funding than available cash and financing draw.",
                required_cash=str(total_cash_required),
                deployable_cash=str(starting_cash),
                financing_draw=str(plan.total_financing_draw),
            )

        forecast_days = _read_value(
            forecast_result,
            "days",
        )

        if not forecast_days:
            return _failure(
                "cash_flow",
                "Forecast contains no forecast days.",
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

        if minimum_cash < reserve_requirement:
            return _failure(
                "cash_flow",
                "Forecasted minimum cash falls below the required reserve.",
                minimum_cash=str(minimum_cash),
                reserve_requirement=str(reserve_requirement),
            )

        return _success(
            "cash_flow",
            "Plan passes the basic cash-flow constraint.",
            deployable_cash=str(starting_cash),
            minimum_forecast_cash=str(minimum_cash),
            reserve_requirement=str(reserve_requirement),
        )

    except (ValueError, TypeError) as exc:
        return _failure(
            "cash_flow",
            str(exc),
        )


# ---------------------------------------------------------------------
# 10. Liquidity Firewall validation
# ---------------------------------------------------------------------

def validate_firewall(
    plan: Plan,
    forecast_result: Any,
) -> ConstraintResult:
    """
    Validate the Liquidity Firewall.

    The Firewall is a hard constraint.

    IMPORTANT SEMANTICS:

        projected_cash < reserve_requirement
        => Firewall violation

    It is NOT:

        projected_cash < 0

    The Forecast Engine already calculates reserve_breach, but this
    function independently verifies the forecast days so that the
    Decision Engine never silently accepts a reserve violation.
    """

    try:
        reserve_requirement = _decimal(
            _read_value(
                forecast_result,
                "reserve_requirement",
            ),
            "reserve_requirement",
        )

        forecast_days = _read_value(
            forecast_result,
            "days",
        )

        if not forecast_days:
            return _failure(
                "firewall",
                "Forecast contains no forecast days.",
            )

        violations: list[dict[str, Any]] = []

        for forecast_day in forecast_days:
            projected_cash = _decimal(
                _read_value(
                    forecast_day,
                    "projected_cash",
                ),
                "projected_cash",
            )

            day_value = _read_value(
                forecast_day,
                "date",
            )

            if projected_cash < reserve_requirement:
                violations.append(
                    {
                        "date": str(day_value),
                        "projected_cash": str(projected_cash),
                        "reserve_requirement": str(
                            reserve_requirement
                        ),
                    }
                )

        reported_breach = bool(
            _read_value(
                forecast_result,
                "reserve_breach",
            )
        )

        calculated_breach = bool(violations)

        # Detect inconsistency between the Forecast Engine's
        # reported value and the actual day-by-day data.
        if reported_breach != calculated_breach:
            return _failure(
                "firewall",
                "Forecast reserve_breach is inconsistent with forecast days.",
                reported_reserve_breach=reported_breach,
                calculated_reserve_breach=calculated_breach,
                violations=violations,
            )

        if calculated_breach:
            return _failure(
                "firewall",
                "Liquidity Firewall would be breached.",
                reserve_requirement=str(reserve_requirement),
                violations=violations,
            )

        return _success(
            "firewall",
            "Plan passes the Liquidity Firewall.",
            reserve_requirement=str(reserve_requirement),
        )

    except (ValueError, TypeError) as exc:
        return _failure(
            "firewall",
            str(exc),
        )


# ---------------------------------------------------------------------
# 11. Complete-plan validation
# ---------------------------------------------------------------------

def validate_plan(
    plan: Plan,
    *,
    invoices: Sequence[Any] = (),
    existing_payments: Sequence[Any] = (),
    mandatory_obligations: Sequence[Any] = (),
    critical_supplier_invoice_ids: Sequence[str] = (),
    forecast_result: Any = None,
    initial_deployable_cash: Optional[Decimal] = None,
    financing_limits: Optional[dict[str, Decimal]] = None,
    eligible_financing_sources: Optional[
        set[FundingSource]
    ] = None,
) -> list[ConstraintResult]:
    """
    Validate a complete candidate plan against all available
    hard constraints.

    The function returns every constraint result instead of stopping
    at the first failure. This makes rejection explanations
    transparent.

    Args:
        plan:
            Existing project Plan model.

        invoices:
            Invoice records used by the plan.

        existing_payments:
            Existing payment records.

        mandatory_obligations:
            Mandatory obligations that must be covered.

        critical_supplier_invoice_ids:
            Invoice IDs belonging to suppliers that the Decision
            Engine has classified as critical.

        forecast_result:
            Forecast Engine's finalized ForecastResult.

        initial_deployable_cash:
            FinancialState.deployable_cash.

        financing_limits:
            Mapping of financing_option_id to currently available
            financing limit.

        eligible_financing_sources:
            Financing sources currently allowed.

    Returns:
        List of ConstraintResult objects.

    Important:
        A plan is feasible only if every returned result is valid.
    """

    results: list[ConstraintResult] = []

    # -------------------------------------------------------------
    # Plan-level sanity check
    # -------------------------------------------------------------

    if not plan.plan_id:
        results.append(
            _failure(
                "plan",
                "Plan ID cannot be empty.",
            )
        )
        return results

    # -------------------------------------------------------------
    # Invoice validations
    # -------------------------------------------------------------

    invoice_by_id: dict[str, Any] = {}

    for invoice in invoices:
        invoice_id = _read_value(
            invoice,
            "invoice_id",
            required=False,
        )

        if invoice_id is None:
            results.append(
                _failure(
                    "invoice",
                    "Invoice is missing invoice_id.",
                )
            )
            continue

        invoice_by_id[str(invoice_id)] = invoice

    for payment_decision in plan.payment_decisions:
        invoice = invoice_by_id.get(
            payment_decision.invoice_id
        )

        if invoice is None:
            results.append(
                _failure(
                    "invoice",
                    "Plan references an invoice that was not supplied.",
                    invoice_id=payment_decision.invoice_id,
                )
            )
            continue

        results.append(
            validate_invoice(invoice)
        )

        results.append(
            validate_duplicate_payment(
                invoice,
                existing_payments,
            )
        )

        results.append(
            validate_payment_window(
                invoice,
                payment_decision.scheduled_date,
            )
        )

        results.append(
            validate_maximum_delay(
                invoice,
                payment_decision.scheduled_date,
            )
        )

    # -------------------------------------------------------------
    # Mandatory obligations
    # -------------------------------------------------------------

    results.append(
        validate_mandatory_obligations(
            plan,
            mandatory_obligations,
        )
    )

    # -------------------------------------------------------------
    # Critical suppliers
    # -------------------------------------------------------------

    results.append(
        validate_critical_supplier_coverage(
            plan,
            critical_supplier_invoice_ids,
        )
    )

    # -------------------------------------------------------------
    # Financing validations
    # -------------------------------------------------------------

    for financing_decision in plan.financing_decisions:

        if financing_limits is not None:
            available_limit = financing_limits.get(
                financing_decision.financing_option_id
            )

            if available_limit is None:
                results.append(
                    _failure(
                        "financing_limit",
                        "No financing limit was supplied for the selected option.",
                        financing_option_id=(
                            financing_decision.financing_option_id
                        ),
                    )
                )
            else:
                results.append(
                    validate_financing_limit(
                        financing_decision,
                        available_limit,
                    )
                )

        results.append(
            validate_financing_eligibility(
                financing_decision,
                eligible_financing_sources,
            )
        )

    # -------------------------------------------------------------
    # Cash-flow validation
    # -------------------------------------------------------------

    if (
        forecast_result is not None
        and initial_deployable_cash is not None
    ):
        results.append(
            validate_cash_flow(
                plan=plan,
                initial_deployable_cash=(
                    initial_deployable_cash
                ),
                forecast_result=forecast_result,
            )
        )

        # ---------------------------------------------------------
        # Liquidity Firewall
        # ---------------------------------------------------------

        results.append(
            validate_firewall(
                plan=plan,
                forecast_result=forecast_result,
            )
        )

    else:
        results.append(
            _failure(
                "cash_flow",
                "FinancialState.deployable_cash and ForecastResult "
                "are required to validate cash-flow feasibility.",
            )
        )

        results.append(
            _failure(
                "firewall",
                "ForecastResult is required to validate the "
                "Liquidity Firewall.",
            )
        )

    return results


# ---------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------

def is_plan_feasible(
    results: Sequence[ConstraintResult],
) -> bool:
    """
    Return True only when every hard constraint is satisfied.

    This helper is intentionally strict:
    any failed constraint makes the plan infeasible.
    """

    return all(
        result.valid
        for result in results
    )