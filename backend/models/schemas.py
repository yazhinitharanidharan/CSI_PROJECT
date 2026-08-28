"""
Pydantic models for the financial state/forecast engine.
These define the shape of every data object used across the system.
"""
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import date


# ---------------------------------------------------------
# Core entities (mirror the JSON files in data/)
# ---------------------------------------------------------

class Supplier(BaseModel):
    supplier_id: str
    name: str
    category: str
    payment_terms_days: int
    reliability_score: float
    average_lead_time_days: int


class Invoice(BaseModel):
    invoice_id: str
    supplier_id: str
    amount: float
    issue_date: date
    due_date: date
    status: str  # "pending" | "paid"


class Receivable(BaseModel):
    receivable_id: str
    customer_name: str
    amount: float
    expected_date: date
    original_expected_date: date
    status: str  # "expected" | "received" | "overdue"
    delay_history: List[dict] = []


class ObligationItem(BaseModel):
    type: str
    amount: float


class DailyObligation(BaseModel):
    date: date
    items: List[ObligationItem]
    total: float


class FinancingOption(BaseModel):
    financing_id: str
    name: str
    type: str
    max_amount: float
    interest_rate_annual: float
    repayment_days: int
    available: bool


class CashPosition(BaseModel):
    current_cash: float
    restricted_cash: float
    protected_cash: float
    as_of_date: date


# ---------------------------------------------------------
# Derived / computed entities
# ---------------------------------------------------------

class ForecastDay(BaseModel):
    date: date
    projected_cash: Decimal
    inflows: Decimal
    outflows: Decimal


class ForecastResult(BaseModel):
    days: List[ForecastDay]
    minimum_cash: Decimal
    reserve_requirement: Decimal
    reserve_breach: bool
    survival_horizon_days: int
    forecast_horizon_days: int
    forecast_confidence: Decimal
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None


class RiskPolicy(BaseModel):
    minimum_reserve: float = 1_00_000
    max_financing_utilization: float = 0.8


# ---------------------------------------------------------
# Request/response models for API endpoints
# ---------------------------------------------------------

class DelayReceivableRequest(BaseModel):
    receivable_id: str
    days: int


class ForecastRequest(BaseModel):
    horizon_days: int = 30


# ---------------------------------------------------------
# Full agent state (as per PRD)
# ---------------------------------------------------------

class FinancialState(BaseModel):
    as_of_date: date

    current_cash: float
    restricted_cash: float
    protected_cash: float
    deployable_cash: float

    invoices: List[Invoice]
    receivables: List[Receivable]
    obligations: List[DailyObligation]
    suppliers: List[Supplier]
    financing_options: List[FinancingOption]

    previous_plan: Optional[dict] = None
    risk_policy: RiskPolicy = RiskPolicy()