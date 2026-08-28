import { motion } from "motion/react";
import { Link } from "react-router-dom";

function Hero() {
  return (
    <section className="hero">
      <motion.div
        className="hero-content"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
      >
        <p className="hero-eyebrow">
          AUTONOMOUS WORKING CAPITAL INTELLIGENCE
        </p>

        <h1>
          Know what cash
          <br />
          you can safely deploy.
        </h1>

        <p className="hero-description">
          LiquidityOS evaluates cash, receivables, obligations,
          uncertainty and constraints to continuously determine
          your safest deployment decision.
        </p>

        <div className="hero-actions">
          <Link to="/signup" className="primary-button">
            Explore LiquidityOS
          </Link>

          <a href="#how-it-works" className="secondary-button">
            See how it works
          </a>
        </div>
      </motion.div>

      <motion.div
        className="hero-visual"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, delay: 0.2 }}
      >
        <div className="hero-dashboard-card">
          <span>SAFE TO DEPLOY</span>

          <strong>₹6.4L</strong>

          <small>
            Based on current liquidity conditions
          </small>
        </div>
      </motion.div>
    </section>
  );
}

export default Hero;