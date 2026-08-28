import { Link } from "react-router-dom";

function Navbar() {
  return (
    <header className="navbar">
      <Link to="/" className="navbar-logo">
        LiquidityOS
      </Link>

      <nav className="navbar-links">
        <a href="#how-it-works">How it works</a>
        <a href="#intelligence">Intelligence</a>
        <a href="#reoptimization">Re-optimization</a>
      </nav>

      <div className="navbar-actions">
        <Link to="/login" className="navbar-login">
          Log in
        </Link>

        <Link to="/signup" className="navbar-cta">
          Get started
        </Link>
      </div>
    </header>
  );
}

export default Navbar;