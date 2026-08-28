import { useEffect, useState } from "react";

const API_URL = "http://127.0.0.1:8000";

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function Dashboard() {
  const [financialState, setFinancialState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchFinancialState() {
      try {
        const response = await fetch(
          `${API_URL}/api/financial-state`
        );

        if (!response.ok) {
          throw new Error("Failed to fetch financial state");
        }

        const data = await response.json();

        setFinancialState(data);
      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchFinancialState();
  }, []);

  if (loading) {
    return (
      <main>
        <h1>Command Center</h1>
        <p>Loading financial intelligence...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main>
        <h1>Command Center</h1>
        <p>Unable to connect to backend.</p>
        <p>{error}</p>
      </main>
    );
  }

  return (
    <main>
      <h1>Command Center</h1>

      <p>Your financial intelligence dashboard.</p>

      <section>
        <h2>Cash Position</h2>

        <div>
          <h3>Total Bank Balance</h3>
          <p>
            {formatCurrency(financialState.current_cash)}
          </p>
        </div>

        <div>
          <h3>Restricted Cash</h3>
          <p>
            {formatCurrency(financialState.restricted_cash)}
          </p>
        </div>

        <div>
          <h3>Protected Cash</h3>
          <p>
            {formatCurrency(financialState.protected_cash)}
          </p>
        </div>

        <div>
          <h3>Safe to Deploy</h3>
          <p>
            {formatCurrency(financialState.deployable_cash)}
          </p>
        </div>
      </section>

      <section>
        <h2>Financial Overview</h2>

        <p>
          Invoices: {financialState.invoice_count}
        </p>

        <p>
          Receivables: {financialState.receivable_count}
        </p>

        <p>
          Obligations: {financialState.obligation_count}
        </p>
      </section>
    </main>
  );
}

export default Dashboard;