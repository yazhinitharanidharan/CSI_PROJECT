from .models import PaymentHistoryRecord, SupplierProfile


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DEFAULT_CRITICALITY_WEIGHTS = {
    "strategic_importance": 0.25,
    "single_source_risk": 0.20,
    "lead_time_risk": 0.15,
    "spend_concentration": 0.20,
    "graph_centrality": 0.20,
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def calculate_single_source_risk(
    substitutability_score: float,
) -> float:
    """
    Higher substitutability means easier replacement.

    Therefore:
        single-source risk = 100 - substitutability

    This mapping is an implementation choice because the PRD
    specifies the dimension but does not prescribe its exact formula.
    """

    return clamp(100.0 - substitutability_score)


def calculate_lead_time_risk(
    lead_time_days: int,
) -> float:
    """
    Convert lead time into a 0-100 risk score.

    Implementation assumption for the hackathon:
      <= 7 days   -> low
      30+ days    -> high

    The PRD identifies lead-time risk as a criticality dimension
    but does not define exact thresholds.
    """

    if lead_time_days <= 7:
        return 0.0

    if lead_time_days >= 30:
        return 100.0

    return ((lead_time_days - 7) / (30 - 7)) * 100.0


def calculate_criticality(
    supplier: SupplierProfile,
    graph_centrality_score: float,
    weights: dict[str, float] | None = None,
) -> float:
    """
    Supplier criticality based on the PRD formula:

        Criticality =
            w1 * StrategicImportance
          + w2 * SingleSourceRisk
          + w3 * LeadTimeRisk
          + w4 * SpendConcentration
          + w5 * GraphCentrality
    """

    weights = weights or DEFAULT_CRITICALITY_WEIGHTS

    single_source_risk = calculate_single_source_risk(
        supplier.substitutability_score
    )

    lead_time_risk = calculate_lead_time_risk(
        supplier.lead_time_days
    )

    score = (
        weights["strategic_importance"]
        * supplier.strategic_importance
        + weights["single_source_risk"]
        * single_source_risk
        + weights["lead_time_risk"]
        * lead_time_risk
        + weights["spend_concentration"]
        * supplier.spend_concentration
        + weights["graph_centrality"]
        * graph_centrality_score
    )

    return round(clamp(score), 2)


def calculate_distress(
    supplier: SupplierProfile,
    payment_history: list[PaymentHistoryRecord],
) -> float:
    """
    Calculate supplier distress.

    If a distress score already exists from the supplier-risk state,
    preserve it.

    Otherwise, use payment-history stress as a lightweight deterministic
    fallback.

    The PRD requires distress as an output but does not define a precise
    mathematical distress formula, so this fallback is explicitly an
    implementation assumption.
    """

    if supplier.distress_score is not None:
        return round(clamp(supplier.distress_score), 2)

    supplier_history = [
        record
        for record in payment_history
        if record.supplier_id == supplier.id
    ]

    if not supplier_history:
        return 0.0

    average_delay = sum(
        record.days_late for record in supplier_history
    ) / len(supplier_history)

    # Implementation assumption:
    # 0 days late = 0 distress
    # 30+ days late = 100 distress
    distress = (average_delay / 30.0) * 100.0

    return round(clamp(distress), 2)


def calculate_disruption_probability(
    criticality_score: float,
    distress_score: float,
) -> float:
    """
    Estimate disruption probability from deterministic risk scores.

    This is an MVP heuristic, not a statistical probability model.
    """

    probability = (
        0.5 * criticality_score
        + 0.5 * distress_score
    ) / 100.0

    return round(max(0.0, min(1.0, probability)), 4)


def calculate_cascade_risk(
    graph,
    supplier_id: str,
    distress_score: float,
    affected_suppliers: list[str],
) -> float:
    """
    Calculate a simple cascading-risk score.

    More downstream dependencies + greater distress
    => greater cascade risk.

    This is an MVP deterministic heuristic.
    """

    if supplier_id not in graph:
        return 0.0

    if not affected_suppliers:
        return 0.0

    total_nodes = max(graph.number_of_nodes() - 1, 1)

    affected_ratio = len(affected_suppliers) / total_nodes

    cascade_risk = affected_ratio * distress_score

    return round(clamp(cascade_risk), 2)


def classify_risk(score: float) -> str:
    if score >= 75:
        return "CRITICAL"

    if score >= 50:
        return "HIGH"

    if score >= 25:
        return "MEDIUM"

    return "LOW"