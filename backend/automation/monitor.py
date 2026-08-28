"""
Background financial automation monitor for LiquidityOS.

The monitor watches the repository's current financial state. It does not
invent events or mutate source data. When the underlying state changes, it
automatically runs the existing Forecast Engine, Supplier Intelligence,
priority/re-ranking engine, and candidate-action generator, then exposes the
latest result to the API/dashboard.
"""

import asyncio
import hashlib
import heapq
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from backend.state_engine.state_engine import load_financial_state
from backend.forecast_engine.forecast_engine import generate_forecast

from backend.agents.supplier_intelligence.agent import (
    SupplierIntelligenceAgent,
)
from backend.agents.supplier_intelligence.models import (
    SupplierProfile,
)

from backend.decision_engine.action_generator import (
    InvoiceInput,
    generate_invoice_actions,
)
from backend.decision_engine.priority_engine import (
    InvoicePriorityInput,
    calculate_urgency,
    re_rank_invoices,
)
from backend.decision_engine.financing_engine import (
    calculate_financing_cost,
)


class AutomationMonitor:
    def __init__(self, poll_seconds: int = 60) -> None:
        self.poll_seconds = max(10, poll_seconds)
        self.running = False
        self.task: Optional[asyncio.Task] = None

        self._previous_snapshot: Optional[dict[str, Any]] = None
        self._previous_fingerprint: Optional[str] = None

        self.last_check: Optional[str] = None
        self.last_event: Optional[dict[str, Any]] = None
        self.last_result: Optional[dict[str, Any]] = None
        self.last_error: Optional[str] = None

    # ---------------------------------------------------------
    # Snapshot / change detection
    # ---------------------------------------------------------

    def _supplier_snapshot(self, supplier: Any) -> dict[str, Any]:
        return {
            "supplier_id": supplier.supplier_id,
            "name": supplier.name,
            "category": supplier.category,
            "reliability_score": supplier.reliability_score,
            "average_lead_time_days": supplier.average_lead_time_days,
            "payment_terms_days": supplier.payment_terms_days,
        }

    def _snapshot(self, state: Any) -> dict[str, Any]:
        return {
            "as_of_date": str(state.as_of_date),
            "current_cash": str(state.current_cash),
            "restricted_cash": str(state.restricted_cash),
            "protected_cash": str(state.protected_cash),
            "deployable_cash": str(state.deployable_cash),
            "invoices": [
                {
                    "invoice_id": invoice.invoice_id,
                    "supplier_id": invoice.supplier_id,
                    "amount": str(invoice.amount),
                    "issue_date": str(invoice.issue_date),
                    "due_date": str(invoice.due_date),
                    "status": invoice.status,
                }
                for invoice in state.invoices
            ],
            "suppliers": [
                self._supplier_snapshot(supplier)
                for supplier in state.suppliers
            ],
            "financing_options": [
                {
                    "financing_id": option.financing_id,
                    "type": option.type,
                    "max_amount": str(option.max_amount),
                    "interest_rate_annual": str(
                        option.interest_rate_annual
                    ),
                    "repayment_days": option.repayment_days,
                    "available": option.available,
                }
                for option in state.financing_options
            ],
        }

    def _fingerprint(self, snapshot: dict[str, Any]) -> str:
        encoded = json.dumps(
            snapshot,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _detect_event(
        self,
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        prev_invoices = {
            item["invoice_id"]: item
            for item in previous.get("invoices", [])
        }
        curr_invoices = {
            item["invoice_id"]: item
            for item in current.get("invoices", [])
        }

        for invoice_id, current_invoice in curr_invoices.items():
            previous_invoice = prev_invoices.get(invoice_id)

            if previous_invoice is None:
                return {
                    "type": "invoice_added",
                    "invoice_id": invoice_id,
                    "description": (
                        f"New invoice {invoice_id} was detected."
                    ),
                }

            if (
                current_invoice["due_date"]
                != previous_invoice["due_date"]
            ):
                return {
                    "type": "invoice_due_date_changed",
                    "invoice_id": invoice_id,
                    "previous_due_date": previous_invoice["due_date"],
                    "new_due_date": current_invoice["due_date"],
                    "description": (
                        f"Invoice {invoice_id} due date changed."
                    ),
                }

            if current_invoice["status"] != previous_invoice["status"]:
                return {
                    "type": "invoice_status_changed",
                    "invoice_id": invoice_id,
                    "previous_status": previous_invoice["status"],
                    "new_status": current_invoice["status"],
                    "description": (
                        f"Invoice {invoice_id} status changed from "
                        f"{previous_invoice['status']} to "
                        f"{current_invoice['status']}."
                    ),
                }

            if current_invoice["amount"] != previous_invoice["amount"]:
                return {
                    "type": "invoice_amount_changed",
                    "invoice_id": invoice_id,
                    "previous_amount": previous_invoice["amount"],
                    "new_amount": current_invoice["amount"],
                    "description": (
                        f"Invoice {invoice_id} amount changed."
                    ),
                }

        prev_suppliers = {
            item["supplier_id"]: item
            for item in previous.get("suppliers", [])
        }
        curr_suppliers = {
            item["supplier_id"]: item
            for item in current.get("suppliers", [])
        }

        for supplier_id, current_supplier in curr_suppliers.items():
            previous_supplier = prev_suppliers.get(supplier_id)
            if previous_supplier is not None and current_supplier != previous_supplier:
                return {
                    "type": "supplier_state_changed",
                    "supplier_id": supplier_id,
                    "description": (
                        f"Supplier {supplier_id} data changed."
                    ),
                }

        if (
            current.get("financing_options")
            != previous.get("financing_options")
        ):
            return {
                "type": "financing_conditions_changed",
                "description": (
                    "Available financing conditions changed."
                ),
            }

        for field in (
            "current_cash",
            "restricted_cash",
            "protected_cash",
            "deployable_cash",
        ):
            if current.get(field) != previous.get(field):
                return {
                    "type": "liquidity_state_changed",
                    "field": field,
                    "previous_value": previous.get(field),
                    "new_value": current.get(field),
                    "description": (
                        f"Financial state field {field} changed."
                    ),
                }

        return {
            "type": "financial_state_changed",
            "description": "A financial-state change was detected.",
        }

    # ---------------------------------------------------------
    # Engine inputs
    # ---------------------------------------------------------

    def _priority_inputs(self, state: Any) -> list[InvoicePriorityInput]:
        result: list[InvoicePriorityInput] = []

        for invoice in state.invoices:
            if str(invoice.status).lower() == "paid":
                continue

            days_until_due = (
                invoice.due_date - state.as_of_date
            ).days

            urgency = calculate_urgency(
                days_until_due=days_until_due,
                permissible_delay_days=0,
            )

            financing_cost = Decimal("0")
            amount = Decimal(str(invoice.amount))

            eligible = [
                option
                for option in state.financing_options
                if option.available
                and Decimal(str(option.max_amount)) >= amount
            ]

            if eligible:
                financing_cost = min(
                    calculate_financing_cost(
                        principal=amount,
                        annual_interest_rate=Decimal(
                            str(option.interest_rate_annual)
                        ),
                        financing_days=max(
                            0,
                            option.repayment_days,
                        ),
                    )
                    for option in eligible
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

    def _supplier_risk(self, state: Any) -> list[dict[str, Any]]:
        profiles = []

        for supplier in state.suppliers:
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

            profiles.append(
                SupplierProfile(
                    id=supplier.supplier_id,
                    name=supplier.name,
                    strategic_importance=strategic_importance,
                    substitutability_score=substitutability,
                    lead_time_days=supplier.average_lead_time_days,
                    payment_terms_days=supplier.payment_terms_days,
                    spend_concentration=50.0,
                    status="Active",
                )
            )

        result = []

        for profile in profiles:
            analysis = SupplierIntelligenceAgent().analyze(
                supplier=profile,
                suppliers=profiles,
                dependencies=[],
                payment_history=[],
            )

            result.append(
                {
                    "supplier_id": profile.id,
                    "risk": analysis.to_dict(),
                    "decision_engine_contract": (
                        analysis.to_decision_engine_dict()
                    ),
                }
            )

        return result

    # ---------------------------------------------------------
    # Pipeline
    # ---------------------------------------------------------

    def _run_pipeline(
        self,
        state: Any,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        forecast = generate_forecast(
            state=state,
            horizon_days=30,
        )

        priority_queue = re_rank_invoices(
            self._priority_inputs(state)
        )

        priorities = []

        while priority_queue:
            negative_score, invoice_id, priority = (
                heapq.heappop(priority_queue)
            )

            priorities.append(
                {
                    "rank": len(priorities) + 1,
                    "invoice_id": invoice_id,
                    "score": str(-negative_score),
                    "urgency": str(priority.urgency),
                    "factors": {
                        key: str(value)
                        for key, value in priority.factors.items()
                    },
                }
            )

        candidate_actions = []

        if priorities:
            top_invoice_id = priorities[0]["invoice_id"]

            invoice = next(
                (
                    item
                    for item in state.invoices
                    if item.invoice_id == top_invoice_id
                ),
                None,
            )

            if invoice is not None:
                amount = Decimal(str(invoice.amount))

                bank = [
                    option
                    for option in state.financing_options
                    if option.available
                    and option.type.lower()
                    in {
                        "bank",
                        "credit_line",
                        "credit-line",
                        "invoice_discounting",
                        "term_loan",
                        "term-loan",
                    }
                ]

                supplier_finance = [
                    option
                    for option in state.financing_options
                    if option.available
                    and option.type.lower()
                    in {
                        "supplier",
                        "supplier_finance",
                        "supplier-finance",
                    }
                ]

                invoice_input = InvoiceInput(
                    invoice_id=invoice.invoice_id,
                    amount=amount,
                    invoice_date=invoice.issue_date,
                    due_date=invoice.due_date,
                    verified=True,
                    bank_financing_available=bool(bank),
                    supplier_financing_available=bool(
                        supplier_finance
                    ),
                    bank_financing_option_id=(
                        bank[0].financing_id
                        if bank
                        else None
                    ),
                    supplier_financing_option_id=(
                        supplier_finance[0].financing_id
                        if supplier_finance
                        else None
                    ),
                )

                candidate_actions = [
                    {
                        "action_type": action.action_type.value,
                        "scheduled_date": (
                            action.scheduled_date.isoformat()
                        ),
                        "amount": str(action.amount),
                        "funding_source": (
                            action.funding_source.value
                            if action.funding_source
                            else None
                        ),
                    }
                    for action in generate_invoice_actions(
                        invoice_input
                    )
                ]

        supplier_risk = self._supplier_risk(state)

        return {
            "event": event,
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "forecast": {
                "minimum_cash": str(
                    forecast.minimum_cash
                ),
                "reserve_requirement": str(
                    forecast.reserve_requirement
                ),
                "reserve_breach": forecast.reserve_breach,
                "survival_horizon_days": (
                    forecast.survival_horizon_days
                ),
            },
            "priorities": priorities[:10],
            "top_priority": (
                priorities[0]
                if priorities
                else None
            ),
            "candidate_actions": candidate_actions,
            "supplier_risk": supplier_risk,
        }

    # ---------------------------------------------------------
    # Public monitor API
    # ---------------------------------------------------------

    async def check_once(self) -> Optional[dict[str, Any]]:
        state = load_financial_state()
        snapshot = self._snapshot(state)
        fingerprint = self._fingerprint(snapshot)

        self.last_check = datetime.now(
            timezone.utc
        ).isoformat()
        self.last_error = None

        if self._previous_fingerprint is None:
            self._previous_snapshot = snapshot
            self._previous_fingerprint = fingerprint
            return None

        if fingerprint == self._previous_fingerprint:
            return None

        event = self._detect_event(
            self._previous_snapshot or {},
            snapshot,
        )

        if event is None:
            event = {
                "type": "financial_state_changed",
                "description": (
                    "A financial-state change was detected."
                ),
            }

        result = self._run_pipeline(state, event)

        self.last_event = event
        self.last_result = result

        self._previous_snapshot = snapshot
        self._previous_fingerprint = fingerprint

        return result

    async def _loop(self) -> None:
        self.running = True

        while self.running:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.last_error = str(exc)

            await asyncio.sleep(self.poll_seconds)

        self.running = False

    async def start(self) -> None:
        if self.running:
            return

        state = load_financial_state()
        snapshot = self._snapshot(state)

        self._previous_snapshot = snapshot
        self._previous_fingerprint = self._fingerprint(snapshot)

        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False

        if self.task is not None:
            self.task.cancel()

            try:
                await self.task
            except asyncio.CancelledError:
                pass

            self.task = None

    def status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "poll_seconds": self.poll_seconds,
            "last_check": self.last_check,
            "last_event": self.last_event,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }
