# Zypher Capital

### Agentic AI for Intelligent Working-Capital Optimization

Zypher Capital is an **Agentic AI-driven financial decision system** that helps businesses optimize working capital under uncertainty. It continuously analyzes cash, receivables, supplier obligations, financing options, and supplier risk to determine **what should be paid, when it should be paid, whether it should be financed or deferred, and how much liquidity must be protected**.

Unlike traditional financial dashboards that only report cash positions and outstanding invoices, Zypher Capital creates an adaptive decision loop that **forecasts, evaluates, optimizes, explains, monitors, and re-optimizes** financial strategies as conditions change.

---

## 🚨 Problem Statement

Businesses constantly face competing working-capital decisions:

* Should an invoice be paid early to capture a discount?
* Should payment be delayed to preserve liquidity?
* Is financing cheaper than using internal cash?
* Which suppliers should be prioritized?
* How much cash should be protected for future obligations?
* What happens if a major customer delays payment?
* What happens if a critical supplier becomes distressed?
* What if financing rates suddenly increase?

Traditional approaches rely heavily on manual decisions, spreadsheets, dashboards, or static rules. These approaches become difficult to manage when **cash uncertainty, supplier dependencies, financing costs, contractual constraints, and future obligations interact simultaneously**.

Zypher Capital addresses this by converting working-capital management into a **constraint-driven, continuously adaptive decision process**.

---

# 🧠 Core Concept

Zypher Capital follows a closed-loop financial decision architecture:

```text
Observe
   ↓
Validate
   ↓
Build Financial State
   ↓
Forecast Cash Flow
   ↓
Model Receivable Uncertainty
   ↓
Assess Supplier Risk
   ↓
Calculate Liquidity Firewall
   ↓
Generate Candidate Actions
   ↓
Apply Hard Constraints
   ↓
Score Soft Constraints
   ↓
MILP Optimization
   ↓
Pareto Strategy Comparison
   ↓
Recommendation + Explanation
   ↓
Human Approval
   ↓
Monitor
   ↓
Re-optimize when conditions change
```

The system therefore does not produce a static recommendation. It maintains a **continuous decision loop**.

---

# ⚙️ How It Works

## 1. Observe

Zypher Capital collects the organization's current financial and operational state.

### Inputs

* Current cash
* Restricted cash
* Bank balances
* Accounts receivable
* Supplier invoices
* Invoice due dates
* Discount windows
* Penalty terms
* Mandatory obligations
* Payroll
* Taxes
* Rent
* Debt repayments
* Financing facilities
* Financing rates
* Financing limits
* Supplier information
* Historical payment behavior
* Supplier risk information

This creates a unified representation of the company's financial state.

---

## 2. Validate

Before any prediction or optimization occurs, the system validates the incoming data.

It detects issues such as:

* Duplicate invoice IDs
* Duplicate payment attempts
* Missing due dates
* Missing discount terms
* Missing supplier records
* Missing financing limits
* Unverified invoices
* Disputed invoices
* Stale cash positions
* Currency inconsistencies
* Missing receivable dates

This prevents incorrect financial data from propagating into the optimization engine.

---

## 3. Cash-Flow Forecasting

The forecasting layer predicts the company's future liquidity position.

It considers:

### Cash inflows

* Customer receivables
* Expected collection dates
* Historical payment behavior

### Cash outflows

* Supplier payments
* Payroll
* Taxes
* Rent
* Debt repayments
* Other mandatory obligations

Instead of assuming receivables will always arrive on time, Zypher Capital models **collection uncertainty** and generates multiple possible future scenarios.

---

# 🎲 Monte Carlo Stress Testing

Zypher Capital can use **Monte Carlo simulation** to evaluate thousands of possible financial outcomes.

For example:

```text
Receivable:
Expected delay = 0 days

Possible scenarios:
0 days
3 days
7 days
10 days
15 days
20 days
...
```

The system can then estimate:

* Probability of liquidity shortfall
* Minimum projected liquidity
* Survival horizon
* Firewall breach probability
* Strategy resilience

This allows the system to evaluate not just:

> "What is likely to happen?"

but also:

> "What happens if things go badly?"

---

# 🛡️ Liquidity Firewall

The **Liquidity Firewall** is a core component of Zypher Capital.

A business may have ₹10 lakh in its bank account, but that does not necessarily mean it can safely spend ₹10 lakh.

The Firewall separates:

```text
Available Cash
      │
      ├─────────────── Protected Cash
      │                 ├─ Operational Reserve
      │                 ├─ Receivable Buffer
      │                 ├─ Supplier Risk Reserve
      │                 ├─ Financing Reserve
      │                 └─ Policy Buffer
      │
      └─────────────── Deployable Cash
```

### Formula

```text
Deployable Cash =
Available Cash − Protected Cash
```

This prevents the optimization engine from consuming cash that is required for future operational continuity.

### Firewall States

```text
GREEN
Normal optimization

YELLOW
Restrict discretionary payments

ORANGE
Stress scenario threatens reserve

RED
Reserve breach predicted

BLACK
Mandatory obligations cannot be funded
```

---

