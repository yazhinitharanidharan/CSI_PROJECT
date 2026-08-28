import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../components/layout/Navbar";
import { useAuth } from "../hooks/useAuth";

function Login() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));

    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const { email, password } = formData;

    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      await signIn(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <Navbar />

      <main className="auth-shell">
        <section className="auth-card">
          <div className="auth-heading">
            <p className="section-eyebrow">ZYPHER CAPITAL</p>

            <h1>Welcome back</h1>

            <p>
              Sign in to continue to your financial intelligence command
              center.
            </p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-field">
              <label htmlFor="email">Email</label>

              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="password">Password</label>

              <input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
            </div>

            {error && (
              <p className="form-message error-message">
                {error}
              </p>
            )}

            <button
              className="auth-submit"
              type="submit"
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="auth-footer">
            <span>Don't have an account?</span>{" "}
            <Link to="/signup">Create one</Link>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Login;