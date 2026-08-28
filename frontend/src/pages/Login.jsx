import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
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

  function handleChange(e) {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();

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
    <main className="auth-page">
      <motion.div
        className="auth-shell"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        {/* LEFT BRAND PANEL */}
        <motion.section
          className="auth-brand-panel"
          initial={{ opacity: 0, x: -25 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          <Link to="/" className="auth-logo">
            ZYPHER<span>.</span>
          </Link>

          <div className="auth-brand-content">
            <p className="auth-eyebrow">
              AUTONOMOUS WORKING CAPITAL INTELLIGENCE
            </p>

            <h1>
              Capital decisions,
              <br />
              with clarity.
            </h1>

            <p>
              Understand your liquidity position, account for
              uncertainty, and know what capital can safely be
              deployed.
            </p>
          </div>

          <div className="auth-mini-card">
            <span>SAFE TO DEPLOY</span>

            <strong>₹6.4L</strong>

            <small>
              Continuously evaluated against liquidity risk
            </small>

            <div className="auth-status">
              <span className="auth-status-dot" />
              Decision engine active
            </div>
          </div>
        </motion.section>

        {/* RIGHT FORM PANEL */}
        <motion.section
          className="auth-form-panel"
          initial={{ opacity: 0, x: 25 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.15 }}
        >
          <div className="auth-form-container">
            <div className="auth-form-header">
              <p className="auth-form-eyebrow">WELCOME BACK</p>

              <h2>Sign in to Zypher</h2>

              <p>
                Access your liquidity command center.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="auth-form">
              <div className="auth-field">
                <label htmlFor="email">Email address</label>

                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>

              <div className="auth-field">
                <div className="auth-label-row">
                  <label htmlFor="password">Password</label>
                </div>

                <input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <motion.div
                  className="auth-message auth-error"
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {error}
                </motion.div>
              )}

              <motion.button
                type="submit"
                className="auth-submit"
                disabled={loading}
                whileHover={!loading ? { y: -2 } : {}}
                whileTap={!loading ? { scale: 0.98 } : {}}
              >
                {loading ? "Signing in..." : "Sign in"}
              </motion.button>
            </form>

            <div className="auth-divider">
              <span>SECURE ACCESS</span>
            </div>

            <p className="auth-switch">
              Don't have an account?{" "}
              <Link to="/signup">Create one</Link>
            </p>
          </div>
        </motion.section>
      </motion.div>
    </main>
  );
}

export default Login;