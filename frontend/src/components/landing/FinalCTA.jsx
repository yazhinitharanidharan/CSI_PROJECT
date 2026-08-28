import { Link } from "react-router-dom";

function FinalCTA() {
  return (
    <section className="final-cta">
      <div className="final-cta-content">
        <p className="section-eyebrow">
          LIQUIDITY, WITH CLARITY
        </p>

        <h2>
          Know what you can
          <br />
          safely deploy.
        </h2>

        <p className="final-cta-description">
          Zypher Capital transforms financial uncertainty into
          informed capital decisions — continuously adapting
          as your business changes.
        </p>

        <div className="final-cta-actions">
          <Link to="/signup" className="primary-button">
            Enter Command Center
          </Link>

          <a href="#how-it-works" className="secondary-button">
            Explore how it works
          </a>
        </div>
      </div>
    </section>
  );
}

export default FinalCTA;