# 🔗 Supplier Risk Graph

Not all suppliers have equal business importance.

Zypher Capital models supplier relationships using a **graph-based risk engine**.

```text
                 Company
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
   Supplier A  Supplier B  Supplier C
        │
        ▼
  Critical Material
        │
        ▼
 Production Dependency
```

Supplier criticality can incorporate:

* Strategic importance
* Single-source risk
* Lead-time risk
* Spend concentration
* Graph centrality
* Historical behavior
* Distress indicators

This allows Zypher Capital to understand **second-order effects**.

For example, delaying a payment to a highly critical single-source supplier may create significantly greater operational risk than delaying an equivalent invoice from a replaceable supplier.

---

# 📑 Intelligent Invoice Prioritization

Zypher Capital dynamically ranks invoices using a **priority queue**.

The priority can consider:

* Due date
* Discount availability
* Discount value
* Late-payment penalty
* Supplier criticality
* Supplier distress
* Liquidity impact
* Permissible delay

The priority is therefore dynamic rather than simply:

```text
Earliest due date → Highest priority
```

Instead:

```text
Financial Impact
+
Liquidity Risk
+
Supplier Risk
+
Payment Economics
=
Dynamic Priority
```

---

# 💰 Financing Optimization

The system evaluates multiple sources of liquidity.

Possible financing sources include:

* Internal cash
* Bank credit facility
* Short-term loans
* Supplier financing
* Reverse factoring
* Purchase-order financing

For every financing option, Zypher Capital evaluates factors such as:

* Interest rate
* Tenor
* Fixed fees
* Facility limits
* Eligibility
* Exposure
* Liquidity preserved

The system then compares:

```text
Cost of Financing
        VS
Value of Liquidity Preserved
+
Discount Benefit
+
Supplier Risk Avoided
```

This allows the system to determine when financing is economically preferable to consuming internal cash.

---

# 🧮 MILP Optimization Engine

After generating possible payment and financing actions, Zypher Capital formulates the decision problem as a **Mixed-Integer Linear Programming (MILP)** optimization problem.

### Hard constraints

These represent conditions that **cannot be violated**.

Examples:

```text
Cash ≥ Required Firewall Reserve

Payment ≤ Available Funding

Financing ≤ Facility Limit

Mandatory Obligations Must Be Funded

Invoice Cannot Be Paid Twice
```

Any strategy violating a hard constraint is rejected.

### Soft constraints

These represent business preferences and trade-offs.

Examples:

* Maximize discount capture
* Minimize financing cost
* Minimize penalties
* Minimize supplier risk
* Preserve liquidity
* Reduce unnecessary plan changes

The optimizer then searches for the **best feasible strategy**.

Technologies such as **OR-Tools CP-SAT or PuLP** can be used for this optimization layer.

---

# 📊 Pareto Strategy Analysis

There may not always be one universally "best" financial strategy.

Zypher Capital can compare alternative strategies across competing objectives.

### Example

| Strategy           | Liquidity | Discount Capture | Financing Cost |
| ------------------ | --------- | ---------------- | -------------- |
| Aggressive Payment | Low       | High             | Low            |
| Maximum Liquidity  | High      | Low              | High           |
| Balanced           | Medium    | Medium           | Medium         |

This provides decision-makers with visibility into the **trade-offs between cost, liquidity, and risk**.

---

# 🤖 Controlled Agentic AI

Zypher Capital uses an **Agentic AI architecture**, but the LLM is deliberately restricted.

The LLM can:

* Explain financial decisions
* Answer "Why was this invoice not selected?"
* Generate CFO-friendly summaries
* Convert natural-language scenarios into structured events
* Explain changes after re-optimization
* Generate counterfactual explanations

### Example

A user can ask:

> "What happens if Customer Delta delays its ₹6 lakh payment by 15 days?"

The system converts this into a structured scenario, runs the deterministic financial models, and returns the resulting impact.

### What the LLM cannot do

The LLM cannot:

* Select payment dates
* Calculate financial values
* Override the Liquidity Firewall
* Override hard constraints
* Approve payments
* Invent supplier risk
* Execute financial transactions

Therefore:

```text
              LLM
               ↓
       Explanation Layer
               ↓
      Optimization Engine
               ↓
       Liquidity Firewall
               ↓
    Financial Constraints
```

The **financial decision is produced by deterministic models and optimization**, while the LLM handles interaction and explanation.

---

# 🔄 Event-Driven Re-optimization

This is what makes Zypher Capital truly adaptive.

The system continuously monitors the financial environment.

Re-optimization can be triggered by:

* Receivable delays
* Significant cash changes
* New payroll/tax/rent obligations
* Financing-rate changes
* Reduced financing limits
* Supplier distress
* Supplier disruption
* Forecast deviations
* Invoice-term changes
* Predicted Firewall breaches
* Approaching payment deadlines

### Example

Initial recommendation:

```text
Cash = ₹10L
Firewall = GREEN

→ Pay Supplier A
→ Pay Supplier B
→ Finance Supplier C
```

A ₹6 lakh receivable is suddenly delayed by 15 days.

The system detects:

