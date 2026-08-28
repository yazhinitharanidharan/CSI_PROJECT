import unittest
from datetime import date
from decimal import Decimal

from forecast_engine.forecast_engine import generate_forecast
from models.schemas import (
    DailyObligation,
    FinancialState,
    Invoice,
    ObligationItem,
    Receivable,
    RiskPolicy,
)


class TestForecastEngine(unittest.TestCase):

    def create_test_state(self):
        return FinancialState(
            as_of_date=date(2026, 8, 28),
            current_cash=1000.0,
            restricted_cash=0.0,
            protected_cash=0.0,
            deployable_cash=1000.0,

            invoices=[],

            receivables=[],

            obligations=[
                DailyObligation(
                    date=date(2026, 8, 28),
                    items=[
                        ObligationItem(
                            type="Test",
                            amount=200.0,
                        )
                    ],
                    total=200.0,
                )
            ],

            suppliers=[],

            financing_options=[],

            risk_policy=RiskPolicy(
                minimum_reserve=500.0
            ),
        )

    def test_forecast_starts_on_state_date(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=3)

        self.assertEqual(
            result.days[0].date,
            date(2026, 8, 28)
        )

    def test_cash_calculation(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=3)

        self.assertEqual(
            result.days[0].projected_cash,
            Decimal("800.0")
        )

    def test_reserve_breach(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=3)

        self.assertFalse(result.reserve_breach)

    def test_forecast_horizon(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=10)

        self.assertEqual(
            len(result.days),
            10
        )

        self.assertEqual(
            result.forecast_horizon_days,
            10
        )

    def test_minimum_cash(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=3)

        self.assertEqual(
            result.minimum_cash,
            Decimal("800.0")
        )

    def test_reserve_requirement(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=3)

        self.assertEqual(
            result.reserve_requirement,
            Decimal("500.0")
        )

    def test_forecast_metadata(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=3)

        self.assertEqual(
            result.forecast_confidence,
            Decimal("1.0")
        )

        self.assertEqual(
            result.scenario_id,
            "base"
        )

        self.assertEqual(
            result.scenario_name,
            "Base"
        )

    def test_survival_horizon(self):
        state = self.create_test_state()

        result = generate_forecast(state, horizon_days=3)

        self.assertEqual(
            result.survival_horizon_days,
            3
        )


if __name__ == "__main__":
    unittest.main()