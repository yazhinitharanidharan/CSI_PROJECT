import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useAuth } from "../hooks/useAuth";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatNumber(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  return number.toFixed(digits);
}

function formatActionType(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .toUpperCase();
}

function formatDate(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
}

function riskClass(value) {
  return String(value || "LOW").toLowerCase();
}

function Dashboard() {
  const { user, signOut } = useAuth();

  // =========================================================
  // CORE STATE
  // =========================================================

  const [financialState, setFinancialState] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [financingOptions, setFinancingOptions] = useState([]);

  const [forecast, setForecast] = useState(null);
  const [decisionResult, setDecisionResult] = useState(null);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [supplierRisk, setSupplierRisk] = useState(null);
  const [reoptimization, setReoptimization] = useState(null);
  const [financingComparison, setFinancingComparison] = useState(null);
  const [discountResult, setDiscountResult] = useState(null);
  const [penaltyResult, setPenaltyResult] = useState(null);

  // =========================================================
  // FORM STATE
  // =========================================================

  const [forecastDays, setForecastDays] = useState(30);
  const [selectedInvoice, setSelectedInvoice] = useState("");
  const [selectedSupplier, setSelectedSupplier] = useState("");
  const [selectedAction, setSelectedAction] = useState("");
  const [selectedFinancingOption, setSelectedFinancingOption] =
    useState("");

  const [reoptimizationInvoice, setReoptimizationInvoice] =
    useState("");
  const [advanceDays, setAdvanceDays] = useState(5);

  const [financingAmount, setFinancingAmount] = useState("");
  const [financingDays, setFinancingDays] = useState(30);

  const [discountRate, setDiscountRate] = useState("0.02");
  const [discountDeadline, setDiscountDeadline] = useState("");
  const [discountPaymentDate, setDiscountPaymentDate] =
    useState("");

  const [penaltyPaymentDate, setPenaltyPaymentDate] =
    useState("");
  const [penaltyRate, setPenaltyRate] = useState("0.001");
  const [permissibleDelayDays, setPermissibleDelayDays] =
    useState(0);

  // =========================================================
  // LOADING / ERROR STATE
  // =========================================================

  const [loading, setLoading] = useState(true);
  const [invoiceLoading, setInvoiceLoading] = useState(true);
  const [supplierLoading, setSupplierLoading] = useState(true);
  const [financingLoading, setFinancingLoading] = useState(true);

  const [forecastLoading, setForecastLoading] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [evaluationLoading, setEvaluationLoading] =
    useState(false);
  const [supplierRiskLoading, setSupplierRiskLoading] =
    useState(false);
  const [reoptimizationLoading, setReoptimizationLoading] =
    useState(false);
  const [financingComparisonLoading, setFinancingComparisonLoading] =
    useState(false);
  const [discountLoading, setDiscountLoading] = useState(false);
  const [penaltyLoading, setPenaltyLoading] = useState(false);

  const [error, setError] = useState("");
  const [invoiceError, setInvoiceError] = useState("");
  const [supplierError, setSupplierError] = useState("");
  const [financingError, setFinancingError] = useState("");
  const [forecastError, setForecastError] = useState("");
  const [decisionError, setDecisionError] = useState("");
  const [evaluationError, setEvaluationError] = useState("");
  const [supplierRiskError, setSupplierRiskError] = useState("");
  const [reoptimizationError, setReoptimizationError] =
    useState("");
  const [financingComparisonError, setFinancingComparisonError] =
    useState("");
  const [discountError, setDiscountError] = useState("");
  const [penaltyError, setPenaltyError] = useState("");

  // =========================================================
  // DERIVED DATA
  // =========================================================

  const unpaidInvoices = useMemo(
    () =>
      invoices.filter(
        (invoice) =>
          String(invoice.status).toLowerCase() !== "paid"
      ),
    [invoices]
  );

  const selectedInvoiceData = useMemo(
    () =>
      invoices.find(
        (invoice) => invoice.invoice_id === selectedInvoice
      ),
    [invoices, selectedInvoice]
  );

  const selectedReoptimizationInvoice = useMemo(
    () =>
      invoices.find(
        (invoice) =>
          invoice.invoice_id === reoptimizationInvoice
      ),
    [invoices, reoptimizationInvoice]
  );

  // =========================================================
  // FETCH FINANCIAL STATE
  // =========================================================

  const fetchFinancialState = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/api/financial-state`
      );

      if (!response.ok) {
        throw new Error(
          `Backend returned ${response.status}`
        );
      }

      setFinancialState(await response.json());
    } catch (err) {
      console.error(err);
      setError(
        "Unable to connect to the backend. Make sure FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // =========================================================
  // FETCH INVOICES
  // =========================================================

  const fetchInvoices = useCallback(async () => {
    try {
      setInvoiceLoading(true);
      setInvoiceError("");

      const response = await fetch(
        `${API_URL}/api/invoices`
      );

      if (!response.ok) {
        throw new Error(
          `Invoice endpoint returned ${response.status}`
        );
      }

      const data = await response.json();

      const loaded = Array.isArray(data.invoices)
        ? data.invoices
        : [];

      setInvoices(loaded);

      setSelectedInvoice((current) => {
        if (
          current &&
          loaded.some(
            (item) => item.invoice_id === current
          )
        ) {
          return current;
        }

        return loaded[0]?.invoice_id || "";
      });

      setReoptimizationInvoice((current) => {
        if (
          current &&
          loaded.some(
            (item) => item.invoice_id === current
          )
        ) {
          return current;
        }

        return (
          loaded.find(
            (item) =>
              String(item.status).toLowerCase() !== "paid"
          )?.invoice_id || ""
        );
      });
    } catch (err) {
      console.error(err);
      setInvoiceError(
        err.message || "Unable to load invoices."
      );
    } finally {
      setInvoiceLoading(false);
    }
  }, []);

  // =========================================================
  // FETCH SUPPLIERS
  // =========================================================

  const fetchSuppliers = useCallback(async () => {
    try {
      setSupplierLoading(true);
      setSupplierError("");

      const response = await fetch(
        `${API_URL}/api/suppliers`
      );

      if (!response.ok) {
        throw new Error(
          `Supplier endpoint returned ${response.status}`
        );
      }

      const data = await response.json();

      const loaded = Array.isArray(data.suppliers)
        ? data.suppliers
        : [];

      setSuppliers(loaded);

      setSelectedSupplier((current) => {
        if (
          current &&
          loaded.some(
            (supplier) =>
              supplier.supplier_id === current
          )
        ) {
          return current;
        }

        return loaded[0]?.supplier_id || "";
      });
    } catch (err) {
      console.error(err);
      setSupplierError(
        err.message || "Unable to load suppliers."
      );
    } finally {
      setSupplierLoading(false);
    }
  }, []);

  // =========================================================
  // FETCH FINANCING OPTIONS
  // =========================================================

  const fetchFinancingOptions = useCallback(async () => {
    try {
      setFinancingLoading(true);
      setFinancingError("");

      const response = await fetch(
        `${API_URL}/api/financing/options`
      );

      if (!response.ok) {
        throw new Error(
          `Financing endpoint returned ${response.status}`
        );
      }

      const data = await response.json();

      const loaded = Array.isArray(data.options)
        ? data.options
        : [];

      setFinancingOptions(loaded);

      setSelectedFinancingOption(
        loaded.find((option) => option.available)
          ?.financing_id || ""
      );
    } catch (err) {
      console.error(err);
      setFinancingError(
        err.message ||
          "Unable to load financing options."
      );
    } finally {
      setFinancingLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFinancialState();
    fetchInvoices();
    fetchSuppliers();
    fetchFinancingOptions();
  }, [
    fetchFinancialState,
    fetchInvoices,
    fetchSuppliers,
    fetchFinancingOptions,
  ]);

  // =========================================================
  // FORECAST
  // =========================================================

  async function runForecast() {
    const days = Number(forecastDays);

    if (
      !Number.isInteger(days) ||
      days < 1 ||
      days > 365
    ) {
      setForecastError(
        "Forecast horizon must be between 1 and 365 days."
      );
      return;
    }

    try {
      setForecastLoading(true);
      setForecastError("");
      setForecast(null);

      const response = await fetch(
        `${API_URL}/api/forecast`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            horizon_days: days,
          }),
        }
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Forecast request failed with ${response.status}`
        );
      }

      setForecast(body);
    } catch (err) {
      console.error(err);
      setForecastError(
        err.message || "Unable to generate forecast."
      );
    } finally {
      setForecastLoading(false);
    }
  }

  // =========================================================
  // DECISION CANDIDATES
  // =========================================================

  async function runDecisionEngine() {
    if (!selectedInvoice) {
      setDecisionError("Please select an invoice.");
      return;
    }

    try {
      setDecisionLoading(true);
      setDecisionError("");
      setDecisionResult(null);
      setEvaluationResult(null);

      const response = await fetch(
        `${API_URL}/api/decision/actions?invoice_id=${encodeURIComponent(
          selectedInvoice
        )}`,
        {
          method: "POST",
        }
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Decision request failed with ${response.status}`
        );
      }

      setDecisionResult(body);

      if (body.actions?.length) {
        setSelectedAction(
          body.actions[0].action_type
        );
      }
    } catch (err) {
      console.error(err);
      setDecisionError(
        err.message ||
          "Unable to generate decision actions."
      );
    } finally {
      setDecisionLoading(false);
    }
  }

  // =========================================================
  // DECISION PLAN EVALUATION
  // =========================================================

  async function evaluateSelectedAction(
    action = selectedAction
  ) {
    if (!selectedInvoice || !action) {
      setEvaluationError(
        "Select an invoice and action first."
      );
      return;
    }

    try {
      setEvaluationLoading(true);
      setEvaluationError("");
      setEvaluationResult(null);

      const actionData = (
        decisionResult?.actions || []
      ).find(
        (item) => item.action_type === action
      );

      const response = await fetch(
        `${API_URL}/api/decision/evaluate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            invoice_id: selectedInvoice,
            action_type: action,
            scheduled_date:
              actionData?.scheduled_date || null,
            financing_option_id:
              actionData?.financing_option_id ||
              selectedFinancingOption ||
              null,
          }),
        }
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Evaluation failed with ${response.status}`
        );
      }

      setEvaluationResult(body);
    } catch (err) {
      console.error(err);
      setEvaluationError(
        err.message ||
          "Unable to evaluate the selected action."
      );
    } finally {
      setEvaluationLoading(false);
    }
  }

  // =========================================================
  // SUPPLIER RISK
  // =========================================================

  async function runSupplierRisk() {
    if (!selectedSupplier) {
      setSupplierRiskError(
        "Please select a supplier."
      );
      return;
    }

    try {
      setSupplierRiskLoading(true);
      setSupplierRiskError("");
      setSupplierRisk(null);

      const response = await fetch(
        `${API_URL}/api/supplier-risk/${encodeURIComponent(
          selectedSupplier
        )}`
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Supplier risk request failed with ${response.status}`
        );
      }

      setSupplierRisk(body);
    } catch (err) {
      console.error(err);
      setSupplierRiskError(
        err.message ||
          "Unable to analyze supplier risk."
      );
    } finally {
      setSupplierRiskLoading(false);
    }
  }

  // =========================================================
  // RE-OPTIMIZATION
  // =========================================================

  async function runReoptimization() {
    if (!reoptimizationInvoice) {
      setReoptimizationError(
        "Please select an unpaid invoice."
      );
      return;
    }

    const days = Number(advanceDays);

    if (
      !Number.isInteger(days) ||
      days < 1 ||
      days > 365
    ) {
      setReoptimizationError(
        "Advance days must be between 1 and 365."
      );
      return;
    }

    try {
      setReoptimizationLoading(true);
      setReoptimizationError("");
      setReoptimization(null);

      const response = await fetch(
        `${API_URL}/api/reoptimize`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            event_type:
              "invoice_due_date_advanced",
            invoice_id: reoptimizationInvoice,
            advance_days: days,
          }),
        }
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Re-optimization failed with ${response.status}`
        );
      }

      setReoptimization(body);
    } catch (err) {
      console.error(err);
      setReoptimizationError(
        err.message ||
          "Unable to run re-optimization."
      );
    } finally {
      setReoptimizationLoading(false);
    }
  }

  // =========================================================
  // FINANCING ENGINE
  // =========================================================

  async function runFinancingComparison() {
    const amount = Number(financingAmount);
    const days = Number(financingDays);

    if (!Number.isFinite(amount) || amount <= 0) {
      setFinancingComparisonError(
        "Enter a valid financing amount."
      );
      return;
    }

    if (
      !Number.isInteger(days) ||
      days < 0 ||
      days > 3650
    ) {
      setFinancingComparisonError(
        "Financing days must be between 0 and 3650."
      );
      return;
    }

    try {
      setFinancingComparisonLoading(true);
      setFinancingComparisonError("");
      setFinancingComparison(null);

      const response = await fetch(
        `${API_URL}/api/financing/compare`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            financing_amount: amount.toFixed(2),
            financing_days: days,
          }),
        }
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Financing comparison failed with ${response.status}`
        );
      }

      setFinancingComparison(body);
    } catch (err) {
      console.error(err);
      setFinancingComparisonError(
        err.message ||
          "Unable to compare financing options."
      );
    } finally {
      setFinancingComparisonLoading(false);
    }
  }

  // =========================================================
  // DISCOUNT ENGINE
  // =========================================================

  async function runDiscountEvaluation() {
    if (!selectedInvoiceData) {
      setDiscountError(
        "Select an invoice first."
      );
      return;
    }

    if (
      !discountPaymentDate ||
      !discountDeadline
    ) {
      setDiscountError(
        "Enter the discount deadline and payment date."
      );
      return;
    }

    try {
      setDiscountLoading(true);
      setDiscountError("");
      setDiscountResult(null);

      const response = await fetch(
        `${API_URL}/api/discount/evaluate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            invoice_amount:
              selectedInvoiceData.amount,
            discount_rate: discountRate,
            discount_deadline:
              discountDeadline,
            payment_date:
              discountPaymentDate,
            maturity_date:
              selectedInvoiceData.due_date,
          }),
        }
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Discount evaluation failed with ${response.status}`
        );
      }

      setDiscountResult(body);
    } catch (err) {
      console.error(err);
      setDiscountError(
        err.message ||
          "Unable to evaluate discount."
      );
    } finally {
      setDiscountLoading(false);
    }
  }

  // =========================================================
  // PENALTY ENGINE
  // =========================================================

  async function runPenaltyEvaluation() {
    if (!selectedInvoiceData) {
      setPenaltyError(
        "Select an invoice first."
      );
      return;
    }

    if (!penaltyPaymentDate) {
      setPenaltyError(
        "Enter a proposed payment date."
      );
      return;
    }

    try {
      setPenaltyLoading(true);
      setPenaltyError("");
      setPenaltyResult(null);

      const response = await fetch(
        `${API_URL}/api/penalty/evaluate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            invoice_amount:
              selectedInvoiceData.amount,
            due_date:
              selectedInvoiceData.due_date,
            payment_date:
              penaltyPaymentDate,
            penalty_rate: penaltyRate,
            permissible_delay_days:
              Number(permissibleDelayDays),
          }),
        }
      );

      const body = await response.json().catch(
        () => null
      );

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Penalty evaluation failed with ${response.status}`
        );
      }

      setPenaltyResult(body);
    } catch (err) {
      console.error(err);
      setPenaltyError(
        err.message ||
          "Unable to evaluate penalty."
      );
    } finally {
      setPenaltyLoading(false);
    }
  }

  // =========================================================
  // LOGOUT
  // =========================================================

  async function handleLogout() {
    try {
      await signOut();
    } catch (err) {
      console.error(err);
    }
  }

  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <main className="dashboard-page">
        <div className="dashboard-container">
          <div className="dashboard-loading">
            <p className="section-eyebrow">
              ZYPHER CAPITAL
            </p>
            <h1>Command Center</h1>
            <p>
              Loading your financial intelligence...
            </p>
          </div>
        </div>
      </main>
    );
  }

  // =========================================================
  // CONNECTION ERROR
  // =========================================================

  if (error || !financialState) {
    return (
      <main className="dashboard-page">
        <div className="dashboard-container">
          <section className="dashboard-error">
            <p className="section-eyebrow">
              CONNECTION ERROR
            </p>

            <h1>Backend unavailable</h1>

            <p>
              {error ||
                "No financial state was returned by the backend."}
            </p>

            <button
              className="dashboard-button"
              onClick={fetchFinancialState}
            >
              Retry connection
            </button>
          </section>
        </div>
      </main>
    );
  }

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <main className="dashboard-page">
      <div className="dashboard-container">

        {/* HEADER */}
        <header className="dashboard-header">
          <div>
            <p className="section-eyebrow">
              ZYPHER CAPITAL
            </p>

            <h1>Command Center</h1>

            <p className="dashboard-subtitle">
              One connected layer for liquidity,
              risk and financial decisions.
            </p>
          </div>

          <div className="dashboard-header-actions">
            <span className="dashboard-user">
              {user?.email || "Authenticated user"}
            </span>

            <button
              className="dashboard-button secondary"
              onClick={handleLogout}
            >
              Log out
            </button>
          </div>
        </header>

        {/* NAV */}
        <nav className="dashboard-quick-nav">
          <a href="#forecast">Forecast</a>
          <a href="#supplier-intelligence">
            Supplier Intelligence
          </a>
          <a href="#decision-engine">
            Decision Engine
          </a>
          <a href="#reoptimization">
            Re-optimization
          </a>
          <a href="#advanced-engines">
            Financial Engines
          </a>
        </nav>

        {/* CASH */}
        <section className="dashboard-grid">
          <article className="dashboard-card primary-stat">
            <span>Total Bank Balance</span>
            <strong>
              {formatCurrency(
                financialState.current_cash
              )}
            </strong>
            <small>
              Current available cash position
            </small>
          </article>

          <article className="dashboard-card">
            <span>Restricted Cash</span>
            <strong>
              {formatCurrency(
                financialState.restricted_cash
              )}
            </strong>
            <small>
              Funds reserved from deployment
            </small>
          </article>

          <article className="dashboard-card">
            <span>Protected Cash</span>
            <strong>
              {formatCurrency(
                financialState.protected_cash
              )}
            </strong>
            <small>
              Liquidity protection buffer
            </small>
          </article>

          <article className="dashboard-card deployable">
            <span>Safe to Deploy</span>
            <strong>
              {formatCurrency(
                financialState.deployable_cash
              )}
            </strong>
            <small>
              Capital currently available
            </small>
          </article>
        </section>

        {/* OVERVIEW */}
        <section className="dashboard-section">
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              FINANCIAL OVERVIEW
            </p>
            <h2>Portfolio snapshot</h2>
          </div>

          <div className="overview-grid">
            <div className="overview-item">
              <span>Invoices</span>
              <strong>
                {financialState.invoice_count}
              </strong>
            </div>

            <div className="overview-item">
              <span>Receivables</span>
              <strong>
                {financialState.receivable_count}
              </strong>
            </div>

            <div className="overview-item">
              <span>Obligations</span>
              <strong>
                {financialState.obligation_count}
              </strong>
            </div>

            <div className="overview-item">
              <span>Data as of</span>
              <strong>
                {formatDate(financialState.as_of_date)}
              </strong>
            </div>
          </div>
        </section>

        {/* FORECAST */}
        <section
          id="forecast"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              FORECAST & SCENARIOS
            </p>
            <h2>Project future liquidity</h2>
            <p className="dashboard-section-description">
              Generate the real deterministic cash-flow
              forecast and inspect reserve pressure.
            </p>
          </div>

          <div className="tool-panel">
            <div className="tool-controls">
              <div className="form-field">
                <label htmlFor="forecastDays">
                  Horizon
                </label>
                <input
                  id="forecastDays"
                  type="number"
                  min="1"
                  max="365"
                  value={forecastDays}
                  onChange={(event) =>
                    setForecastDays(
                      event.target.value
                    )
                  }
                />
              </div>

              <button
                className="dashboard-button"
                onClick={runForecast}
                disabled={forecastLoading}
              >
                {forecastLoading
                  ? "Running..."
                  : "Run forecast"}
              </button>
            </div>

            {forecastError && (
              <p className="form-message error-message">
                {forecastError}
              </p>
            )}

            {forecast && (
              <>
                <div className="result-grid">
                  <div className="result-item">
                    <span>Minimum Cash</span>
                    <strong>
                      {formatCurrency(
                        forecast.minimum_cash
                      )}
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Reserve</span>
                    <strong>
                      {formatCurrency(
                        forecast.reserve_requirement
                      )}
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Survival</span>
                    <strong>
                      {
                        forecast.survival_horizon_days
                      }{" "}
                      days
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Reserve Breach</span>
                    <strong>
                      {forecast.reserve_breach
                        ? "YES"
                        : "NO"}
                    </strong>
                  </div>
                </div>

                <div className="forecast-preview">
                  <div className="forecast-preview-header">
                    <span>
                      Projected cash
                    </span>
                    <span>
                      {forecast.days?.length || 0} days
                    </span>
                  </div>

                  <div className="forecast-list">
                    {(forecast.days || [])
                      .slice(0, 8)
                      .map((day) => (
                        <div
                          className="forecast-row"
                          key={day.date}
                        >
                          <span>
                            {formatDate(day.date)}
                          </span>

                          <strong>
                            {formatCurrency(
                              day.projected_cash
                            )}
                          </strong>
                        </div>
                      ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </section>

        {/* SUPPLIER INTELLIGENCE */}
        <section
          id="supplier-intelligence"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              SUPPLIER INTELLIGENCE
            </p>

            <h2>Supplier risk network</h2>

            <p className="dashboard-section-description">
              Analyze supplier criticality, distress,
              disruption and cascade risk through the
              Supplier Intelligence Agent.
            </p>
          </div>

          <div className="tool-panel">
            <div className="tool-controls">
              <div className="form-field">
                <label htmlFor="selectedSupplier">
                  Supplier
                </label>

                <select
                  id="selectedSupplier"
                  value={selectedSupplier}
                  onChange={(event) => {
                    setSelectedSupplier(
                      event.target.value
                    );
                    setSupplierRisk(null);
                    setSupplierRiskError("");
                  }}
                  disabled={
                    supplierLoading ||
                    suppliers.length === 0
                  }
                >
                  <option value="">
                    {supplierLoading
                      ? "Loading suppliers..."
                      : suppliers.length === 0
                        ? "No suppliers"
                        : "Select supplier"}
                  </option>

                  {suppliers.map((supplier) => (
                    <option
                      key={supplier.supplier_id}
                      value={supplier.supplier_id}
                    >
                      {supplier.supplier_id} —{" "}
                      {supplier.name}
                    </option>
                  ))}
                </select>
              </div>

              <button
                className="dashboard-button"
                onClick={runSupplierRisk}
                disabled={
                  supplierRiskLoading ||
                  !selectedSupplier
                }
              >
                {supplierRiskLoading
                  ? "Analyzing..."
                  : "Analyze supplier risk"}
              </button>
            </div>

            {supplierError && (
              <p className="form-message error-message">
                {supplierError}
              </p>
            )}

            {supplierRiskError && (
              <p className="form-message error-message">
                {supplierRiskError}
              </p>
            )}

            {supplierRisk?.risk && (
              <div className="risk-result">
                <div className="risk-result-header">
                  <div>
                    <span className="section-eyebrow">
                      SUPPLIER RISK
                    </span>

                    <h3>
                      {
                        supplierRisk.risk
                          .supplier_name
                      }
                    </h3>
                  </div>

                  <span
                    className={`risk-badge ${riskClass(
                      supplierRisk.risk.risk_level
                    )}`}
                  >
                    {
                      supplierRisk.risk
                        .risk_level
                    }
                  </span>
                </div>

                <div className="result-grid">
                  <div className="result-item">
                    <span>Criticality</span>
                    <strong>
                      {formatNumber(
                        supplierRisk.risk
                          .criticality_score
                      )}
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Distress</span>
                    <strong>
                      {formatNumber(
                        supplierRisk.risk
                          .distress_score
                      )}
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Disruption</span>
                    <strong>
                      {(
                        Number(
                          supplierRisk.risk
                            .disruption_probability
                        ) * 100
                      ).toFixed(1)}
                      %
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Cascade Risk</span>
                    <strong>
                      {formatNumber(
                        supplierRisk.risk
                          .cascade_risk_score
                      )}
                    </strong>
                  </div>
                </div>

                <div className="supplier-risk-details">
                  <span>
                    Dependencies:{" "}
                    {
                      supplierRisk.risk
                        .dependency_count
                    }
                  </span>

                  <span>
                    Affected suppliers:{" "}
                    {
                      supplierRisk.risk
                        .affected_suppliers
                        ?.length || 0
                    }
                  </span>

                  <span>
                    Data confidence:{" "}
                    {
                      supplierRisk.risk
                        .data_confidence
                    }
                    %
                  </span>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* DECISION ENGINE */}
        <section
          id="decision-engine"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              DECISION ENGINE
            </p>

            <h2>Generate and evaluate actions</h2>

            <p className="dashboard-section-description">
              Generate candidate payment/financing actions,
              then run them through hard constraints and
              deterministic scoring.
            </p>
          </div>

          <div className="tool-panel">
            <div className="tool-controls">
              <div className="form-field invoice-selector">
                <label htmlFor="selectedInvoice">
                  Invoice
                </label>

                <select
                  id="selectedInvoice"
                  value={selectedInvoice}
                  onChange={(event) => {
                    setSelectedInvoice(
                      event.target.value
                    );
                    setDecisionResult(null);
                    setEvaluationResult(null);
                    setDecisionError("");
                    setEvaluationError("");
                  }}
                  disabled={
                    invoiceLoading ||
                    invoices.length === 0
                  }
                >
                  <option value="">
                    {invoiceLoading
                      ? "Loading invoices..."
                      : "Select invoice"}
                  </option>

                  {unpaidInvoices.map((invoice) => (
                    <option
                      key={invoice.invoice_id}
                      value={invoice.invoice_id}
                    >
                      {invoice.invoice_id} —{" "}
                      {formatCurrency(
                        invoice.amount
                      )}
                  </option>
                  ))}
                </select>
              </div>

              <button
                className="dashboard-button"
                onClick={runDecisionEngine}
                disabled={
                  decisionLoading ||
                  !selectedInvoice
                }
              >
                {decisionLoading
                  ? "Generating..."
                  : "Generate actions"}
              </button>
            </div>

            {invoiceError && (
              <p className="form-message error-message">
                {invoiceError}
              </p>
            )}

            {decisionError && (
              <p className="form-message error-message">
                {decisionError}
              </p>
            )}

            {decisionResult && (
              <>
                <div className="decision-result">
                  <div className="decision-result-header">
                    <div>
                      <span className="section-eyebrow">
                        CANDIDATE ACTIONS
                      </span>

                      <h3>
                        {
                          decisionResult.invoice
                            ?.invoice_id
                        }
                      </h3>
                    </div>

                    <strong>
                      {formatCurrency(
                        decisionResult.invoice
                          ?.amount
                      )}
                    </strong>
                  </div>

                  <div className="action-list">
                    {(
                      decisionResult.actions || []
                    ).map((action, index) => (
                      <div
                        className="action-row action-row-selectable"
                        key={`${action.action_type}-${index}`}
                      >
                        <div>
                          <span>
                            {formatActionType(
                              action.action_type
                            )}
                          </span>

                          <small>
                            Scheduled:{" "}
                            {formatDate(
                              action.scheduled_date
                            )}
                          </small>
                        </div>

                        <div>
                          <strong>
                            {formatCurrency(
                              action.amount
                            )}
                          </strong>

                          <button
                            className="inline-button"
                            onClick={() => {
                              setSelectedAction(
                                action.action_type
                              );
                              evaluateSelectedAction(
                                action.action_type
                              );
                            }}
                            disabled={
                              evaluationLoading
                            }
                          >
                            Evaluate
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {evaluationError && (
                  <p className="form-message error-message">
                    {evaluationError}
                  </p>
                )}

                {evaluationResult && (
                  <div className="evaluation-result">
                    <div className="evaluation-header">
                      <div>
                        <span className="section-eyebrow">
                          PLAN EVALUATION
                        </span>

                        <h3>
                          {
                            evaluationResult
                              .selected_action
                              ?.action_type
                          }
                        </h3>
                      </div>

                      <span
                        className={
                          evaluationResult.feasible
                            ? "status-badge success"
                            : "status-badge danger"
                        }
                      >
                        {evaluationResult.feasible
                          ? "FEASIBLE"
                          : "REJECTED"}
                      </span>
                    </div>

                    <div className="result-grid">
                      <div className="result-item">
                        <span>Plan Score</span>
                        <strong>
                          {
                            evaluationResult.score
                          }
                        </strong>
                      </div>

                      <div className="result-item">
                        <span>Action Score</span>
                        <strong>
                          {
                            evaluationResult.action_score
                          }
                        </strong>
                      </div>

                      <div className="result-item">
                        <span>Total Cost</span>
                        <strong>
                          {formatCurrency(
                            evaluationResult
                              .metrics?.total_cost
                          )}
                        </strong>
                      </div>

                      <div className="result-item">
                        <span>Reserve Violations</span>
                        <strong>
                          {
                            evaluationResult
                              .metrics
                              ?.reserve_violations
                          }
                        </strong>
                      </div>
                    </div>

                    <div className="constraint-list">
                      {(evaluationResult.constraints ||
                        []).map((item) => (
                        <div
                          className={`constraint-row ${
                            item.valid
                              ? "valid"
                              : "invalid"
                          }`}
                          key={item.constraint}
                        >
                          <span>
                            {item.valid
                              ? "✓"
                              : "✕"}{" "}
                            {item.constraint}
                          </span>

                          <small>
                            {item.reason}
                          </small>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </section>

        {/* RE-OPTIMIZATION */}
        <section
          id="reoptimization"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              EVENT-DRIVEN RE-OPTIMIZATION
            </p>

            <h2>React to a financial event</h2>

            <p className="dashboard-section-description">
              Simulate an invoice becoming more urgent,
              then compare the priority queue before and
              after the event.
            </p>
          </div>

          <div className="tool-panel">
            <div className="event-panel">
              <div className="event-panel-header">
                <p className="section-eyebrow">
                  SIMULATED EVENT
                </p>

                <h3>
                  Invoice due date advanced
                </h3>

                <p>
                  Select an unpaid invoice and move its
                  due date closer to today. The priority
                  engine recalculates urgency and rebuilds
                  the queue.
                </p>
              </div>

              <div className="tool-controls">
                <div className="form-field">
                  <label htmlFor="reoptimizationInvoice">
                    Invoice
                  </label>

                  <select
                    id="reoptimizationInvoice"
                    value={reoptimizationInvoice}
                    onChange={(event) => {
                      setReoptimizationInvoice(
                        event.target.value
                      );
                      setReoptimization(null);
                      setReoptimizationError("");
                    }}
                    disabled={
                      invoiceLoading ||
                      unpaidInvoices.length === 0
                    }
                  >
                    <option value="">
                      {invoiceLoading
                        ? "Loading..."
                        : "Select invoice"}
                    </option>

                    {unpaidInvoices.map((invoice) => (
                      <option
                        key={invoice.invoice_id}
                        value={invoice.invoice_id}
                      >
                        {invoice.invoice_id} —{" "}
                        {formatCurrency(
                          invoice.amount
                        )}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-field">
                  <label htmlFor="advanceDays">
                    Advance by
                  </label>

                  <input
                    id="advanceDays"
                    type="number"
                    min="1"
                    max="365"
                    value={advanceDays}
                    onChange={(event) =>
                      setAdvanceDays(
                        event.target.value
                      )
                    }
                  />

                  <small>days</small>
                </div>

                <button
                  className="dashboard-button"
                  onClick={runReoptimization}
                  disabled={
                    reoptimizationLoading ||
                    !selectedReoptimizationInvoice
                  }
                >
                  {reoptimizationLoading
                    ? "Re-optimizing..."
                    : "Simulate event & re-optimize"}
                </button>
              </div>

              {reoptimizationError && (
                <p className="form-message error-message">
                  {reoptimizationError}
                </p>
              )}
            </div>

            {reoptimization && (
              <>
                <div className="event-result">
                  <p className="section-eyebrow">
                    EVENT DETECTED
                  </p>

                  <h3>
                    {
                      reoptimization.event
                        ?.description
                    }
                  </h3>

                  <p>
                    The event changed invoice urgency,
                    and the deterministic priority queue
                    was rebuilt.
                  </p>
                </div>

                <div className="result-grid">
                  <div className="result-item">
                    <span>Before Rank</span>
                    <strong>
                      #
                      {(
                        reoptimization.before ||
                        []
                      ).findIndex(
                        (item) =>
                          item.invoice_id ===
                          reoptimization.event
                            ?.invoice_id
                      ) + 1}
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>After Rank</span>
                    <strong>
                      #
                      {(
                        reoptimization.after ||
                        []
                      ).findIndex(
                        (item) =>
                          item.invoice_id ===
                          reoptimization.event
                            ?.invoice_id
                      ) + 1}
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Before Urgency</span>
                    <strong>
                      {
                        reoptimization
                          .target_invoice
                          ?.before?.urgency
                      }
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>After Urgency</span>
                    <strong>
                      {
                        reoptimization
                          .target_invoice
                          ?.after?.urgency
                      }
                    </strong>
                  </div>
                </div>

                <div className="decision-result">
                  <div className="decision-result-header">
                    <div>
                      <span className="section-eyebrow">
                        UPDATED PRIORITY QUEUE
                      </span>

                      <h3>
                        After event
                      </h3>
                    </div>

                    <strong>
                      {reoptimization.after
                        ?.length || 0}{" "}
                      invoices
                    </strong>
                  </div>

                  <div className="action-list">
                    {(
                      reoptimization.after ||
                      []
                    )
                      .slice(0, 10)
                      .map((item, index) => (
                        <div
                          className="action-row"
                          key={item.invoice_id}
                        >
                          <div>
                            <span>
                              #{index + 1}{" "}
                              {item.invoice_id}
                            </span>

                            <small>
                              Urgency:{" "}
                              {item.urgency}
                            </small>
                          </div>

                          <strong>
                            Score: {item.score}
                          </strong>
                        </div>
                      ))}
                  </div>
                </div>

                {reoptimization.changes
                  ?.length > 0 && (
                  <div className="tool-panel">
                    <p className="section-eyebrow">
                      WHAT CHANGED
                    </p>

                    <div className="action-list">
                      {reoptimization.changes
                        .slice(0, 10)
                        .map((change) => (
                          <div
                            className="action-row"
                            key={change.invoice_id}
                          >
                            <div>
                              <span>
                                {
                                  change.invoice_id
                                }
                              </span>

                              <small>
                                Rank #
                                {
                                  change.previous_rank
                                }{" "}
                                → #
                                {
                                  change.new_rank
                                }
                              </small>
                            </div>

                            <strong>
                              {change.rank_change >
                              0
                                ? `↑ ${change.rank_change}`
                                : change.rank_change <
                                    0
                                  ? `↓ ${Math.abs(
                                      change.rank_change
                                    )}`
                                  : "—"}
                            </strong>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </section>

        {/* ADVANCED ENGINES */}
        <section
          id="advanced-engines"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              FINANCIAL ENGINES
            </p>

            <h2>Financing, discounts & penalties</h2>

            <p className="dashboard-section-description">
              Directly exercise the supporting deterministic
              financial engines used by the Decision Engine.
            </p>
          </div>

          {/* FINANCING */}
          <div className="tool-panel advanced-panel">
            <div className="dashboard-section-heading">
              <p className="section-eyebrow">
                FINANCING ENGINE
              </p>

              <h3>
                Compare financing options
              </h3>
            </div>

            <div className="tool-controls">
              <div className="form-field">
                <label htmlFor="financingAmount">
                  Amount
                </label>

                <input
                  id="financingAmount"
                  type="number"
                  min="1"
                  value={financingAmount}
                  onChange={(event) =>
                    setFinancingAmount(
                      event.target.value
                    )
                  }
                  placeholder="250000"
                />
              </div>

              <div className="form-field">
                <label htmlFor="financingDays">
                  Financing days
                </label>

                <input
                  id="financingDays"
                  type="number"
                  min="0"
                  value={financingDays}
                  onChange={(event) =>
                    setFinancingDays(
                      event.target.value
                    )
                  }
                />
              </div>

              <button
                className="dashboard-button"
                onClick={runFinancingComparison}
                disabled={
                  financingComparisonLoading
                }
              >
                {financingComparisonLoading
                  ? "Comparing..."
                  : "Compare options"}
              </button>
            </div>

            {financingError && (
              <p className="form-message error-message">
                {financingError}
              </p>
            )}

            {financingComparisonError && (
              <p className="form-message error-message">
                {financingComparisonError}
              </p>
            )}

            {financingComparison && (
              <>
                <div className="advanced-list">
                  {(
                    financingComparison.evaluations ||
                    []
                  ).map((item) => (
                    <div
                      className="advanced-row"
                      key={item.option_id}
                    >
                      <div>
                        <strong>
                          {item.option_id}
                        </strong>

                        <small>
                          {item.funding_source} •{" "}
                          {item.reason}
                        </small>
                      </div>

                      <div>
                        <strong>
                          {formatCurrency(
                            item.total_cost
                          )}
                        </strong>

                        <small>
                          {item.eligible
                            ? "Eligible"
                            : "Ineligible"}
                        </small>
                      </div>
                    </div>
                  ))}
                </div>

                {financingComparison.best_option && (
                  <div className="highlight-result">
                    Best option:{" "}
                    {
                      financingComparison
                        .best_option.option_id
                    }{" "}
                    —{" "}
                    {formatCurrency(
                      financingComparison
                        .best_option.total_cost
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* DISCOUNT + PENALTY */}
          <div className="advanced-grid">
            <div className="tool-panel advanced-panel">
              <p className="section-eyebrow">
                DISCOUNT ENGINE
              </p>

              <h3>Evaluate early-payment savings</h3>

              <div className="form-field">
                <label htmlFor="discountInvoice">
                  Invoice
                </label>

                <select
                  id="discountInvoice"
                  value={selectedInvoice}
                  onChange={(event) =>
                    setSelectedInvoice(
                      event.target.value
                    )
                  }
                >
                  <option value="">
                    Select invoice
                  </option>

                  {invoices.map((invoice) => (
                    <option
                      key={invoice.invoice_id}
                      value={invoice.invoice_id}
                    >
                      {invoice.invoice_id}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-field">
                <label htmlFor="discountRate">
                  Discount rate
                </label>

                <input
                  id="discountRate"
                  type="number"
                  min="0"
                  max="0.99"
                  step="0.001"
                  value={discountRate}
                  onChange={(event) =>
                    setDiscountRate(
                      event.target.value
                    )
                  }
                />
              </div>

              <div className="form-field">
                <label htmlFor="discountDeadline">
                  Discount deadline
                </label>

                <input
                  id="discountDeadline"
                  type="date"
                  value={discountDeadline}
                  onChange={(event) =>
                    setDiscountDeadline(
                      event.target.value
                    )
                  }
                />
              </div>

              <div className="form-field">
                <label htmlFor="discountPaymentDate">
                  Payment date
                </label>

                <input
                  id="discountPaymentDate"
                  type="date"
                  value={discountPaymentDate}
                  onChange={(event) =>
                    setDiscountPaymentDate(
                      event.target.value
                    )
                  }
                />
              </div>

              <button
                className="dashboard-button"
                onClick={runDiscountEvaluation}
                disabled={discountLoading}
              >
                {discountLoading
                  ? "Evaluating..."
                  : "Evaluate discount"}
              </button>

              {discountError && (
                <p className="form-message error-message">
                  {discountError}
                </p>
              )}

              {discountResult && (
                <div className="highlight-result">
                  <strong>
                    {discountResult.eligible
                      ? `Savings: ${formatCurrency(
                          discountResult.discount_value
                        )}`
                      : "Not eligible"}
                  </strong>

                  <small>
                    {discountResult.reason}
                  </small>
                </div>
              )}
            </div>

            <div className="tool-panel advanced-panel">
              <p className="section-eyebrow">
                PENALTY ENGINE
              </p>

              <h3>Evaluate late-payment impact</h3>

              <div className="form-field">
                <label htmlFor="penaltyPaymentDate">
                  Proposed payment date
                </label>

                <input
                  id="penaltyPaymentDate"
                  type="date"
                  value={penaltyPaymentDate}
                  onChange={(event) =>
                    setPenaltyPaymentDate(
                      event.target.value
                    )
                  }
                />
              </div>

              <div className="form-field">
                <label htmlFor="penaltyRate">
                  Daily penalty rate
                </label>

                <input
                  id="penaltyRate"
                  type="number"
                  min="0"
                  max="0.99"
                  step="0.0001"
                  value={penaltyRate}
                  onChange={(event) =>
                    setPenaltyRate(
                      event.target.value
                    )
                  }
                />
              </div>

              <div className="form-field">
                <label htmlFor="permissibleDelayDays">
                  Permissible delay
                </label>

                <input
                  id="permissibleDelayDays"
                  type="number"
                  min="0"
                  value={permissibleDelayDays}
                  onChange={(event) =>
                    setPermissibleDelayDays(
                      event.target.value
                    )
                  }
                />
              </div>

              <button
                className="dashboard-button"
                onClick={runPenaltyEvaluation}
                disabled={penaltyLoading}
              >
                {penaltyLoading
                  ? "Evaluating..."
                  : "Evaluate penalty"}
              </button>

              {penaltyError && (
                <p className="form-message error-message">
                  {penaltyError}
                </p>
              )}

              {penaltyResult && (
                <div className="highlight-result">
                  <strong>
                    Penalty:{" "}
                    {formatCurrency(
                      penaltyResult.penalty_amount
                    )}
                  </strong>

                  <small>
                    Late days:{" "}
                    {penaltyResult.late_days} • Risk:{" "}
                    {penaltyResult.penalty_risk}
                  </small>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* LIVE STATUS */}
        <section className="dashboard-footer-card">
          <div>
            <p className="section-eyebrow">
              SYSTEM STATUS
            </p>

            <h2>
              Financial intelligence is connected.
            </h2>

            <p>
              State, forecast, supplier risk, decision
              generation, plan evaluation, financial
              engines and event-driven re-optimization
              are available from this command center.
            </p>
          </div>

          <button
            className="dashboard-button"
            onClick={() => {
              fetchFinancialState();
              fetchInvoices();
              fetchSuppliers();
              fetchFinancingOptions();
            }}
          >
            Refresh all
          </button>
        </section>
      </div>
    </main>
  );
}

export default Dashboard;