```text
Receivable Delay
      ↓
Forecast Changes
      ↓
Firewall Risk Increases
      ↓
Previous Plan Becomes Unsafe
      ↓
Cancel Low-Priority Early Payments
      ↓
Retain Internal Cash
      ↓
Finance Critical Supplier if Required
      ↓
Generate New Optimized Plan
```

The important distinction is:

> **Zypher Capital does not merely alert the user that liquidity has deteriorated. It changes the recommended action plan.**

---

# 🚨 Emergency Liquidity Mode

If no feasible strategy satisfies the required financial constraints, Zypher Capital enters **Emergency Liquidity Mode**.

The system identifies:

* Current Firewall state
* Funding gap
* Earliest projected shortfall
* Mandatory obligations at risk
* Critical suppliers at risk
* Payments that can legally be deferred
* Financing still available
* Recommended emergency funding
* Required human approvals
* Data-quality warnings

The system never claims an unsafe strategy is optimal.

---

# 👤 Human-in-the-Loop

High-impact financial decisions require human approval.

Approval may be required when:

* Financing exceeds a defined threshold
* Supplier payment exceeds a threshold
* Firewall enters Orange/Red/Black
* Critical supplier payment is delayed
* Shortfall probability exceeds tolerance
* Forecast confidence is low
* Data is incomplete
* Strategy changes significantly
* Emergency financing is recommended

Users can:

```text
Approve
Reject
Modify Payment Timing
Change Financing Source
Change Risk Weights
Create Scenario
Override with Reason
```

All approvals and overrides are recorded in the **audit trail**.

---

# 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │      Frontend       │
                    │   React / Next.js   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │      REST APIs      │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       Forecasting        Risk Engine       Financial State
       pandas/NumPy       NetworkX          PostgreSQL
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Liquidity Firewall  │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Optimization Engine │
                    │    OR-Tools/PuLP    │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Recommendation      │
                    │ + Explanation Layer │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Human Approval      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Event Monitoring    │
                    └──────────┬──────────┘
                               │
                               └──────→ Re-optimize
```

---

# 🛠️ Technology Stack

| Layer               | Technology                         |
| ------------------- | ---------------------------------- |
| Frontend            | Next.js, React                     |
| Styling             | Tailwind CSS                       |
| Backend             | FastAPI                            |
| Database            | Supabase / PostgreSQL              |
| Optimization        | OR-Tools / PuLP                    |
| Forecasting         | Python, pandas, NumPy              |
| ML                  | scikit-learn / XGBoost             |
| Graph Analysis      | NetworkX                           |
| Graph Visualization | React Flow / D3                    |
| Charts              | Recharts                           |
| AI Layer            | Controlled LLM API                 |
| Deployment          | Vercel + Render/Railway + Supabase |

---

# 📡 Core API Endpoints

```text
GET  /invoices
GET  /receivables
GET  /suppliers
GET  /financing-options

POST /forecast
POST /optimize
POST /simulate
POST /scenario
POST /agent/reoptimize

GET  /decisions/{id}
GET  /decisions/{id}/explanation

POST /decisions/{id}/approve
POST /decisions/{id}/override

GET  /audit-events
```

---

# 📈 Key Metrics

Zypher Capital can evaluate its performance using:

* Total working-capital cost
* Discount capture rate
* Financing cost
* Penalty cost
* Minimum liquidity
* Firewall breaches
* Liquidity survival horizon
* Supplier-risk exposure
* Critical supplier delays
* Decision stability
* Re-optimization latency
* Forecast accuracy
* Explanation completeness
* Human approval rate

---

# 🎯 What Makes Zypher Capital Different?

Zypher Capital is **not simply a dashboard, forecasting model, chatbot, or invoice-prioritization system**.

It combines multiple decision technologies into a single closed-loop architecture:

```text
Forecasting
     +
Uncertainty Modeling
     +
Monte Carlo Simulation
     +
Supplier Graph Intelligence
     +
Liquidity Firewall
     +
Priority Queues
     +
MILP Optimization
     +
Pareto Analysis
     +
Explainable AI
     +
Event-Driven Re-optimization
     +
Human Governance
```

The result is a system that moves working-capital management from:

**"What is happening to our cash?"**

to:

**"What should we do about it, why is that decision safe, and how should the plan change if the situation changes?"**

---

# 🚀 Project Vision

Zypher Capital aims to transform working-capital management from a **static, manually managed financial process into a continuous, explainable and constraint-aware decision system**.

Its ultimate objective is not simply to maximize short-term cash efficiency, but to find the optimal balance between:

**Liquidity + Cost + Supplier Resilience + Risk + Financial Constraints**

while keeping humans in control of high-impact financial decisions.

---

## 👥 Team

**Project:** Zypher Capital
**Domain:** FinTech / Agentic AI / Financial Optimization
**Focus:** Working-Capital Intelligence & Liquidity Optimization

---

## ⚠️ Disclaimer

Zypher Capital is a decision-support and optimization prototype. Recommendations are generated from configured financial data, constraints, scenarios, and optimization models and should be reviewed by authorized financial personnel before execution.
