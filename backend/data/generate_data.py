"""
Generates synthetic data for the financial state/forecast engine.
Run this once to populate data/*.json
"""
import json
import random
from datetime import date, timedelta

random.seed(42)  # reproducible output

TODAY = date.today()

def d(offset_days: int) -> str:
    """Return an ISO date string offset from today."""
    return (TODAY + timedelta(days=offset_days)).isoformat()

# ---------------------------------------------------------
# 1. Suppliers (15)
# ---------------------------------------------------------
SUPPLIER_NAMES = [
    "Shree Metals Pvt Ltd", "Ganesh Alloys", "Coastal Copper Traders",
    "Vandana Steel Corp", "Murugan Scrap Industries", "Chennai Metal Works",
    "Bharat Recycling Co", "Sri Balaji Ferrous", "Om Sakthi Non-Ferrous",
    "Kaveri Metal Exports", "SS Industrial Supplies", "Tamil Nadu Copper Mills",
    "Anand Metal Traders", "Velan Aluminium Co", "Sundar Industrial Corp"
]

suppliers = []
for i, name in enumerate(SUPPLIER_NAMES, start=1):
    suppliers.append({
        "supplier_id": f"S{i:03d}",
        "name": name,
        "category": random.choice(["Aluminium", "Copper", "Mixed Scrap"]),
        "payment_terms_days": random.choice([15, 30, 45, 60]),
        "reliability_score": round(random.uniform(0.7, 0.99), 2),
        "average_lead_time_days": random.randint(2, 10),
    })

# ---------------------------------------------------------
# 2. Invoices (30) - money the business OWES suppliers
# ---------------------------------------------------------
invoices = []
for i in range(1, 31):
    supplier = random.choice(suppliers)
    issue_offset = random.randint(-20, 5)
    due_offset = issue_offset + supplier["payment_terms_days"]
    amount = random.randint(50_000, 8_00_000)
    invoices.append({
        "invoice_id": f"INV{i:03d}",
        "supplier_id": supplier["supplier_id"],
        "amount": amount,
        "issue_date": d(issue_offset),
        "due_date": d(due_offset),
        "status": random.choice(["pending", "pending", "pending", "paid"]),
    })

# ---------------------------------------------------------
# 3. Receivables (10) - money OWED TO the business
# ---------------------------------------------------------
receivables = []
CUSTOMER_NAMES = [
    "Orion Fabricators", "Delta Engineering", "Coastal Auto Parts",
    "Marina Industrial Buyers", "Everest Metal Buyers", "Zenith Exports",
    "Prime Alloys Buyer Co", "Skyline Manufacturing", "Nova Copper Buyers",
    "Titan Metal Purchasers"
]
for i, cust in enumerate(CUSTOMER_NAMES, start=1):
    expected_offset = random.randint(1, 30)
    amount = random.randint(1_00_000, 10_00_000)
    receivables.append({
        "receivable_id": f"R{i:03d}",
        "customer_name": cust,
        "amount": amount,
        "expected_date": d(expected_offset),
        "original_expected_date": d(expected_offset),
        "status": "expected",
        "delay_history": [],  # will track delay_receivable() calls
    })

# ---------------------------------------------------------
# 4. Obligations (30 days) - fixed recurring costs (payroll, rent, utilities...)
# ---------------------------------------------------------
obligation_types = ["Payroll", "Rent", "Utilities", "Transport", "Loan EMI", "Misc Overheads"]
obligations = []
for day in range(30):
    daily_items = []
    for otype in obligation_types:
        if otype == "Payroll" and day % 30 != 29:
            continue
        if otype == "Loan EMI" and day % 30 != 4:
            continue
        if otype == "Rent" and day % 30 != 0:
            continue
        if random.random() < 0.6:
            daily_items.append({
                "type": otype,
                "amount": random.randint(5_000, 3_00_000) if otype != "Payroll" else random.randint(4_00_000, 6_00_000)
            })
    obligations.append({
        "date": d(day),
        "items": daily_items,
        "total": sum(x["amount"] for x in daily_items)
    })

# ---------------------------------------------------------
# 5. Financing options (2-3)
# ---------------------------------------------------------
financing_options = [
    {
        "financing_id": "F001",
        "name": "Working Capital Line of Credit",
        "type": "credit_line",
        "max_amount": 20_00_000,
        "interest_rate_annual": 0.14,
        "repayment_days": 90,
        "available": True,
    },
    {
        "financing_id": "F002",
        "name": "Invoice Discounting",
        "type": "invoice_discounting",
        "max_amount": 15_00_000,
        "interest_rate_annual": 0.16,
        "repayment_days": 45,
        "available": True,
    },
    {
        "financing_id": "F003",
        "name": "Short-Term Business Loan",
        "type": "term_loan",
        "max_amount": 25_00_000,
        "interest_rate_annual": 0.18,
        "repayment_days": 180,
        "available": True,
    },
]

# ---------------------------------------------------------
# 6. Cash position
# ---------------------------------------------------------
cash = {
    "current_cash": 12_50_000,
    "restricted_cash": 2_00_000,
    "protected_cash": 1_50_000,
    "as_of_date": d(0),
}

# ---------------------------------------------------------
# Write all files
# ---------------------------------------------------------
def save(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {filename} ({len(data) if isinstance(data, list) else 1} records)")

save("suppliers.json", suppliers)
save("invoices.json", invoices)
save("receivables.json", receivables)
save("obligations.json", obligations)
save("financing.json", financing_options)
save("cash.json", cash)

print("\nAll synthetic data generated successfully.")