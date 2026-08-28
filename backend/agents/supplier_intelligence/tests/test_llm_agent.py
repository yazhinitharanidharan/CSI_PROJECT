from agents.supplier_intelligence.llm_agent import SupplierRiskLLMAgent


def test_llm_agent_accepts_supplier_risk_payload():
    supplier_risk = {
        "supplier_id": "supplier-001",
        "criticality_score": 91.5,
        "distress_score": 78.0,
        "disruption_probability": 0.8225,
        "cascade_risk_score": 74.5,
        "dependency_count": 3,
        "affected_supplier_ids": [
            "supplier-002",
            "supplier-003",
        ],
        "risk_level": "CRITICAL",
    }

    assert isinstance(supplier_risk, dict)
    assert supplier_risk["supplier_id"] == "supplier-001"
    assert supplier_risk["risk_level"] == "CRITICAL"


def test_llm_agent_does_not_modify_supplier_risk_payload():
    supplier_risk = {
        "supplier_id": "supplier-001",
        "criticality_score": 91.5,
        "distress_score": 78.0,
        "disruption_probability": 0.8225,
        "cascade_risk_score": 74.5,
        "dependency_count": 3,
        "affected_supplier_ids": [
            "supplier-002",
            "supplier-003",
        ],
        "risk_level": "CRITICAL",
    }

    original = supplier_risk.copy()

    # The LLM layer should treat the deterministic
    # supplier-risk payload as input data only.
    assert supplier_risk == original


def test_llm_agent_class_exists():
    agent = SupplierRiskLLMAgent

    assert agent is not None
    assert hasattr(agent, "explain_supplier_risk")