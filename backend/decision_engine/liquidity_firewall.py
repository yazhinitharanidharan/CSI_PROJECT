"""Dynamic, constraint-first liquidity safety gate.

This module does not replace ``constraints.validate_firewall``.  It provides a
stricter pre-optimizer boundary based on future obligations, uncertainty,
supplier-risk data already produced elsewhere, and conservative financing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence


class FirewallStatus(str, Enum):
    SAFE = "SAFE"
    BLOCKED = "BLOCKED"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"


@dataclass(frozen=True)
class FirewallResult:
    status: FirewallStatus
    allowed: bool
    risk_level: str
    risk_score: Decimal
    protected_cash: Decimal
    available_cash: Decimal
    proposed_transaction: Decimal
    projected_cash_after_transaction: Decimal
    safety_margin: Decimal
    future_obligation_requirement: Decimal
    receivable_uncertainty_buffer: Decimal
    supplier_risk_buffer: Decimal
    financing_adjustment: Decimal
    human_approval_required: bool
    reasons: tuple[str, ...]
    metrics: dict[str, Any]


def _read(item: Any, field: str, default: Any = None) -> Any:
    return item.get(field, default) if isinstance(item, Mapping) else getattr(item, field, default)


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean.")
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{name} must be numeric.") from exc


def _policy_reserve(state: Any, forecast: Any, explicit: Decimal | None) -> Decimal:
    if explicit is not None:
        reserve = _decimal(explicit, "policy_reserve")
    else:
        policy = _read(state, "risk_policy")
        reserve = _read(policy, "minimum_reserve", _read(forecast, "reserve_requirement", 0))
        reserve = _decimal(reserve, "minimum_reserve")
    if reserve < 0:
        raise ValueError("policy reserve cannot be negative.")
    return reserve


def _obligation_requirement(obligations: Sequence[Any]) -> Decimal:
    """Protect mandatory/critical obligations in full and others at 50%."""
    total = Decimal("0")
    for obligation in obligations:
        amount = _read(obligation, "total", _read(obligation, "amount", 0))
        amount = _decimal(amount, "obligation amount")
        if amount < 0:
            raise ValueError("obligation amount cannot be negative.")
        mandatory = bool(_read(obligation, "mandatory", False))
        critical = bool(_read(obligation, "critical", False)) or _decimal(_read(obligation, "supplier_criticality", 0), "supplier_criticality") >= Decimal("75")
        total += amount if mandatory or critical else amount * Decimal("0.50")
    return total


def _uncertainty(value: Any) -> Decimal:
    """Normalize an explicit uncertainty or reliability value to 0..1."""
    explicit = _read(value, "uncertainty", None)
    if explicit is not None:
        result = _decimal(explicit, "receivable uncertainty")
    else:
        reliability = _read(value, "reliability", _read(value, "reliability_score", None))
        if reliability is None:
            return Decimal("0.50")  # Unknown receivables are not guaranteed.
        result = Decimal("1") - _decimal(reliability, "receivable reliability")
        if result < 0:  # Scores may use 0..100.
            result = Decimal("1") - _decimal(reliability, "receivable reliability") / Decimal("100")
    if result > 1:
        result /= Decimal("100")
    return min(Decimal("1"), max(Decimal("0"), result))


def _receivable_buffer(receivables: Sequence[Any]) -> Decimal:
    buffer = Decimal("0")
    for receivable in receivables:
        if str(_read(receivable, "status", "expected")).lower() == "received":
            continue
        amount = _decimal(_read(receivable, "amount", 0), "receivable amount")
        if amount < 0:
            raise ValueError("receivable amount cannot be negative.")
        buffer += amount * _uncertainty(receivable)
    return buffer


def _supplier_risk_factor(risk: Any) -> Decimal:
    """Consume adapter-compatible risk fields; never recalculate supplier risk."""
    criticality = _decimal(_read(risk, "supplier_criticality", _read(risk, "criticality_score", 0)), "supplier criticality") / Decimal("100")
    liquidity_need = _decimal(_read(risk, "supplier_liquidity_need", _read(risk, "distress_score", 0)), "supplier liquidity need") / Decimal("100")
    disruption = _decimal(_read(risk, "disruption_probability", 0), "disruption probability")
    cascade = _decimal(_read(risk, "cascade_risk_score", 0), "cascade risk") / Decimal("100")
    return min(Decimal("1"), max(Decimal("0"), (criticality + liquidity_need + disruption + cascade) / Decimal("4")))


def _supplier_buffer(supplier_risks: Sequence[Any], policy_reserve: Decimal) -> tuple[Decimal, Decimal]:
    factors = [_supplier_risk_factor(risk) for risk in supplier_risks]
    return (policy_reserve * max(factors, default=Decimal("0")) * Decimal("0.25"), max(factors, default=Decimal("0")))


def _financing_adjustment(financing_options: Sequence[Any]) -> Decimal:
    """Only explicit, reliable, eligible financing reduces pressure; never at 100%."""
    adjustment = Decimal("0")
    for option in financing_options:
        if not bool(_read(option, "eligible", _read(option, "available", False))):
            continue
        reliability = _read(option, "reliability", _read(option, "reliability_score", None))
        if reliability is None:
            continue  # Existing facility limit alone is not a guarantee of funding.
        reliability = _decimal(reliability, "financing reliability")
        if reliability > 1:
            reliability /= Decimal("100")
        if reliability < Decimal("0.75"):
            continue
        limit = _decimal(_read(option, "available_limit", _read(option, "max_amount", 0)), "financing limit")
        if limit < 0:
            raise ValueError("financing limit cannot be negative.")
        approval_haircut = Decimal("0.50") if bool(_read(option, "approval_required", False)) else Decimal("0.80")
        adjustment += limit * min(Decimal("1"), reliability) * approval_haircut
    return adjustment


def calculate_dynamic_protected_cash(state: Any, *, forecast: Any = None, obligations: Sequence[Any] | None = None, receivables: Sequence[Any] | None = None, supplier_risks: Sequence[Any] = (), financing_options: Sequence[Any] = (), policy_reserve: Decimal | None = None) -> dict[str, Decimal]:
    """Calculate protected cash without ever reducing it below policy reserve."""
    obligations = list(_read(state, "obligations", ()) if obligations is None else obligations)
    receivables = list(_read(state, "receivables", ()) if receivables is None else receivables)
    reserve = _policy_reserve(state, forecast, policy_reserve)
    future = _obligation_requirement(obligations)
    receivable = _receivable_buffer(receivables)
    supplier, _ = _supplier_buffer(supplier_risks, reserve)
    financing = _financing_adjustment(financing_options)
    protected = max(reserve, reserve + future + receivable + supplier - financing)
    return {"protected_cash": protected, "policy_reserve": reserve, "future_obligation_requirement": future, "receivable_uncertainty_buffer": receivable, "supplier_risk_buffer": supplier, "financing_adjustment": financing}


def evaluate_transaction(state: Any, proposed_transaction: Any, *, forecast: Any = None, obligations: Sequence[Any] | None = None, receivables: Sequence[Any] | None = None, supplier_risks: Sequence[Any] = (), financing_options: Sequence[Any] = (), policy_reserve: Decimal | None = None) -> FirewallResult:
    """Authoritatively allow, block, or escalate one cash-consuming transaction."""
    amount = _decimal(_read(proposed_transaction, "cash_impact", _read(proposed_transaction, "amount", proposed_transaction)), "proposed transaction")
    if amount < 0:
        raise ValueError("proposed transaction cannot be negative.")
    components = calculate_dynamic_protected_cash(state, forecast=forecast, obligations=obligations, receivables=receivables, supplier_risks=supplier_risks, financing_options=financing_options, policy_reserve=policy_reserve)
    available = _decimal(_read(state, "deployable_cash", _read(state, "current_cash", 0)), "available cash")
    projected = available - amount
    margin = projected - components["protected_cash"]
    supplier_factor = _supplier_buffer(supplier_risks, components["policy_reserve"])[1]
    uncertainty_ratio = components["receivable_uncertainty_buffer"] / components["policy_reserve"] if components["policy_reserve"] else Decimal("0")
    margin_risk = max(Decimal("0"), Decimal("1") - max(Decimal("0"), margin) / max(components["protected_cash"], Decimal("1"))) * Decimal("20")
    score = min(Decimal("100"), margin_risk + supplier_factor * Decimal("65") + min(Decimal("1"), uncertainty_ratio) * Decimal("15") + (Decimal("20") if supplier_factor >= Decimal("0.95") else Decimal("0")))
    risk_level = "CRITICAL" if score >= 75 else "HIGH" if score >= 50 else "MEDIUM" if score >= 25 else "LOW"
    base_breach = bool(_read(forecast, "reserve_breach", False))
    reasons = ["Dynamic protected cash includes policy reserve.", "Future obligations and receivable uncertainty were considered."]
    if base_breach or margin < 0:
        reasons.append("Transaction would violate the Dynamic Liquidity Firewall.")
        status = FirewallStatus.BLOCKED
    elif risk_level in {"HIGH", "CRITICAL"}:
        reasons.append("Transaction is inside the boundary but requires human approval due to risk.")
        status = FirewallStatus.HUMAN_APPROVAL
    else:
        reasons.append("Required reserve and dynamic protection are maintained.")
        status = FirewallStatus.SAFE
    return FirewallResult(status=status, allowed=status != FirewallStatus.BLOCKED, risk_level=risk_level, risk_score=score.quantize(Decimal("0.01")), protected_cash=components["protected_cash"], available_cash=available, proposed_transaction=amount, projected_cash_after_transaction=projected, safety_margin=margin, future_obligation_requirement=components["future_obligation_requirement"], receivable_uncertainty_buffer=components["receivable_uncertainty_buffer"], supplier_risk_buffer=components["supplier_risk_buffer"], financing_adjustment=components["financing_adjustment"], human_approval_required=status == FirewallStatus.HUMAN_APPROVAL, reasons=tuple(reasons), metrics={"policy_reserve": components["policy_reserve"], "base_forecast_breach": base_breach})


def firewall_summary(result: FirewallResult) -> dict[str, Any]:
    """Return the compact JSON-safe frontend boundary representation."""
    money = lambda value: str(value)
    return {"status": result.status.value, "allowed": result.allowed, "risk": {"level": result.risk_level, "score": float(result.risk_score)}, "liquidity": {"protected_cash": money(result.protected_cash), "available_cash": money(result.available_cash), "projected_cash": money(result.projected_cash_after_transaction), "safety_margin": money(result.safety_margin)}, "requirements": {"future_obligations": money(result.future_obligation_requirement), "receivable_uncertainty_buffer": money(result.receivable_uncertainty_buffer), "supplier_risk_buffer": money(result.supplier_risk_buffer), "financing_offset": money(result.financing_adjustment)}, "human_approval_required": result.human_approval_required, "reasons": list(result.reasons)}
