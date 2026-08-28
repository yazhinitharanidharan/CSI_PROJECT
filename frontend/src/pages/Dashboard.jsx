import { useCallback, useEffect, useState } from "react";
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

function formatActionType(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .toUpperCase();
}

function Dashboard() {
  const { user, signOut } = useAuth();

  // ---------------------------------------------------------
  // State
  // ---------------------------------------------------------

  const [financialState, setFinancialState] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [suppliers, setSuppliers] = useState([]);

  const [forecast, setForecast] = useState(null);
  const [decisionResult, setDecisionResult] = useState(null);
  const [reoptimization, setReoptimization] = useState(null);

  const [forecastDays, setForecastDays] = useState(30);
  const [selectedInvoice, setSelectedInvoice] = useState("");

  const [loading, setLoading] = useState(true);
  const [invoiceLoading, setInvoiceLoading] = useState(true);
  const [supplierLoading, setSupplierLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [reoptimizationLoading, setReoptimizationLoading] =
    useState(false);

  const [error, setError] = useState("");
  const [invoiceError, setInvoiceError] = useState("");
  const [supplierError, setSupplierError] = useState("");
  const [forecastError, setForecastError] = useState("");
  const [decisionError, setDecisionError] = useState("");
  const [reoptimizationError, setReoptimizationError] =
    useState("");

  // ---------------------------------------------------------
  // Financial state
  // ---------------------------------------------------------

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

      const data = await response.json();
      setFinancialState(data);
    } catch (err) {
      console.error(err);
      setError(
        "Unable to connect to the backend. Make sure FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // ---------------------------------------------------------
  // Invoices
  // ---------------------------------------------------------

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
      const loadedInvoices = Array.isArray(data.invoices)
        ? data.invoices
        : [];

      setInvoices(loadedInvoices);

      setSelectedInvoice((current) => {
        if (current) {
          const stillExists = loadedInvoices.some(
            (invoice) => invoice.invoice_id === current
          );

          return stillExists
            ? current
            : loadedInvoices[0]?.invoice_id || "";
        }

        return loadedInvoices[0]?.invoice_id || "";
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

  // ---------------------------------------------------------
  // Suppliers
  // ---------------------------------------------------------

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

      setSuppliers(
        Array.isArray(data.suppliers)
          ? data.suppliers
          : []
      );
    } catch (err) {
      console.error(err);
      setSupplierError(
        err.message || "Unable to load suppliers."
      );
    } finally {
      setSupplierLoading(false);
    }
  }, []);

  // ---------------------------------------------------------
  // Initial loading
  // ---------------------------------------------------------

  useEffect(() => {
    fetchFinancialState();
    fetchInvoices();
    fetchSuppliers();
  }, [
    fetchFinancialState,
    fetchInvoices,
    fetchSuppliers,
  ]);

  // ---------------------------------------------------------
  // Forecast
  // ---------------------------------------------------------

  async function runForecast() {
    const days = Number(forecastDays);

    if (!Number.isInteger(days) || days < 1 || days > 365) {
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

      const body = await response.json().catch(() => null);

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

  // ---------------------------------------------------------
  // Decision Engine
  // ---------------------------------------------------------

  async function runDecisionEngine() {
    if (!selectedInvoice) {
      setDecisionError("Please select an invoice first.");
      return;
    }

    try {
      setDecisionLoading(true);
      setDecisionError("");
      setDecisionResult(null);

      const response = await fetch(
        `${API_URL}/api/decision/actions?invoice_id=${encodeURIComponent(
          selectedInvoice
        )}`,
        {
          method: "POST",
        }
      );

      const body = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Decision request failed with ${response.status}`
        );
      }

      setDecisionResult(body);
    } catch (err) {
      console.error(err);
      setDecisionError(
        err.message ||
          "Unable to evaluate invoice actions."
      );
    } finally {
      setDecisionLoading(false);
    }
  }

  // ---------------------------------------------------------
  // Re-optimization
  // ---------------------------------------------------------

  async function runReoptimization() {
    try {
      setReoptimizationLoading(true);
      setReoptimizationError("");
      setReoptimization(null);

      const response = await fetch(
        `${API_URL}/api/reoptimize`,
        {
          method: "POST",
        }
      );

      const body = await response.json().catch(() => null);

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

  // ---------------------------------------------------------
  // Logout
  // ---------------------------------------------------------

  async function handleLogout() {
    try {
      await signOut();
    } catch (err) {
      console.error(err);
    }
  }

  // ---------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------

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

  // ---------------------------------------------------------
  // Connection error
  // ---------------------------------------------------------

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

  // ---------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------

  return (
    <main className="dashboard-page">
      <div className="dashboard-container">

        {/* =================================================
            HEADER
        ================================================= */}

        <header className="dashboard-header">
          <div>
            <p className="section-eyebrow">
              ZYPHER CAPITAL
            </p>

            <h1>Command Center</h1>

            <p className="dashboard-subtitle">
              Your financial intelligence at a glance.
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

        {/* =================================================
            QUICK NAVIGATION
        ================================================= */}

        <nav className="dashboard-quick-nav">
          <a href="#forecast">Forecast</a>
          <a href="#decision-engine">
            Decision Engine
          </a>
          <a href="#suppliers">
            Supplier Intelligence
          </a>
          <a href="#reoptimization">
            Re-optimization
          </a>
        </nav>

        {/* =================================================
            CASH POSITION
        ================================================= */}

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

        {/* =================================================
            FINANCIAL OVERVIEW
        ================================================= */}

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
                {financialState.as_of_date}
              </strong>
            </div>
          </div>
        </section>

        {/* =================================================
            FORECAST & SCENARIOS
        ================================================= */}

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
              Run the deterministic cash-flow forecast
              against the current financial state.
            </p>
          </div>

          <div className="tool-panel">
            <div className="tool-controls">
              <div className="form-field">
                <label htmlFor="forecastDays">
                  Forecast horizon
                </label>

                <input
                  id="forecastDays"
                  type="number"
                  min="1"
                  max="365"
                  value={forecastDays}
                  onChange={(event) =>
                    setForecastDays(event.target.value)
                  }
                />
              </div>

              <button
                className="dashboard-button"
                onClick={runForecast}
                disabled={forecastLoading}
              >
                {forecastLoading
                  ? "Running forecast..."
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
                    <span>Reserve Requirement</span>

                    <strong>
                      {formatCurrency(
                        forecast.reserve_requirement
                      )}
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Survival Horizon</span>

                    <strong>
                      {forecast.survival_horizon_days} days
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
                    <span>Projected cash</span>

                    <span>
                      {forecast.days?.length || 0} days
                    </span>
                  </div>

                  <div className="forecast-list">
                    {(forecast.days || [])
                      .filter((_, index, days) => {
                        if (days.length <= 3) {
                          return true;
                        }

                        return (
                          index === 0 ||
                          index ===
                            Math.floor(days.length / 2) ||
                          index === days.length - 1
                        );
                      })
                      .map((day) => (
                        <div
                          className="forecast-row"
                          key={day.date}
                        >
                          <span>{day.date}</span>

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

        {/* =================================================
            DECISION ENGINE
        ================================================= */}

        <section
          id="decision-engine"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              DECISION ENGINE
            </p>

            <h2>Evaluate invoice actions</h2>

            <p className="dashboard-section-description">
              Generate the actual candidate actions supported
              by the deterministic Decision Engine.
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
                    setDecisionError("");
                    setDecisionResult(null);
                  }}
                  disabled={
                    invoiceLoading ||
                    invoices.length === 0
                  }
                >
                  <option value="">
                    {invoiceLoading
                      ? "Loading invoices..."
                      : invoices.length === 0
                        ? "No invoices available"
                        : "Select an invoice"}
                  </option>

                  {invoices.map((invoice) => (
                    <option
                      key={invoice.invoice_id}
                      value={invoice.invoice_id}
                    >
                      {invoice.invoice_id} —{" "}
                      {formatCurrency(invoice.amount)}
                    </option>
                  ))}
                </select>
              </div>

              <button
                className="dashboard-button"
                onClick={runDecisionEngine}
                disabled={
                  decisionLoading ||
                  invoiceLoading ||
                  !selectedInvoice
                }
              >
                {decisionLoading
                  ? "Evaluating..."
                  : "Evaluate actions"}
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
              <div className="decision-result">
                <div className="decision-result-header">
                  <div>
                    <span className="section-eyebrow">
                      SELECTED INVOICE
                    </span>

                    <h3>
                      {decisionResult.invoice?.invoice_id}
                    </h3>
                  </div>

                  <strong>
                    {formatCurrency(
                      decisionResult.invoice?.amount
                    )}
                  </strong>
                </div>

                <div className="action-list">
                  {(decisionResult.actions || []).map(
                    (action, index) => (
                      <div
                        className="action-row"
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
                            {action.scheduled_date}
                          </small>
                        </div>

                        <div>
                          <strong>
                            {formatCurrency(action.amount)}
                          </strong>

                          <small>
                            {action.funding_source ||
                              "No funding source"}
                          </small>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* =================================================
            SUPPLIER INTELLIGENCE
        ================================================= */}

        <section
          id="suppliers"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              SUPPLIER INTELLIGENCE
            </p>

            <h2>Supplier network</h2>

            <p className="dashboard-section-description">
              Explore the supplier records currently
              available to the intelligence layer.
            </p>
          </div>

          {supplierError && (
            <p className="form-message error-message">
              {supplierError}
            </p>
          )}

          <div className="supplier-grid">
            {supplierLoading ? (
              <div className="tool-panel">
                Loading supplier data...
              </div>
            ) : suppliers.length === 0 ? (
              <div className="tool-panel">
                No supplier data available.
              </div>
            ) : (
              suppliers.map((supplier) => (
                <article
                  className="supplier-card"
                  key={supplier.supplier_id}
                >
                  <div className="supplier-card-top">
                    <span>
                      {supplier.supplier_id}
                    </span>

                    <span>
                      {supplier.category}
                    </span>
                  </div>

                  <h3>{supplier.name}</h3>

                  <div className="supplier-metrics">
                    <div>
                      <span>Reliability</span>

                      <strong>
                        {Math.round(
                          Number(
                            supplier.reliability_score || 0
                          ) * 100
                        )}
                        %
                      </strong>
                    </div>

                    <div>
                      <span>Lead time</span>

                      <strong>
                        {supplier.average_lead_time_days}{" "}
                        days
                      </strong>
                    </div>

                    <div>
                      <span>Terms</span>

                      <strong>
                        {supplier.payment_terms_days} days
                      </strong>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>

        {/* =================================================
            RE-OPTIMIZATION
        ================================================= */}

        <section
          id="reoptimization"
          className="dashboard-section"
        >
          <div className="dashboard-section-heading">
            <p className="section-eyebrow">
              RE-OPTIMIZATION
            </p>

            <h2>Adapt when conditions change</h2>

            <p className="dashboard-section-description">
              Re-rank unpaid invoices using the current
              financial state and deterministic priority engine.
            </p>
          </div>

          <div className="tool-panel">
            <div className="tool-controls">
              <button
                className="dashboard-button"
                onClick={runReoptimization}
                disabled={reoptimizationLoading}
              >
                {reoptimizationLoading
                  ? "Re-optimizing..."
                  : "Run re-optimization"}
              </button>
            </div>

            {reoptimizationError && (
              <p className="form-message error-message">
                {reoptimizationError}
              </p>
            )}

            {reoptimization && (
              <div className="decision-result">
                <div className="decision-result-header">
                  <div>
                    <span className="section-eyebrow">
                      UPDATED PRIORITY QUEUE
                    </span>

                    <h3>
                      {reoptimization.invoice_count || 0}{" "}
                      unpaid invoices re-ranked
                    </h3>
                  </div>

                  <strong>
                    {reoptimization.as_of_date}
                  </strong>
                </div>

                <div className="action-list">
                  {(
                    reoptimization.priorities || []
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
                            {item.priority?.urgency ??
                              "0"}
                          </small>
                        </div>

                        <div>
                          <strong>
                            Score: {item.score}
                          </strong>

                          <small>
                            Deterministic priority ranking
                          </small>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* =================================================
            LIVE DATA
        ================================================= */}

        <section className="dashboard-footer-card">
          <div>
            <p className="section-eyebrow">
              LIVE DATA
            </p>

            <h2>Financial state is connected.</h2>

            <p>
              Refresh the current financial state before
              running another forecast or decision evaluation.
            </p>
          </div>

          <button
            className="dashboard-button"
            onClick={fetchFinancialState}
          >
            Refresh data
          </button>
        </section>
      </div>
    </main>
  );
}

export default Dashboard;