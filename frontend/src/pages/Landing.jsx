import Navbar from "../components/layout/Navbar";
import Hero from "../components/landing/Hero";
import ProblemSection from "../components/landing/ProblemSection";
import IntelligenceSection from "../components/landing/IntelligenceSection";
import MonteCarloSection from "../components/landing/MonteCarloSection";
import ReoptimizationSection from "../components/landing/ReoptimizationSection";
import FinalCTA from "../components/landing/FinalCTA";

function Landing() {
  return (
    <>
      <Navbar />

      <main>
        <Hero />

        <ProblemSection />

        <IntelligenceSection />

        <MonteCarloSection />

        <ReoptimizationSection />

        <FinalCTA />

        <section id="how-it-works" className="section">
          <p className="section-eyebrow">
            HOW ZYPHER THINKS
          </p>

          <h2>
            From financial data
            <br />
            to an informed decision.
          </h2>

          <p>
            Zypher Capital evaluates your current liquidity,
            future obligations, receivables and uncertainty
            before determining what capital can safely be deployed.
          </p>
        </section>
      </main>
    </>
  );
}

export default Landing;