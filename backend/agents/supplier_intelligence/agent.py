from .graph import (
    build_supplier_graph,
    calculate_centrality,
    find_affected_suppliers,
)
from .models import (
    PaymentHistoryRecord,
    SupplierDependency,
    SupplierProfile,
    SupplierRiskResult,
)
from .scoring import (
    calculate_criticality,
    calculate_distress,
    calculate_disruption_probability,
    calculate_cascade_risk,
    classify_risk,
)


class SupplierIntelligenceAgent:
    """
    Deterministic Supplier Intelligence Agent.

    Responsibilities:
      - Build supplier dependency graph
      - Calculate supplier centrality
      - Calculate criticality
      - Calculate distress
      - Estimate disruption probability
      - Traverse downstream dependencies
      - Calculate cascade risk
    """

    def analyze(
        self,
        supplier: SupplierProfile,
        suppliers: list[SupplierProfile],
        dependencies: list[SupplierDependency],
        payment_history: list[PaymentHistoryRecord],
    ) -> SupplierRiskResult:

        # 1. Build graph
        graph = build_supplier_graph(
            suppliers=suppliers,
            dependencies=dependencies,
        )

        # 2. Calculate centrality
        centrality_scores = calculate_centrality(graph)

        centrality_score = centrality_scores.get(
            supplier.id,
            0.0,
        )

        # 3. Calculate supplier distress
        distress_score = calculate_distress(
            supplier=supplier,
            payment_history=payment_history,
        )

        # 4. Calculate criticality
        criticality_score = calculate_criticality(
            supplier=supplier,
            graph_centrality_score=centrality_score,
        )

        # 5. Estimate disruption probability
        disruption_probability = calculate_disruption_probability(
            criticality_score=criticality_score,
            distress_score=distress_score,
        )

        # 6. Find downstream affected suppliers
        affected_suppliers = find_affected_suppliers(
            graph=graph,
            supplier_id=supplier.id,
        )

        # 7. Calculate cascade risk
        cascade_risk_score = calculate_cascade_risk(
            graph=graph,
            supplier_id=supplier.id,
            distress_score=distress_score,
            affected_suppliers=affected_suppliers,
        )

        # 8. Overall risk classification
        overall_risk_score = max(
            criticality_score,
            distress_score,
            cascade_risk_score,
        )

        risk_level = classify_risk(overall_risk_score)

        return SupplierRiskResult(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            criticality_score=criticality_score,
            distress_score=distress_score,
            graph_centrality_score=round(centrality_score, 2),
            disruption_probability=disruption_probability,
            cascade_risk_score=cascade_risk_score,
            dependency_count=len(affected_suppliers),
            affected_suppliers=affected_suppliers,
            risk_level=risk_level,
        )