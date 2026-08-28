import heapq
from decimal import Decimal
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.state_engine.state_engine import load_financial_state
from backend.forecast_engine.forecast_engine import generate_forecast
from contextlib import asynccontextmanager

from backend.automation.monitor import AutomationMonitor
from backend.agents.supplier_intelligence.agent import SupplierIntelligenceAgent
from backend.agents.supplier_intelligence.models import (
    PaymentHistoryRecord,
    SupplierDependency,
    SupplierProfile,
)

from backend.decision_engine.action_generator import (
    InvoiceInput,
    generate_invoice_actions,
)
from backend.decision_engine.models import (
    ActionType,
    FundingSource,
    FinancingDecision,
    PaymentDecision,
    Plan,
)
from backend.decision_engine.priority_engine import (
    InvoicePriorityInput,
    calculate_urgency,
    re_rank_invoices,
)
from backend.decision_engine.supplier_risk_adapter import (
    consume_supplier_risk,
)
from backend.decision_engine.constraints import (
    validate_plan,
    is_plan_feasible,
)
from backend.decision_engine.scoring import (
    calculate_action_score,
    calculate_plan_score,
    evaluate_plan,
)
from backend.decision_engine.financing_engine import (
    FinancingOption as EngineFinancingOption,
    compare_financing_options,
    select_best_financing_option,
    calculate_financing_cost,
)
from backend.decision_engine.discount_engine import (
    evaluate_discount_action,
)
from backend.decision_engine.penalty_engine import (
    evaluate_penalty_action,
)
automation_monitor = AutomationMonitor(
    poll_seconds=60
)


@asynccontextmanager
async def lifespan(app):
    await automation_monitor.start()

    try:
        yield
    finally:
        await automation_monitor.stop()

