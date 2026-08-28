import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { useAuth } from "../hooks/useAuth";

function Signup() {
  const navigate = useNavigate();
  const { signUp } = useAuth();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    setError("");
    setSuccess("");
  }

  async function handleSubmit(e) {
    e.preventDefault();

    const { email, password, confirmPassword } = formData;

    if (!email || !password || !confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }

    if (password.length < 6) {
      setError("Password must contain at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccess("");

      const data = await signUp(email, password);

      if (data.session) {
        navigate("/dashboard");
      } else {
        setSuccess(
          "Account created successfully. Please check your email to verify your account."
        );
      }
    } catch (err) {
      setError(err.message || "Unable to create your account.");
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
              Turn uncertainty
              <br />
              into confidence.
            </h1>

            <p>
              Zypher evaluates your cash, receivables,
              obligations and financial uncertainty to help
              determine what you can safely deploy.
            </p>
          </div>

          <div className="auth-mini-card">
            <span>LIQUIDITY POSITION</span>

            <strong>₹24.8L</strong>

            <small>
              Current financial position under evaluation
            </small>

            <div className="auth-status">
              <span className="auth-status-dot" />
              Intelligence engine ready
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
              <p className="auth-form-eyebrow">
                GET STARTED
              </p>

              <h2>Create your account</h2>

              <p>
                Build a clearer view of your working capital.
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
                <label htmlFor="password">Password</label>

                <input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="At least 6 characters"
                  autoComplete="new-password"
                />
              </div>

              <div className="auth-field">
                <label htmlFor="confirmPassword">
                  Confirm password
                </label>

                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Repeat your password"
                  autoComplete="new-password"
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

              {success && (
                <motion.div
                  className="auth-message auth-success"
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {success}
                </motion.div>
              )}

              <motion.button
                type="submit"
                className="auth-submit"
                disabled={loading}
                whileHover={!loading ? { y: -2 } : {}}
                whileTap={!loading ? { scale: 0.98 } : {}}
              >
                {loading
                  ? "Creating account..."
                  : "Create account"}
              </motion.button>
            </form>

            <div className="auth-divider">
              <span>SECURE ACCESS</span>
            </div>

            <p className="auth-switch">
              Already have an account?{" "}
              <Link to="/login">Log in</Link>
            </p>
          </div>
        </motion.section>
      </motion.div>
    </main>
  );
}

export default Signup;