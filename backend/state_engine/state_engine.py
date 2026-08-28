"""
Financial state loader.

This module loads the synthetic financial data from JSON files,
validates it using the Pydantic models, calculates deployable cash,
and builds a single FinancialState object.
"""

import json
from pathlib import Path

from models.schemas import (
    CashPosition,
    FinancialState,
    FinancingOption,
    Invoice,
    Receivable,
    DailyObligation,
    Supplier,
)


class FinancialStateLoader:
    """
    Loads all financial data and builds the application's FinancialState.
    """

    def __init__(self, data_directory: str | Path | None = None):
        """
        Create a state loader.

        If no data directory is supplied, use:
        backend/data/
        """

        if data_directory is None:
            # state_engine.py is inside:
            # backend/state_engine/
            #
            # parent       = state_engine/
            # parent.parent = backend/
            self.data_directory = (
                Path(__file__).resolve().parent.parent / "data"
            )
        else:
            self.data_directory = Path(data_directory)

    def _load_json(self, filename: str):
        """
        Read one JSON file and return the decoded Python object.
        """

        file_path = self.data_directory / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Financial data file not found: {file_path}"
            )

        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def load_suppliers(self) -> list[Supplier]:
        """Load and validate supplier records."""

        data = self._load_json("suppliers.json")

        return [Supplier(**item) for item in data]

    def load_invoices(self) -> list[Invoice]:
        """Load and validate invoice records."""

        data = self._load_json("invoices.json")

        return [Invoice(**item) for item in data]

    def load_receivables(self) -> list[Receivable]:
        """Load and validate receivable records."""

        data = self._load_json("receivables.json")

        return [Receivable(**item) for item in data]

    def load_obligations(self) -> list[DailyObligation]:
        """Load and validate daily obligation records."""

        data = self._load_json("obligations.json")

        return [DailyObligation(**item) for item in data]

    def load_financing_options(self) -> list[FinancingOption]:
        """Load and validate financing options."""

        data = self._load_json("financing.json")

        return [FinancingOption(**item) for item in data]

    def load_cash(self) -> CashPosition:
        """Load and validate the current cash position."""

        data = self._load_json("cash.json")

        return CashPosition(**data)

    def build_state(self) -> FinancialState:
        """
        Load all financial data and construct the complete FinancialState.
        """

        cash = self.load_cash()

        suppliers = self.load_suppliers()
        invoices = self.load_invoices()
        receivables = self.load_receivables()
        obligations = self.load_obligations()
        financing_options = self.load_financing_options()

        deployable_cash = (
            cash.current_cash
            - cash.restricted_cash
            - cash.protected_cash
        )

        return FinancialState(
            as_of_date=cash.as_of_date,
            current_cash=cash.current_cash,
            restricted_cash=cash.restricted_cash,
            protected_cash=cash.protected_cash,
            deployable_cash=deployable_cash,
            invoices=invoices,
            receivables=receivables,
            obligations=obligations,
            suppliers=suppliers,
            financing_options=financing_options,
        )


def load_financial_state() -> FinancialState:
    """
    Convenience function used by the rest of the application.

    Example:

        state = load_financial_state()
    """

    loader = FinancialStateLoader()
    return loader.build_state()