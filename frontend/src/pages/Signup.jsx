import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../components/layout/Navbar";
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

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));

    setError("");
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

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
    <div className="auth-page">
      <Navbar />

      <main className="auth-shell">
        <section className="auth-card signup-card">
          <div className="auth-heading">
            <p className="section-eyebrow">ZYPHER CAPITAL</p>

            <h1>Create your account</h1>

            <p>
              Build a smarter financial command center for your business.
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
                autoComplete="new-password"
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="confirmPassword">Confirm password</label>

              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Confirm your password"
                autoComplete="new-password"
                required
              />
            </div>

            {error && (
              <p className="form-message error-message">{error}</p>
            )}

            {success && (
              <p className="form-message success-message">{success}</p>
            )}

            <button
              className="auth-submit"
              type="submit"
              disabled={loading}
            >
              {loading ? "Creating account..." : "Create account"}
            </button>
          </form>

          <div className="auth-footer">
            <span>Already have an account?</span>{" "}
            <Link to="/login">Log in</Link>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Signup;