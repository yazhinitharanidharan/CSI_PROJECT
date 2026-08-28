from datetime import date
from decimal import Decimal
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.state_engine.state_engine import load_financial_state

from backend.forecast_engine.forecast_engine import (
    generate_forecast,
)

from backend.agents.supplier_intelligence.agent import (
    SupplierIntelligenceAgent,
)
from backend.agents.supplier_intelligence.models import (
    PaymentHistoryRecord,
    SupplierDependency,
    SupplierProfile,
)

from backend.decision_engine.action_generator import (
    InvoiceInput,
    generate_invoice_actions,
)
from backend.decision_engine.priority_engine import (
    InvoicePriorityInput,
    re_rank_invoices,
)

app = FastAPI(
    title="LiquidityOS API",
    description="Financial intelligence backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------


class ForecastRequest(BaseModel):
    horizon_days: int = Field(default=30, gt=0, le=365)


class SupplierRiskRequest(BaseModel):
    supplier: dict[str, Any]
    suppliers: list[dict[str, Any]]
    dependencies: list[dict[str, Any]] = []
    payment_history: list[dict[str, Any]] = []


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def action_to_dict(action) -> dict[str, Any]:
    return {
        "invoice_id": action.invoice_id,
        "action_type": action.action_type.value,
        "scheduled_date": action.scheduled_date.isoformat(),
        "amount": str(action.amount),
        "funding_source": (
            action.funding_source.value
            if action.funding_source is not None
            else None
        ),
        "financing_option_id": action.financing_option_id,
    }


def forecast_to_dict(result) -> dict[str, Any]:
    return {
        "days": [
            {
                "date": day.date.isoformat(),
                "projected_cash": str(day.projected_cash),
                "inflows": str(day.inflows),
                "outflows": str(day.outflows),
            }
            for day in result.days
        ],
        "minimum_cash": str(result.minimum_cash),
        "reserve_requirement": str(result.reserve_requirement),
        "reserve_breach": result.reserve_breach,
        "survival_horizon_days": result.survival_horizon_days,
        "forecast_horizon_days": result.forecast_horizon_days,
        "forecast_confidence": str(result.forecast_confidence),
        "scenario_id": result.scenario_id,
        "scenario_name": result.scenario_name,
    }


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------


@app.get("/")
def root():
    return {
        "message": "LiquidityOS backend is running",
        "status": "healthy",
    }


# ---------------------------------------------------------
# Financial State
# ---------------------------------------------------------


@app.get("/api/financial-state")
def get_financial_state():
    state = load_financial_state()

    return {
        "as_of_date": state.as_of_date,
        "current_cash": state.current_cash,
        "restricted_cash": state.restricted_cash,
        "protected_cash": state.protected_cash,
        "deployable_cash": state.deployable_cash,
        "invoice_count": len(state.invoices),
        "receivable_count": len(state.receivables),
        "obligation_count": len(state.obligations),
    }


# ---------------------------------------------------------
# Suppliers
# ---------------------------------------------------------


@app.get("/api/suppliers")
def get_suppliers():
    state = load_financial_state()

    return {
        "suppliers": [
            supplier.model_dump(mode="json")
            for supplier in state.suppliers
        ]
    }


# ---------------------------------------------------------
# Forecast
# ---------------------------------------------------------


@app.post("/api/forecast")
def get_forecast(request: ForecastRequest):
    try:
        state = load_financial_state()

        result = generate_forecast(
            state=state,
            horizon_days=request.horizon_days,
        )

        return forecast_to_dict(result)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Forecast generation failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Supplier Intelligence
# ---------------------------------------------------------


@app.post("/api/supplier-risk")
def analyze_supplier_risk(request: SupplierRiskRequest):
    try:
        supplier = SupplierProfile(**request.supplier)

        suppliers = [
            SupplierProfile(**item)
            for item in request.suppliers
        ]

        dependencies = [
            SupplierDependency(**item)
            for item in request.dependencies
        ]

        payment_history = [
            PaymentHistoryRecord(**item)
            for item in request.payment_history
        ]

        agent = SupplierIntelligenceAgent()

        result = agent.analyze(
            supplier=supplier,
            suppliers=suppliers,
            dependencies=dependencies,
            payment_history=payment_history,
        )

        return {
            "risk": result.to_dict(),
            "decision_engine_contract": (
                result.to_decision_engine_dict()
            ),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Supplier analysis failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Decision Engine — Candidate Actions
# ---------------------------------------------------------
@app.get("/api/invoices")
def get_invoices():
    state = load_financial_state()

    return {
        "invoices": [
            {
                "invoice_id": invoice.invoice_id,
                "supplier_id": invoice.supplier_id,
                "amount": invoice.amount,
                "issue_date": invoice.issue_date,
                "due_date": invoice.due_date,
                "status": invoice.status,
            }
            for invoice in state.invoices
        ]
    }

@app.post("/api/decision/actions")
def generate_decision_actions(invoice_id: str):
    state = load_financial_state()

    invoice = next(
        (
            item
            for item in state.invoices
            if item.invoice_id == invoice_id
        ),
        None,
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_id} not found.",
        )

    bank_options = [
        option
        for option in state.financing_options
        if option.available
        and option.type.lower() == "bank"
    ]

    supplier_options = [
        option
        for option in state.financing_options
        if option.available
        and option.type.lower() in {
            "supplier",
            "supplier_finance",
            "supplier-finance",
        }
    ]

    invoice_input = InvoiceInput(
        invoice_id=invoice.invoice_id,
        amount=Decimal(str(invoice.amount)),
        invoice_date=invoice.issue_date,
        due_date=invoice.due_date,
        verified=True,
        bank_financing_available=bool(bank_options),
        supplier_financing_available=bool(supplier_options),
        bank_financing_option_id=(
            bank_options[0].financing_id
            if bank_options
            else None
        ),
        supplier_financing_option_id=(
            supplier_options[0].financing_id
            if supplier_options
            else None
        ),
    )

    actions = generate_invoice_actions(invoice_input)

    return {
        "invoice": {
            "invoice_id": invoice.invoice_id,
            "supplier_id": invoice.supplier_id,
            "amount": invoice.amount,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
            "status": invoice.status,
        },
        "actions": [
            action_to_dict(action)
            for action in actions
        ],
    }
@app.post("/api/reoptimize")
def reoptimize():
    try:
        state = load_financial_state()

        priority_inputs = []

        for invoice in state.invoices:
            if invoice.status.lower() == "paid":
                continue

            # Calculate basic urgency from the invoice due date.
            days_until_due = (
                invoice.due_date - state.as_of_date
            ).days

            urgency = Decimal(
                max(0, 30 - days_until_due)
            )

            priority_inputs.append(
                InvoicePriorityInput(
                    invoice_id=invoice.invoice_id,
                    discount_value=Decimal("0"),
                    financing_cost=Decimal("0"),
                    penalty_risk=Decimal("0"),
                    supplier_criticality=Decimal("0"),
                    supplier_liquidity_need=Decimal("0"),
                    urgency=urgency,
                )
            )

        ranked = re_rank_invoices(priority_inputs)

        priorities = []

        for score, invoice_id, priority in ranked:
            priorities.append(
                {
                    "invoice_id": invoice_id,
                    "score": str(score),
                    "priority": {
    key: (
        str(value)
        if isinstance(value, Decimal)
        else value
    )
    for key, value in vars(priority).items()
},
                }
            )

        return {
            "status": "reoptimized",
            "as_of_date": state.as_of_date,
            "invoice_count": len(priorities),
            "priorities": priorities,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Re-optimization failed: {exc}",
        ) from exc