Zypher Capital

An autonomous, explainable working-capital decision engine for allocating scarce capital across payments, financing, and supplier-risk priorities.

CSI ORIGIN 2026 · Problem Statement 4
Challenge: Autonomous Working-Capital Management Under Financial and Supply-Chain Constraints

Overview

 Zypher Capital is built to answer a question a normal finance dashboard cannot:

Given current cash, expected receivables, supplier invoices, upcoming obligations, financing choices, risk limits, and uncertainty, what should we pay, defer, finance, or retain — and why?

Instead of optimizing only today's cash balance, Zypher Capital follows a continuous loop:

Observe
  ↓
Forecast
  ↓
Prioritize
  ↓
Evaluate Financing
  ↓
Allocate Capital
  ↓
Recommend / Execute in Sandbox
  ↓
Monitor Outcomes
  ↓
Re-optimize
  ↺

The product is designed as an event-driven financial decision system rather than a reporting dashboard.

Core capabilities

Financial State

The system maintains a normalized working-capital state covering available/restricted/protected/deployable cash, invoices, receivables, obligations, financing options, supplier information, risk context, and prior decision context.

Forward-looking Forecasting

The Forecast Engine projects daily liquidity over a configurable horizon.

Conceptually:

ProjectedCash(t+1)
=
ProjectedCash(t)
+ Receivables(t)
+ FinancingInflows(t)
- InvoicePayments(t)
- Obligations(t)
- FinancingRepayments(t)

The forecast exposes projected cash, minimum cash, reserve requirements, reserve-breach status, and liquidity survival horizon.

Supplier Intelligence

Suppliers are treated as operationally significant entities, not just payment destinations.

Risk analysis considers strategic importance, single-source exposure, lead-time risk, spend concentration, supplier liquidity need, financial distress, payment dependency, centrality, disruption probability, and cascade impact.

Supplier Dependency Graph

Supplier relationships are represented as a directed graph. This enables:

dependency exploration

cascading-risk traversal

connected components / supplier clusters

centrality-based supplier importance

downstream impact analysis

A supplier can therefore influence payment priority because of network position, not simply invoice value.

Payment Prioritization

Invoice priority is deterministic and multi-factor:

PriorityScore =
    wd × DiscountValue
  - wf × FinancingCost
  - wp × PenaltyRisk
  + ws × SupplierCriticality
  + wl × SupplierLiquidityNeed
  + wu × Urgency

Higher scores are considered earlier. The implementation also uses deterministic tie-breaking so the same inputs produce reproducible rankings.

Candidate Actions

For each invoice the decision layer can generate candidates such as:

PAY NOW
PAY EARLY
PAY AT MATURITY
DEFER
BANK FINANCE
SUPPLIER FINANCE
RETAIN CASH

Candidate generation is deliberately separated from final decision authority.

Financing Intelligence

Financing is evaluated across configured funding sources using financing amount, annual rate, fees, limits, tenor, eligibility, liquidity preserved, and effective cost.

Zypher Capital can choose financing even when cash exists when preserving future liquidity is more valuable than consuming internal cash.

Discount Engine

The Discount Engine evaluates early-payment economics, discount value, discount window, annualized return, eligibility, and reason for accepting or rejecting the discount.

Penalty Engine

The Penalty Engine evaluates the cost of delaying payment using invoice amount, due date, payment date, penalty rate, and permissible delay.

Decision Engine

Candidate actions are passed through:

Candidate Actions
      ↓
Hard Constraints
      ↓
Feasible / Rejected
      ↓
Deterministic Scoring
      ↓
Preferred Strategy

This prevents a financially attractive but infeasible action from being recommended.

Re-optimization

The core differentiator is adaptation.

A previously good decision may become unsafe after:

a receivable is delayed

cash changes materially

a new obligation appears

a supplier becomes distressed

financing rates or availability change

payment terms change

forecast confidence falls

a previously recommended action becomes infeasible

The system then recalculates:

Old State
   ↓
Material Event
   ↓
New State
   ↓
Forecast Again
   ↓
Re-rank
   ↓
Re-evaluate
   ↓
New Plan

Example:

Before:
Pay Invoice A early
Use internal cash
Keep existing queue

Event:
Receivable arrives late

After:
Cancel non-critical early payment
Preserve liquidity reserve
Prioritize a strategic supplier
Re-evaluate financing
Build a revised queue

