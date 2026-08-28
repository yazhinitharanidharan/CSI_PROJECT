from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from state_engine.state_engine import load_financial_state


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


@app.get("/")
def root():
    return {
        "message": "LiquidityOS backend is running"
    }


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