app = FastAPI(
    title="LiquidityOS API",
    description="Integrated financial intelligence and decision backend",
    version="1.0.0",
    lifespan=lifespan,
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


# =========================================================
# REQUEST MODELS
# =========================================================

class ForecastRequest(BaseModel):
    horizon_days: int = Field(default=30, gt=0, le=365)


class SupplierRiskRequest(BaseModel):
    supplier: dict[str, Any]
    suppliers: list[dict[str, Any]]
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    payment_history: list[dict[str, Any]] = Field(default_factory=list)


class ReoptimizationRequest(BaseModel):
    event_type: str = Field(
        default="invoice_due_date_advanced",
        min_length=1,
    )
    invoice_id: str
    advance_days: int = Field(default=5, ge=1, le=365)


class FinancingComparisonRequest(BaseModel):
    financing_amount: Decimal = Field(gt=0)
    financing_days: int = Field(default=30, ge=0, le=3650)


class DiscountEvaluationRequest(BaseModel):
    invoice_amount: Decimal = Field(gt=0)
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    discount_deadline: Optional[str] = None
    payment_date: str
    maturity_date: str


class PenaltyEvaluationRequest(BaseModel):
    invoice_amount: Decimal = Field(gt=0)
    due_date: str
    payment_date: str
    penalty_rate: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    permissible_delay_days: int = Field(default=0, ge=0)


class DecisionEvaluationRequest(BaseModel):
    invoice_id: str
    action_type: str
    scheduled_date: Optional[str] = None
    financing_option_id: Optional[str] = None


# =========================================================
# HELPERS
# =========================================================

def _decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _parse_date(value: str):
    from datetime import date
    return date.fromisoformat(value)


def _find_invoice(state, invoice_id: str):
    return next(
        (
            invoice
            for invoice in state.invoices
            if invoice.invoice_id == invoice_id
        ),
        None,
    )


def _available_engine_financing_options(state):
    result = []

    for option in state.financing_options:
        source = FundingSource.BANK

        normalized = option.type.lower()

        if normalized in {
            "supplier",
            "supplier_finance",
            "supplier-finance",
        }:
            source = FundingSource.SUPPLIER_FINANCE
        elif normalized in {
            "bank",
            "credit_line",
            "credit-line",
            "invoice_discounting",
            "term_loan",
            "term-loan",
        }:
            source = FundingSource.BANK
        else:
            continue

        result.append(
            EngineFinancingOption(
                option_id=option.financing_id,
                funding_source=source,
                annual_interest_rate=Decimal(
                    str(option.interest_rate_annual)
                ),
                fixed_fee=Decimal("0"),
                available_limit=Decimal(
                    str(option.max_amount)
                ),
                eligible=option.available,
            )
        )

    return result


def _financing_candidates_for_invoice(state, invoice):
    amount = Decimal(str(invoice.amount))
    days = max(
        0,
        (invoice.due_date - state.as_of_date).days,
    )

    return select_best_financing_option(
        financing_amount=amount,
        financing_days=days,
        options=_available_engine_financing_options(state),
        requested_date=state.as_of_date,
    )


def _build_invoice_input(state, invoice):
    best = _financing_candidates_for_invoice(
        state,
        invoice,
    )

    bank_options = [
        option
        for option in state.financing_options
        if option.available
        and option.type.lower() in {
            "bank",
            "credit_line",
            "credit-line",
            "invoice_discounting",
            "term_loan",
            "term-loan",
        }
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

    bank_id = (
        bank_options[0].financing_id
        if bank_options
        else None
    )
    supplier_id = (
        supplier_options[0].financing_id
        if supplier_options
        else None
    )

    return InvoiceInput(
        invoice_id=invoice.invoice_id,
        amount=Decimal(str(invoice.amount)),
        invoice_date=invoice.issue_date,
        due_date=invoice.due_date,
        verified=True,
        bank_financing_available=bool(bank_options),
        supplier_financing_available=bool(supplier_options),
        bank_financing_option_id=bank_id,
        supplier_financing_option_id=supplier_id,
    ), best


def _action_to_dict(action, financing_evaluation=None):
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
        "discount_value": str(action.discount_value),
        "penalty_cost": str(action.penalty_cost),
        "financing_cost": str(
            financing_evaluation.total_cost
            if financing_evaluation is not None
            else action.financing_cost
        ),
        "net_cost": str(action.net_cost),
    }


def _forecast_to_dict(result):
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


def _supplier_profile_from_shared_supplier(supplier):
    """
    Adapt the shared state supplier model to the Supplier Intelligence
    model.

    The current shared Supplier schema does not contain strategic
    importance, substitutability, or spend concentration. For the
    dashboard's live overview, explicit MVP assumptions are used:
      - strategic importance = payment-term leverage score
      - substitutability = reliability score
      - spend concentration = neutral 50
    The underlying Supplier Intelligence formula remains unchanged.
    """
    strategic_importance = min(
        100.0,
        max(
            0.0,
            float(supplier.payment_terms_days) * 2.0,
        ),
    )

    substitutability = min(
        100.0,
        max(
            0.0,
            float(supplier.reliability_score) * 100.0,
        ),
    )

    return SupplierProfile(
        id=supplier.supplier_id,
        name=supplier.name,
        strategic_importance=strategic_importance,
        substitutability_score=substitutability,
        lead_time_days=supplier.average_lead_time_days,
        payment_terms_days=supplier.payment_terms_days,
        spend_concentration=50.0,
        status="Active",
    )


def _build_default_supplier_risk_context(state):
    profiles = [
        _supplier_profile_from_shared_supplier(supplier)
        for supplier in state.suppliers
    ]

    return profiles, [], []


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "message": "LiquidityOS backend is running",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/api/health")
def health():
    state = load_financial_state()

    return {
        "status": "healthy",
        "invoices": len(state.invoices),
        "suppliers": len(state.suppliers),
        "financing_options": len(
            state.financing_options
        ),
    }


# =========================================================
# FINANCIAL STATE
# =========================================================

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


# =========================================================
# INVOICES
# =========================================================

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


# =========================================================
# SUPPLIERS
# =========================================================

@app.get("/api/suppliers")
def get_suppliers():
    state = load_financial_state()

    return {
        "suppliers": [
            supplier.model_dump(mode="json")
            for supplier in state.suppliers
        ]
    }


# =========================================================
# FORECAST
# =========================================================

@app.post("/api/forecast")
def get_forecast(request: ForecastRequest):
    try:
        state = load_financial_state()

        result = generate_forecast(
            state=state,
            horizon_days=request.horizon_days,
        )

        return _forecast_to_dict(result)

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


# =========================================================
# SUPPLIER INTELLIGENCE
# =========================================================

@app.post("/api/supplier-risk")
def analyze_supplier_risk(
    request: SupplierRiskRequest,
):
    try:
        supplier = SupplierProfile(
            **request.supplier
        )

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

        result = SupplierIntelligenceAgent().analyze(
            supplier=supplier,
            suppliers=suppliers,
            dependencies=dependencies,
            payment_history=payment_history,
        )

        return {
            "risk": result.to_dict(),
            "decision_engine_contract": (
                consume_supplier_risk(
                    result.to_decision_engine_dict()
                )
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


@app.get("/api/supplier-risk/{supplier_id}")
def analyze_supplier_risk_from_state(
    supplier_id: str,
):
    state = load_financial_state()

    supplier = next(
        (
            item
            for item in state.suppliers
            if item.supplier_id == supplier_id
        ),
        None,
    )

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier {supplier_id} not found.",
        )

    profiles, dependencies, payment_history = (
        _build_default_supplier_risk_context(state)
    )

    target_profile = next(
        profile
        for profile in profiles
        if profile.id == supplier_id
    )

    result = SupplierIntelligenceAgent().analyze(
        supplier=target_profile,
        suppliers=profiles,
        dependencies=dependencies,
        payment_history=payment_history,
    )

    return {
        "risk": result.to_dict(),
        "decision_engine_contract": (
            consume_supplier_risk(
                result.to_decision_engine_dict()
            )
        ),
        "data_note": (
            "Live shared supplier data was adapted to the "
            "Supplier Intelligence schema using documented MVP "
            "assumptions because the current financial state "
            "does not include supplier dependency/payment-history feeds."
        ),
    }


# =========================================================
# FINANCING ENGINE
# =========================================================

@app.get("/api/financing/options")
def get_financing_options():
    state = load_financial_state()

    return {
        "options": [
            {
                "financing_id": option.financing_id,
                "name": option.name,
                "type": option.type,
                "max_amount": option.max_amount,
                "interest_rate_annual": option.interest_rate_annual,
                "repayment_days": option.repayment_days,
                "available": option.available,
            }
            for option in state.financing_options
        ]
    }


@app.post("/api/financing/compare")
def compare_financing(
    request: FinancingComparisonRequest,
):
    state = load_financial_state()

    options = _available_engine_financing_options(state)

    evaluations = compare_financing_options(
        financing_amount=request.financing_amount,
        financing_days=request.financing_days,
        options=options,
    )

    best = select_best_financing_option(
        financing_amount=request.financing_amount,
        financing_days=request.financing_days,
        options=options,
    )

    return {
        "evaluations": [
            {
                "option_id": item.option_id,
                "funding_source": item.funding_source.value,
                "eligible": item.eligible,
                "financing_amount": str(
                    item.financing_amount
                ),
                "interest_cost": str(
                    item.interest_cost
                ),
                "fixed_fee": str(item.fixed_fee),
                "total_cost": str(item.total_cost),
                "liquidity_preserved": str(
                    item.liquidity_preserved
                ),
                "effective_cost_rate": str(
                    item.effective_cost_rate
                ),
                "reason": item.reason,
            }
            for item in evaluations
        ],
        "best_option": (
            {
                "option_id": best.option_id,
                "funding_source": best.funding_source.value,
                "total_cost": str(best.total_cost),
                "effective_cost_rate": str(
                    best.effective_cost_rate
                ),
            }
            if best is not None
            else None
        ),
    }


# =========================================================
# DISCOUNT ENGINE
# =========================================================

@app.post("/api/discount/evaluate")
def evaluate_discount(
    request: DiscountEvaluationRequest,
):
    result = evaluate_discount_action(
        invoice_amount=request.invoice_amount,
        discount_rate=request.discount_rate,
        discount_deadline=(
            _parse_date(request.discount_deadline)
            if request.discount_deadline
            else None
        ),
        payment_date=_parse_date(
            request.payment_date
        ),
        maturity_date=_parse_date(
            request.maturity_date
        ),
    )

    return {
        "eligible": result.eligible,
        "discount_value": str(
            result.discount_value
        ),
        "discount_days": result.discount_days,
        "annualized_return": str(
            result.annualized_return
        ),
        "reason": result.reason,
    }


# =========================================================
# PENALTY ENGINE
# =========================================================

@app.post("/api/penalty/evaluate")
def evaluate_penalty(
    request: PenaltyEvaluationRequest,
):
    result = evaluate_penalty_action(
        invoice_amount=request.invoice_amount,
        due_date=_parse_date(request.due_date),
        payment_date=_parse_date(request.payment_date),
        penalty_rate=request.penalty_rate,
        permissible_delay_days=(
            request.permissible_delay_days
        ),
    )

    return {
        "late_days": result.late_days,
        "penalty_amount": str(
            result.penalty_amount
        ),
        "penalty_risk": str(
            result.penalty_risk
        ),
        "past_absolute_deadline": (
            result.past_absolute_deadline
        ),
        "reason": result.reason,
    }


# =========================================================
# DECISION ENGINE — CANDIDATE ACTIONS
# =========================================================

@app.post("/api/decision/actions")
def generate_decision_actions(
    invoice_id: str,
):
    state = load_financial_state()

    invoice = _find_invoice(
        state,
        invoice_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_id} not found.",
        )

    if invoice.status.lower() == "paid":
        raise HTTPException(
            status_code=400,
            detail=f"Invoice {invoice_id} is already paid.",
        )

    invoice_input, best_financing = (
        _build_invoice_input(
            state,
            invoice,
        )
    )

    try:
        actions = generate_invoice_actions(
            invoice_input
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "invoice": {
            "invoice_id": invoice.invoice_id,
            "supplier_id": invoice.supplier_id,
            "amount": invoice.amount,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
            "status": invoice.status,
        },
        "financing_recommendation": (
            {
                "option_id": best_financing.option_id,
                "funding_source": (
                    best_financing.funding_source.value
                ),
                "total_cost": str(
                    best_financing.total_cost
                ),
            }
            if best_financing is not None
            else None
        ),
        "actions": [
            _action_to_dict(
                action,
                best_financing
                if (
                    action.action_type
                    == ActionType.FINANCE
                )
                and best_financing is not None
                else None,
            )
            for action in actions
        ],
    }


# =========================================================
# DECISION ENGINE — PLAN EVALUATION
# =========================================================

@app.post("/api/decision/evaluate")
def evaluate_decision(
    request: DecisionEvaluationRequest,
):
    state = load_financial_state()

    invoice = _find_invoice(
        state,
        request.invoice_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {request.invoice_id} not found.",
        )

    if invoice.status.lower() == "paid":
        raise HTTPException(
            status_code=400,
            detail=f"Invoice {request.invoice_id} is already paid.",
        )

    invoice_input, best_financing = (
        _build_invoice_input(
            state,
            invoice,
        )
    )

    actions = generate_invoice_actions(
        invoice_input
    )

    normalized_action_type = (
        request.action_type.lower()
    )

    selected_action = next(
        (
            action
            for action in actions
            if action.action_type.value
            == normalized_action_type
        ),
        None,
    )

    if selected_action is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Action '{request.action_type}' is not "
                f"available for {request.invoice_id}."
            ),
        )

    scheduled_date = (
        _parse_date(request.scheduled_date)
        if request.scheduled_date
        else selected_action.scheduled_date
    )

    payment_decisions = []
    financing_decisions = []

    if selected_action.action_type == ActionType.FINANCE:
        financing_option_id = (
            request.financing_option_id
            or selected_action.financing_option_id
        )

        if not financing_option_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "A financing option is required "
                    "for a financing action."
                ),
            )

        option = next(
            (
                item
                for item in state.financing_options
                if item.financing_id
                == financing_option_id
                and item.available
            ),
            None,
        )

        if option is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Financing option "
                    f"{financing_option_id} is unavailable."
                ),
            )

        amount = Decimal(
            str(invoice.amount)
        )

        financing_cost = calculate_financing_cost(
            principal=amount,
            annual_interest_rate=Decimal(
                str(option.interest_rate_annual)
            ),
            financing_days=max(
                0,
                option.repayment_days,
            ),
        )

        funding_source = (
            FundingSource.SUPPLIER_FINANCE
            if option.type.lower()
            in {
                "supplier",
                "supplier_finance",
                "supplier-finance",
            }
            else FundingSource.BANK
        )

        financing_decisions.append(
            FinancingDecision(
                financing_option_id=(
                    option.financing_id
                ),
                funding_source=funding_source,
                amount=amount,
                scheduled_date=scheduled_date,
                interest_cost=financing_cost,
                financing_cost=financing_cost,
                remaining_limit=(
                    Decimal(str(option.max_amount))
                    - amount
                ),
            )
        )

        payment_decisions.append(
            PaymentDecision(
                invoice_id=invoice.invoice_id,
                action_type=ActionType.PAY,
                scheduled_date=scheduled_date,
                amount=amount,
                funding_source=funding_source,
                financing_cost=financing_cost,
            )
        )

    elif selected_action.action_type == ActionType.RETAIN:
        payment_decisions = []

    else:
        payment_decisions.append(
            PaymentDecision(
                invoice_id=invoice.invoice_id,
                action_type=selected_action.action_type,
                scheduled_date=scheduled_date,
                amount=Decimal(
                    str(invoice.amount)
                ),
                funding_source=selected_action.funding_source,
            )
        )

    plan = Plan(
        plan_id=(
            f"plan-{invoice.invoice_id}-"
            f"{normalized_action_type}"
        ),
        payment_decisions=tuple(
            payment_decisions
        ),
        financing_decisions=tuple(
            financing_decisions
        ),
        retained_cash=(
            Decimal(str(invoice.amount))
            if selected_action.action_type
            == ActionType.RETAIN
            else Decimal("0")
        ),
    )

    forecast_result = generate_forecast(
        state=state,
        horizon_days=30,
    )

    constraint_results = validate_plan(
        plan,
        invoices=state.invoices,
        mandatory_obligations=[],
        critical_supplier_invoice_ids=[],
        forecast_result=forecast_result,
        initial_deployable_cash=Decimal(
            str(state.deployable_cash)
        ),
        financing_limits={
            option.financing_id: Decimal(
                str(option.max_amount)
            )
            for option in state.financing_options
            if option.available
        },
        eligible_financing_sources={
            FundingSource.BANK,
            FundingSource.SUPPLIER_FINANCE,
        },
    )

    feasible = is_plan_feasible(
        constraint_results
    )

    metrics = evaluate_plan(
        plan,
        forecast_result=forecast_result,
    )

    score = calculate_plan_score(
        plan
    )

    action_score = calculate_action_score(
        selected_action
    )

    return {
        "invoice_id": invoice.invoice_id,
        "selected_action": _action_to_dict(
            selected_action,
            best_financing
            if selected_action.action_type
            == ActionType.FINANCE
            else None,
        ),
        "plan": plan.to_dict(),
        "feasible": feasible,
        "score": str(score),
        "action_score": str(action_score),
        "metrics": {
            "total_cost": str(metrics.total_cost),
            "financing_cost": str(
                metrics.financing_cost
            ),
            "late_payment_penalty": str(
                metrics.late_payment_penalty
            ),
            "discount_savings": str(
                metrics.discount_savings
            ),
            "supplier_risk_cost": str(
                metrics.supplier_risk_cost
            ),
            "liquidity_shortfall_cost": str(
                metrics.liquidity_shortfall_cost
            ),
            "minimum_projected_cash": str(
                metrics.minimum_projected_cash
            ),
            "liquidity_reserve": str(
                metrics.liquidity_reserve
            ),
            "liquidity_survival_horizon_days": (
                metrics.liquidity_survival_horizon_days
            ),
            "reserve_violations": (
                metrics.reserve_violations
            ),
        },
        "constraints": [
            {
                "constraint": item.constraint,
                "valid": item.valid,
                "reason": item.reason,
                "details": item.details,
            }
            for item in constraint_results
        ],
    }


