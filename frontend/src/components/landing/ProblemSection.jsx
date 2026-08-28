import { motion } from "motion/react";

function ProblemSection() {
  return (
    <section className="section problem-section">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.6 }}
      >
        <p className="section-eyebrow">THE PROBLEM</p>

        <h2>
          Cash isn't just a number.
        </h2>

        <p>
          A healthy bank balance does not necessarily mean
          healthy deployable cash. Timing, receivables,
          obligations, risk and business constraints all
          influence what can safely be deployed.
        </p>
      </motion.div>
    </section>
  );
}

export default ProblemSection;