Automation

Zypher Capital includes an automation monitor around the decision pipeline.

Financial State
      ↓
Periodic Monitoring
      ↓
Detect Material Change
      ↓
Forecast
      ↓
Priority Re-ranking
      ↓
Candidate Actions
      ↓
Updated Decision Context

The user can also run a manual check. Scenario simulation remains separate:

Automation:
Actual state changes → system reacts

Scenario:
User supplies a hypothetical event → system simulates it

The event is never intended to be invented silently.

Data Structures & Algorithms

The repository deliberately uses DSA concepts that map to real product problems.

Heap / Priority Queue

Invoice ranking uses a heap-backed priority queue.

The queue stores:

(-priority_score, invoice_id, priority)

and uses heapq so the highest actual score is retrieved first. Heap removal is O(log n).

This supports fast priority retrieval and rebuilding after financial events.

Graph Algorithms

Supplier risk uses graph structures with:

BFS for cascade propagation

DFS for dependency exploration

connected components for isolated supplier clusters

centrality / PageRank-style importance

shortest/least-cost paths when multi-channel routing is relevant

BFS/DFS operate in O(V + E).

Greedy Strategy

Greedy ranking provides a transparent baseline, solver warm start, or fallback. It is intentionally not the final authority for scenarios with complex cross-period interactions.

Knapsack Perspective

Scarce capital can be viewed as a multi-dimensional knapsack:

Capacity → cash available above reserve
Item     → invoice action
Value    → discount + supplier benefit - risk/cost
Weight   → cash required

Real working-capital decisions go beyond basic knapsack because time, financing, reserve requirements, and dependencies interact.

Dynamic Programming

Small discretized multi-period examples can be represented as:

DP[t][c]

where t is time and c is discretized available cash.

The PRD treats this as a teaching/small-instance technique, not the main production solver, because the state space grows rapidly as invoices, cash granularity, actions, and financing choices increase.

Fenwick Tree / Segment Tree

For a higher-frequency real-time implementation, Fenwick trees or segment trees can support fast cash-flow updates and range queries. The PRD identifies these as advanced scalability options.

Monte Carlo

Monte Carlo simulation can stress uncertain receivable dates, supplier disruption, financing availability, and unexpected obligations:

Sample uncertain events
        ↓
Generate cash path
        ↓
Apply strategy
        ↓
Measure minimum cash / reserve breach
        ↓
Repeat S times

A key risk measure is:

ShortfallProbability =
reserve-breach scenarios / total scenarios

with conceptual complexity O(S × T × A).

Pareto Optimization

There may be no single objectively best strategy. Pareto analysis exposes non-dominated strategies across:

total cost

liquidity protection

supplier risk

financing exposure

discount capture

For example:

Cost-first
Balanced
Supplier-first

This makes trade-offs visible instead of hiding them behind one score.

Risk-adjusted objective

Zypher Capital is designed to minimize a broader risk-adjusted working-capital cost:

Financing Cost
+ Late-Payment Penalty
- Discount Savings
+ Supplier Risk Cost
+ Liquidity Shortfall Cost
+ Financial Exposure Cost
+ Decision Instability Cost

The point is simple:

The cheapest action today is not necessarily the safest action tomorrow.

Liquidity Firewall

The decision layer is built around protecting mandatory liquidity and can conceptually move through:

GREEN → YELLOW → ORANGE → RED → BLACK

As liquidity risk increases, the strategy becomes more conservative.

The system can reduce discretionary payments, increase protected liquidity, prefer liquidity-preserving financing, or escalate risky recommendations.

Emergency Liquidity Mode

If no feasible safe plan exists, Zypher Capital should not return an optimistic recommendation.

Instead it enters:

EMERGENCY LIQUIDITY MODE

and surfaces what is required to restore feasibility.

Explainability & Auditability

Every decision should be explainable:

What was recommended?
        ↓
Why?
        ↓
Which constraints mattered?
        ↓
Which alternatives were considered?
        ↓
Why were alternatives rejected?
        ↓
What assumptions were used?
        ↓
What would need to change?

The intended audit trail contains:

triggering event

input snapshot

objective weights

selected strategy

rejected alternatives

human approval/override

outcome tracking

solver/model version

Human-in-the-loop safety

Automation does not mean blindly executing financial actions.

High-risk recommendations are intended to require human approval.