# =========================================================
# EVENT-DRIVEN RE-OPTIMIZATION
# =========================================================

@app.post("/api/reoptimize")
def reoptimize(request: ReoptimizationRequest):
    try:
        state = load_financial_state()

        target = _find_invoice(
            state,
            request.invoice_id,
        )

        if target is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Invoice {request.invoice_id} not found."
                ),
            )

        if target.status.lower() == "paid":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invoice {request.invoice_id} is already paid."
                ),
            )

        def build_inputs(apply_event: bool):
            result = []

            for invoice in state.invoices:
                if invoice.status.lower() == "paid":
                    continue

                days_until_due = (
                    invoice.due_date
                    - state.as_of_date
                ).days

                financing_cost = Decimal("0")

                eligible = [
                    option
                    for option
                    in state.financing_options
                    if option.available
                    and Decimal(
                        str(option.max_amount)
                    ) >= Decimal(
                        str(invoice.amount)
                    )
                ]

                if eligible:
                    amount = Decimal(
                        str(invoice.amount)
                    )

                    costs = []

                    for option in eligible:
                        costs.append(
                            calculate_financing_cost(
                                principal=amount,
                                annual_interest_rate=Decimal(
                                    str(
                                        option.interest_rate_annual
                                    )
                                ),
                                financing_days=max(
                                    0,
                                    option.repayment_days,
                                ),
                            )
                        )

                    financing_cost = min(costs)

                if (
                    apply_event
                    and invoice.invoice_id
                    == request.invoice_id
                ):
                    if (
                        request.event_type
                        != "invoice_due_date_advanced"
                    ):
                        raise ValueError(
                            "Unsupported event_type. "
                            "Supported event_type: "
                            "invoice_due_date_advanced."
                        )

                    days_until_due -= (
                        request.advance_days
                    )

                urgency = calculate_urgency(
                    days_until_due=days_until_due,
                    permissible_delay_days=0,
                )

                result.append(
                    InvoicePriorityInput(
                        invoice_id=invoice.invoice_id,
                        discount_value=Decimal("0"),
                        financing_cost=financing_cost,
                        penalty_risk=Decimal("0"),
                        supplier_criticality=Decimal("0"),
                        supplier_liquidity_need=Decimal("0"),
                        urgency=urgency,
                    )
                )

            return result

        before_queue = re_rank_invoices(
            build_inputs(False)
        )

        after_queue = re_rank_invoices(
            build_inputs(True)
        )

        before = []

        while before_queue:
            negative_score, invoice_id, priority = (
                heapq.heappop(before_queue)
            )

            before.append(
                {
                    "invoice_id": invoice_id,
                    "score": str(-negative_score),
                    "urgency": str(
                        priority.urgency
                    ),
                    "factors": {
                        key: str(value)
                        for key, value
                        in priority.factors.items()
                    },
                }
            )

        after = []

        while after_queue:
            negative_score, invoice_id, priority = (
                heapq.heappop(after_queue)
            )

            after.append(
                {
                    "invoice_id": invoice_id,
                    "score": str(-negative_score),
                    "urgency": str(
                        priority.urgency
                    ),
                    "factors": {
                        key: str(value)
                        for key, value
                        in priority.factors.items()
                    },
                }
            )

        before_rank = {
            item["invoice_id"]: index + 1
            for index, item in enumerate(before)
        }

        after_rank = {
            item["invoice_id"]: index + 1
            for index, item in enumerate(after)
        }

        changes = []

        for invoice_id, new_rank in after_rank.items():
            old_rank = before_rank[invoice_id]

            if old_rank != new_rank:
                changes.append(
                    {
                        "invoice_id": invoice_id,
                        "previous_rank": old_rank,
                        "new_rank": new_rank,
                        "rank_change": (
                            old_rank - new_rank
                        ),
                    }
                )

        target_before = next(
            item
            for item in before
            if item["invoice_id"]
            == request.invoice_id
        )

        target_after = next(
            item
            for item in after
            if item["invoice_id"]
            == request.invoice_id
        )

        return {
            "status": "reoptimized",
            "event": {
                "type": request.event_type,
                "invoice_id": request.invoice_id,
                "advance_days": request.advance_days,
                "description": (
                    f"Due date for "
                    f"{request.invoice_id} advanced by "
                    f"{request.advance_days} days."
                ),
            },
            "target_invoice": {
                "before": target_before,
                "after": target_after,
            },
            "before": before,
            "after": after,
            "changes": changes,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Re-optimization failed: {exc}",
        ) from exc
# =========================================================
# AUTOMATION
# =========================================================

@app.get("/api/automation/status")
def automation_status():
    return automation_monitor.status()


@app.post("/api/automation/check")
async def automation_check():
    result = await automation_monitor.check_once()

    return {
        "triggered": result is not None,
        "result": result,
        "status": automation_monitor.status(),
    }


@app.post("/api/automation/start")
async def automation_start():
    await automation_monitor.start()

    return {
        "status": "started",
        "automation": automation_monitor.status(),
    }


@app.post("/api/automation/stop")
async def automation_stop():
    await automation_monitor.stop()

    return {
        "status": "stopped",
        "automation": automation_monitor.status(),
    }