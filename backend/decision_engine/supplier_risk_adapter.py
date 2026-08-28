"""
Supplier Risk Adapter for the Decision Engine.

This module translates the stable 8-field Supplier Intelligence
contract into the internal supplier-risk inputs expected by the
Decision Engine.

Important:
    - Supplier Intelligence remains unchanged.
    - The 8-field external contract remains unchanged.
    - The adapter does not make payment or financing decisions.
    - The adapter only validates and translates supplier-risk data.

MVP mapping:

    criticality_score
        -> supplier_criticality

    distress_score
        -> supplier_liquidity_need

The distress -> liquidity-need mapping is a Decision Engine
integration assumption for the MVP. It is NOT a Supplier
Intelligence formula.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping


# ---------------------------------------------------------------------
# Supplier Intelligence contract
# ---------------------------------------------------------------------

REQUIRED_FIELDS = {
    "supplier_id",
    "criticality_score",
    "distress_score",
    "disruption_probability",
    "cascade_risk_score",
    "dependency_count",
    "affected_supplier_ids",
    "risk_level",
}

VALID_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


# ---------------------------------------------------------------------
# Decision Engine representation
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class SupplierRiskInputs:
    """
    Supplier-risk values consumed by the Decision Engine.

    These names intentionally match InvoicePriorityInput in
    priority_engine.py.
    """

    supplier_id: str

    supplier_criticality: Decimal
    supplier_liquidity_need: Decimal

    disruption_probability: Decimal
    cascade_risk_score: Decimal

    dependency_count: int
    affected_supplier_ids: tuple[str, ...]

    risk_level: str

    # Preserve the original deterministic values for explainability.
    criticality_score: Decimal
    distress_score: Decimal


# ---------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------

def _require_field(
    payload: Mapping[str, Any],
    field_name: str,
) -> Any:
    """Return a required field or raise a clear validation error."""

    if field_name not in payload:
        raise ValueError(
            f"Supplier risk payload is missing required field "
            f"'{field_name}'."
        )

    return payload[field_name]


def _to_decimal(
    value: Any,
    field_name: str,
) -> Decimal:
    """
    Convert a numeric value to Decimal.

    Strings are supported because JSON payloads commonly represent
    decimal values as strings.
    """

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be numeric, not boolean."
        )

    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(
            f"{field_name} must be numeric."
        ) from exc


def _validate_range(
    value: Decimal,
    field_name: str,
    minimum: Decimal,
    maximum: Decimal,
) -> None:
    """Validate an inclusive numeric range."""

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{field_name} must be between "
            f"{minimum} and {maximum}; got {value}."
        )


# ---------------------------------------------------------------------
# Main adapter
# ---------------------------------------------------------------------

def adapt_supplier_risk(
    payload: Mapping[str, Any],
) -> SupplierRiskInputs:
    """
    Validate and translate a Supplier Intelligence payload.

    Expected external contract:

        {
            "supplier_id": "...",
            "criticality_score": 0-100,
            "distress_score": 0-100,
            "disruption_probability": 0-1,
            "cascade_risk_score": 0-100,
            "dependency_count": integer,
            "affected_supplier_ids": ["..."],
            "risk_level": "LOW|MEDIUM|HIGH|CRITICAL"
        }

    Decision Engine output:

        supplier_criticality
        supplier_liquidity_need

    MVP mapping:

        supplier_criticality = criticality_score
        supplier_liquidity_need = distress_score

    The function does not modify the original payload.
    """

    if not isinstance(payload, Mapping):
        raise TypeError(
            "Supplier risk payload must be a mapping/dictionary."
        )

    # -------------------------------------------------------------
    # Validate required fields
    # -------------------------------------------------------------

    missing_fields = sorted(
        REQUIRED_FIELDS - set(payload.keys())
    )

    if missing_fields:
        raise ValueError(
            "Supplier risk payload is missing required fields: "
            + ", ".join(missing_fields)
        )

    supplier_id = _require_field(
        payload,
        "supplier_id",
    )

    if not isinstance(supplier_id, str) or not supplier_id.strip():
        raise ValueError(
            "supplier_id must be a non-empty string."
        )

    # -------------------------------------------------------------
    # Convert numeric values
    # -------------------------------------------------------------

    criticality_score = _to_decimal(
        payload["criticality_score"],
        "criticality_score",
    )

    distress_score = _to_decimal(
        payload["distress_score"],
        "distress_score",
    )

    disruption_probability = _to_decimal(
        payload["disruption_probability"],
        "disruption_probability",
    )

    cascade_risk_score = _to_decimal(
        payload["cascade_risk_score"],
        "cascade_risk_score",
    )

    # -------------------------------------------------------------
    # Validate ranges
    # -------------------------------------------------------------

    _validate_range(
        criticality_score,
        "criticality_score",
        Decimal("0"),
        Decimal("100"),
    )

    _validate_range(
        distress_score,
        "distress_score",
        Decimal("0"),
        Decimal("100"),
    )

    _validate_range(
        disruption_probability,
        "disruption_probability",
        Decimal("0"),
        Decimal("1"),
    )

    _validate_range(
        cascade_risk_score,
        "cascade_risk_score",
        Decimal("0"),
        Decimal("100"),
    )

    # -------------------------------------------------------------
    # Validate dependency count
    # -------------------------------------------------------------

    dependency_count = payload["dependency_count"]

    if isinstance(dependency_count, bool):
        raise ValueError(
            "dependency_count must be a non-negative integer."
        )

    if isinstance(dependency_count, str):
        if not dependency_count.isdigit():
            raise ValueError(
                "dependency_count must be a non-negative integer."
            )

        dependency_count = int(
            dependency_count
        )

    elif isinstance(
        dependency_count,
        int,
    ):
        pass

    else:
        raise ValueError(
            "dependency_count must be a non-negative integer."
        )

    if dependency_count < 0:
        raise ValueError(
            "dependency_count cannot be negative."
        )

    # -------------------------------------------------------------
    # Validate affected suppliers
    # -------------------------------------------------------------

    affected_supplier_ids = payload[
        "affected_supplier_ids"
    ]

    if not isinstance(
        affected_supplier_ids,
        (list, tuple),
    ):
        raise ValueError(
            "affected_supplier_ids must be a list or tuple."
        )

    normalized_affected_ids: list[str] = []

    for supplier in affected_supplier_ids:
        if not isinstance(supplier, str):
            raise ValueError(
                "Every affected supplier ID must be a string."
            )

        if not supplier.strip():
            raise ValueError(
                "affected_supplier_ids cannot contain empty IDs."
            )

        normalized_affected_ids.append(
            supplier
        )

    # -------------------------------------------------------------
    # Validate risk level
    # -------------------------------------------------------------

    risk_level = payload["risk_level"]

    if not isinstance(risk_level, str):
        raise ValueError(
            "risk_level must be a string."
        )

    risk_level = risk_level.upper()

    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            "risk_level must be one of: "
            "LOW, MEDIUM, HIGH, CRITICAL."
        )

    # -------------------------------------------------------------
    # MVP Decision Engine mapping
    # -------------------------------------------------------------

    supplier_criticality = criticality_score

    supplier_liquidity_need = distress_score

    # -------------------------------------------------------------
    # Return normalized Decision Engine input
    # -------------------------------------------------------------

    return SupplierRiskInputs(
        supplier_id=supplier_id.strip(),

        supplier_criticality=supplier_criticality,
        supplier_liquidity_need=supplier_liquidity_need,

        disruption_probability=disruption_probability,
        cascade_risk_score=cascade_risk_score,

        dependency_count=dependency_count,

        affected_supplier_ids=tuple(
            normalized_affected_ids
        ),

        risk_level=risk_level,

        criticality_score=criticality_score,
        distress_score=distress_score,
    )


# ---------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------

def consume_supplier_risk(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Validate and return the supplier-risk information in the
    Decision Engine's internal naming convention.

    This is the simple API that other Decision Engine modules can call.

    Example:

        supplier = consume_supplier_risk(
            supplier_agent.to_decision_engine_dict()
        )

        priority_input = InvoicePriorityInput(
            invoice_id="INV-001",
            supplier_criticality=supplier[
                "supplier_criticality"
            ],
            supplier_liquidity_need=supplier[
                "supplier_liquidity_need"
            ],
        )
    """

    result = adapt_supplier_risk(
        payload
    )

    return {
        "supplier_id": result.supplier_id,

        "supplier_criticality": (
            result.supplier_criticality
        ),

        "supplier_liquidity_need": (
            result.supplier_liquidity_need
        ),

        "disruption_probability": (
            result.disruption_probability
        ),

        "cascade_risk_score": (
            result.cascade_risk_score
        ),

        "dependency_count": (
            result.dependency_count
        ),

        "affected_supplier_ids": (
            result.affected_supplier_ids
        ),

        "risk_level": result.risk_level,

        # Original values retained for traceability.
        "criticality_score": (
            result.criticality_score
        ),

        "distress_score": (
            result.distress_score
        ),
    }