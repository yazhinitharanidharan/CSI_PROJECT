"""
Deterministic cash-flow forecast engine.

This module takes a FinancialState and projects cash over
a requested number of days.
"""

from datetime import timedelta
from decimal import Decimal

from backend.models.schemas import FinancialState, ForecastDay, ForecastResult


class ForecastEngine:
    """
    Creates a deterministic cash forecast from the current
    financial state.
    """

    def __init__(self, state: FinancialState):
        self.state = state

    def _calculate_inflows(self, forecast_date):
        """
        Calculate expected cash inflows for a particular date.

        Only receivables that are not already received are included.
        """

        total = Decimal("0")

        for receivable in self.state.receivables:
            if (
                receivable.expected_date == forecast_date
                and receivable.status != "received"
            ):
                total += Decimal(str(receivable.amount))

        return total

    def _calculate_invoice_outflows(self, forecast_date):
        """
        Calculate supplier invoice payments due on a particular date.
        """

        total = Decimal("0")

        for invoice in self.state.invoices:
            if (
                invoice.due_date == forecast_date
                and invoice.status != "paid"
            ):
                total += Decimal(str(invoice.amount))

        return total

    def _calculate_obligation_outflows(self, forecast_date):
        """
        Calculate recurring business obligations for a particular date.
        """

        total = Decimal("0")

        for obligation in self.state.obligations:
            if obligation.date == forecast_date:
                total += Decimal(str(obligation.total))

        return total

    def forecast(
        self,
        horizon_days: int = 30,
        start_date=None,
    ) -> ForecastResult:
        """
        Generate a deterministic cash forecast.

        Parameters:
            horizon_days:
                Number of days to forecast.

            start_date:
                Date from which forecasting begins.
                If omitted, FinancialState.as_of_date is used.
        """

        if horizon_days <= 0:
            raise ValueError("horizon_days must be greater than zero")

        if start_date is None:
            start_date = self.state.as_of_date

        reserve_requirement = Decimal(
            str(self.state.risk_policy.minimum_reserve)
        )

        projected_cash = Decimal(
            str(self.state.deployable_cash)
        )

        forecast_days = []

        minimum_cash = projected_cash
        minimum_cash_date = start_date

        first_breach_day = None

        for day_number in range(horizon_days):
            forecast_date = start_date + timedelta(days=day_number)

            inflows = self._calculate_inflows(forecast_date)

            invoice_outflows = self._calculate_invoice_outflows(
                forecast_date
            )

            obligation_outflows = self._calculate_obligation_outflows(
                forecast_date
            )

            outflows = invoice_outflows + obligation_outflows

            projected_cash = (
                projected_cash
                + inflows
                - outflows
            )

            reserve_breach = projected_cash < reserve_requirement

            if (
                reserve_breach
                and first_breach_day is None
            ):
                first_breach_day = day_number + 1

            if projected_cash < minimum_cash:
                minimum_cash = projected_cash
                minimum_cash_date = forecast_date

            forecast_days.append(
                ForecastDay(
                    date=forecast_date,
                    projected_cash=projected_cash,
                    inflows=inflows,
                    outflows=outflows,
                )
            )

        reserve_breach = first_breach_day is not None

        if first_breach_day is None:
            survival_horizon_days = horizon_days
        else:
            survival_horizon_days = first_breach_day

        return ForecastResult(
            days=forecast_days,
            minimum_cash=minimum_cash,
            reserve_requirement=reserve_requirement,
            reserve_breach=reserve_breach,
            survival_horizon_days=survival_horizon_days,
            forecast_horizon_days=horizon_days,
            forecast_confidence=Decimal("1.0"),
            scenario_id="base",
            scenario_name="Base",
        )


def generate_forecast(
    state: FinancialState,
    horizon_days: int = 30,
) -> ForecastResult:
    """
    Convenience function for generating a forecast.
    """

    engine = ForecastEngine(state)

    return engine.forecast(
        horizon_days=horizon_days,
        start_date=state.as_of_date,
    )