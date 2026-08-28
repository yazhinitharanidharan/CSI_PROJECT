from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SupplierProfile:
    """
    Supplier information used by the Supplier Intelligence Agent.

    Scores are represented on a 0-100 scale unless otherwise stated.
    """

    id: str
    name: str
    strategic_importance: float
    substitutability_score: float
    lead_time_days: int
    payment_terms_days: int
    spend_concentration: float
    status: str = "Active"

    # Optional because the supplier table in the PRD does not contain
    # distress_score directly. It lives in supplier_risk.
    distress_score: Optional[float] = None


@dataclass
class SupplierDependency:
    """
    Directed dependency between suppliers.

    This follows the supplier_dependencies data model from the PRD.
    """

    source_supplier_id: str
    target_supplier_id: str
    dependency_type: str
    dependency_weight: float
    disruption_impact: float


@dataclass
class PaymentHistoryRecord:
    """
    Simplified payment-history record.

    The PRD identifies payment history as an input to the Supplier
    Intelligence Agent, but does not prescribe a specific table schema
    for payment history.
    """

    supplier_id: str
    amount: float
    days_late: int = 0


@dataclass
class SupplierRiskResult:
    supplier_id: str
    supplier_name: str

    criticality_score: float
    distress_score: float
    graph_centrality_score: float
    disruption_probability: float
    cascade_risk_score: float

    dependency_count: int
    affected_suppliers: List[str] = field(default_factory=list)

    risk_level: str = "LOW"
    data_confidence: float = 100.0

    def to_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "criticality_score": self.criticality_score,
            "distress_score": self.distress_score,
            "graph_centrality_score": self.graph_centrality_score,
            "disruption_probability": self.disruption_probability,
            "cascade_risk_score": self.cascade_risk_score,
            "dependency_count": self.dependency_count,
            "affected_suppliers": self.affected_suppliers,
            "risk_level": self.risk_level,
            "data_confidence": self.data_confidence,
        }