Deterministic financial logic remains authoritative.

An LLM, if used, is restricted to:

natural-language explanations

conversational scenario setup

summarization

translating structured factors into human-readable reasoning

It must not control:

payment selection

financing allocation

final numerical cost calculations

constraint checking

approval bypass

actual payment execution

Dashboard

The Command Center brings the engines together:

Financial State
      ↓
Forecast
      ↓
Supplier Intelligence
      ↓
Decision Engine
      ↓
Re-optimization
      ↓
Automation Monitor
      ↓
Financing / Discounts / Penalties

Users can work with real invoices and suppliers returned by the backend and trigger explicit scenarios instead of entering internal scoring variables.

API

The FastAPI backend exposes endpoints for:

GET  /api/health
GET  /api/financial-state
GET  /api/invoices
GET  /api/suppliers

POST /api/forecast

POST /api/supplier-risk
GET  /api/supplier-risk/{supplier_id}

GET  /api/financing/options
POST /api/financing/compare

POST /api/discount/evaluate
POST /api/penalty/evaluate

POST /api/decision/actions
POST /api/decision/evaluate

POST /api/reoptimize

GET  /api/automation/status
POST /api/automation/check
POST /api/automation/start
POST /api/automation/stop

Repository structure

CSI_PROJECT/
├── backend/
│   ├── agents/
│   │   └── supplier_intelligence/
│   ├── automation/
│   ├── decision_engine/
│   │   ├── action_generator.py
│   │   ├── constraints.py
│   │   ├── discount_engine.py
│   │   ├── financing_engine.py
│   │   ├── models.py
│   │   ├── penalty_engine.py
│   │   ├── priority_engine.py
│   │   ├── scoring.py
│   │   └── supplier_risk_adapter.py
│   ├── forecast_engine/
│   ├── models/
│   ├── state_engine/
│   └── main.py
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── pages/
│       └── services/
│
└── README.md

Getting started

Backend

python -m uvicorn backend.main:app --reload

API documentation:

http://127.0.0.1:8000/docs

Frontend

cd frontend
npm install
npm run dev

Frontend:

http://localhost:5173

Tests

python -m pytest -v

Frontend checks:

cd frontend
npm run lint
npm run build

Demo scenario

The strongest demonstration is event-driven:

1. Show current liquidity.
2. Run the forward cash forecast.
3. Show invoice priority.
4. Introduce a material event such as a receivable delay.
5. Forecast changes.
6. Supplier/payment priorities change.
7. Candidate actions are regenerated.
8. Hard constraints reject unsafe options.
9. Financing is re-evaluated.
10. Re-optimization produces a revised plan.
11. Explain what changed and why.

What makes Zypher Capital different?

A conventional dashboard says:

Cash = X
Invoices = Y
Receivables = Z

A static rule system says:

Discount > Financing Rate
→ Pay Early

Zypher Capital combines:

Current Cash
+ Future Receivables
+ Uncertainty
+ Obligations
+ Invoice Urgency
+ Discounts
+ Penalties
+ Financing Cost
+ Supplier Criticality
+ Supplier Distress
+ Dependency Graph
+ Hard Constraints
+ Decision Stability
        ↓
Risk-adjusted Recommendation
        ↓
Event-driven Re-optimization

The result is a working-capital system that acts like a continuously adapting treasury and supply-chain analyst rather than a static reporting screen.

Project principles

Forward-looking: safe cash is not simply today's cash.

Multi-objective: liquidity, cost, discounts, penalties, supplier risk, financing, and stability matter together.

Event-driven: material changes invalidate stale decisions.

Deterministic authority: numerical decisions come from explicit financial logic and constraints.

Explainable: recommendations should expose the reasoning and trade-offs.

Safe by design: infeasible or high-risk decisions are blocked or escalated.

Important scope note

Some advanced algorithms in the PRD — including dynamic programming, Fenwick/segment trees, Monte Carlo, Pareto optimization, counterfactual analysis, and more advanced solver formulations — are documented as extensions or advanced directions. They should not be represented as implemented production features unless the corresponding modules exist in the repository.

Likewise, any benchmark figures from the PRD should be treated as simulated/hypothetical until reproduced by the project's own simulator.

Built for

CSI ORIGIN 2026 — Problem Statement 4
Autonomous Working-Capital Management Under Financial and Supply-Chain Constraints
