from agents.supplier_intelligence.agent import SupplierIntelligenceAgent
from agents.supplier_intelligence.models import (
    PaymentHistoryRecord,
    SupplierDependency,
    SupplierProfile,
)


def create_test_data():
    supplier_a = SupplierProfile(
        id="supplier-a",
        name="Alpha Components",
        strategic_importance=95,
        substitutability_score=10,
        lead_time_days=28,
        payment_terms_days=30,
        spend_concentration=85,
        distress_score=78,
    )

    supplier_b = SupplierProfile(
        id="supplier-b",
        name="Beta Metals",
        strategic_importance=60,
        substitutability_score=50,
        lead_time_days=14,
        payment_terms_days=30,
        spend_concentration=40,
        distress_score=20,
    )

    supplier_c = SupplierProfile(
        id="supplier-c",
        name="Gamma Logistics",
        strategic_importance=50,
        substitutability_score=70,
        lead_time_days=10,
        payment_terms_days=30,
        spend_concentration=30,
        distress_score=10,
    )

    dependencies = [
        SupplierDependency(
            source_supplier_id="supplier-a",
            target_supplier_id="supplier-b",
            dependency_type="Supplies",
            dependency_weight=80,
            disruption_impact=90,
        ),
        SupplierDependency(
            source_supplier_id="supplier-b",
            target_supplier_id="supplier-c",
            dependency_type="Supplies",
            dependency_weight=60,
            disruption_impact=70,
        ),
    ]

    payment_history = [
        PaymentHistoryRecord(
            supplier_id="supplier-a",
            amount=200000,
            days_late=12,
        )
    ]

    return (
        supplier_a,
        [supplier_a, supplier_b, supplier_c],
        dependencies,
        payment_history,
    )


def test_supplier_agent_returns_risk_result():
    supplier, suppliers, dependencies, payment_history = create_test_data()

    agent = SupplierIntelligenceAgent()

    result = agent.analyze(
        supplier=supplier,
        suppliers=suppliers,
        dependencies=dependencies,
        payment_history=payment_history,
    )

    assert result.supplier_id == "supplier-a"
    assert result.criticality_score > 0
    assert result.distress_score == 78
    assert result.graph_centrality_score > 0
    assert result.disruption_probability > 0
    assert result.cascade_risk_score > 0


def test_supplier_agent_finds_downstream_dependencies():
    supplier, suppliers, dependencies, payment_history = create_test_data()

    agent = SupplierIntelligenceAgent()

    result = agent.analyze(
        supplier=supplier,
        suppliers=suppliers,
        dependencies=dependencies,
        payment_history=payment_history,
    )

    assert "supplier-b" in result.affected_suppliers
    assert "supplier-c" in result.affected_suppliers


def test_high_risk_supplier_is_classified():
    supplier, suppliers, dependencies, payment_history = create_test_data()

    agent = SupplierIntelligenceAgent()

    result = agent.analyze(
        supplier=supplier,
        suppliers=suppliers,
        dependencies=dependencies,
        payment_history=payment_history,
    )

    assert result.risk_level in {"HIGH", "CRITICAL"}
def test_isolated_supplier_has_no_cascade():
    isolated_supplier = SupplierProfile(
        id="isolated",
        name="Isolated Supplier",
        strategic_importance=40,
        substitutability_score=80,
        lead_time_days=5,
        payment_terms_days=30,
        spend_concentration=20,
        distress_score=20,
    )

    agent = SupplierIntelligenceAgent()

    result = agent.analyze(
        supplier=isolated_supplier,
        suppliers=[isolated_supplier],
        dependencies=[],
        payment_history=[],
    )

    assert result.affected_suppliers == []
    assert result.cascade_risk_score == 0
def test_supplier_distress_increases_disruption_probability():
    supplier_low_distress = SupplierProfile(
        id="supplier-critical",
        name="Critical Supplier",
        strategic_importance=90,
        substitutability_score=5,
        lead_time_days=30,
        payment_terms_days=30,
        spend_concentration=90,
        distress_score=20,
    )

    supplier_high_distress = SupplierProfile(
        id="supplier-critical",
        name="Critical Supplier",
        strategic_importance=90,
        substitutability_score=5,
        lead_time_days=30,
        payment_terms_days=30,
        spend_concentration=90,
        distress_score=90,
    )

    agent = SupplierIntelligenceAgent()

    low_risk = agent.analyze(
        supplier=supplier_low_distress,
        suppliers=[supplier_low_distress],
        dependencies=[],
        payment_history=[],
    )

    high_risk = agent.analyze(
        supplier=supplier_high_distress,
        suppliers=[supplier_high_distress],
        dependencies=[],
        payment_history=[],
    )

    assert high_risk.distress_score > low_risk.distress_score

    assert (
        high_risk.disruption_probability
        > low_risk.disruption_probability
    )
def test_critical_supplier_has_high_criticality():
    supplier = SupplierProfile(
        id="critical",
        name="Critical Supplier",
        strategic_importance=95,
        substitutability_score=5,
        lead_time_days=30,
        payment_terms_days=30,
        spend_concentration=90,
        distress_score=50,
    )

    agent = SupplierIntelligenceAgent()

    result = agent.analyze(
        supplier=supplier,
        suppliers=[supplier],
        dependencies=[],
        payment_history=[],
    )

    assert result.criticality_score >= 75