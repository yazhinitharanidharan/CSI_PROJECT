import { motion } from "motion/react";

function IntelligenceSection() {
  const steps = [
    {
      number: "01",
      title: "Understand",
      text: "Aggregate cash, receivables, obligations and financial conditions.",
    },
    {
      number: "02",
      title: "Simulate",
      text: "Evaluate possible future liquidity outcomes under uncertainty.",
    },
    {
      number: "03",
      title: "Constrain",
      text: "Apply hard and soft business constraints to possible decisions.",
    },
    {
      number: "04",
      title: "Decide",
      text: "Recommend the amount of cash that can be safely deployed.",
    },
  ];

  return (
    <section
      id="intelligence"
      className="section intelligence-section"
    >
      <div className="section-heading">
        <p className="section-eyebrow">
          LIQUIDITY INTELLIGENCE
        </p>

        <h2>
          From financial data
          <br />
          to an informed decision.
        </h2>
      </div>

      <div className="intelligence-grid">
        {steps.map((step, index) => (
          <motion.article
            key={step.number}
            initial={{ opacity: 0, y: 25 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{
              duration: 0.5,
              delay: index * 0.1,
            }}
            className="intelligence-card"
          >
            <span>{step.number}</span>

            <h3>{step.title}</h3>

            <p>{step.text}</p>
          </motion.article>
        ))}
      </div>
    </section>
  );
}

export default IntelligenceSection;