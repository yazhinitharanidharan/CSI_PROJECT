import Navbar from "../components/layout/Navbar";
import Hero from "../components/landing/Hero";
import ProblemSection from "../components/landing/ProblemSection";
import IntelligenceSection from "../components/landing/IntelligenceSection";

function Landing() {
  return (
    <>
      <Navbar />

      <main>
        <Hero />
        <ProblemSection />
        <IntelligenceSection />

        <section
          id="how-it-works"
          className="section"
        >
          <p className="section-eyebrow">
            HOW IT WORKS
          </p>

          <h2>
            Simulate. Evaluate. Decide.
          </h2>

          <p>
            LiquidityOS combines financial information,
            uncertainty and business constraints to
            continuously evaluate deployment decisions.
          </p>
        </section>

        <section
          id="reoptimization"
          className="section"
        >
          <p className="section-eyebrow">
            ADAPTIVE DECISION MAKING
          </p>

          <h2>
            When reality changes,
            the decision changes.
          </h2>

          <p>
            When an interrupt or financial event occurs,
            LiquidityOS can re-evaluate the situation and
            produce a new recommendation.
          </p>
        </section>
      </main>
    </>
  );
}

export default Landing;