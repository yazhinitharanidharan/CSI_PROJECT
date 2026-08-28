import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";

function ReoptimizationSection() {
  const [triggered, setTriggered] = useState(false);

  return (
    <section id="reoptimization" className="reoptimization-section">
      <div className="reoptimization-inner">

        <div className="reoptimization-heading">
          <p className="section-eyebrow">
            ADAPTIVE INTELLIGENCE
          </p>

          <h2>
            When reality changes,
            <br />
            the decision changes.
          </h2>

          <p>
            Financial decisions shouldn't be static. When a delayed
            receivable, unexpected obligation or other interrupt
            changes the liquidity picture, Zypher re-evaluates the
            situation and produces a new recommendation.
          </p>
        </div>

        <div className="reoptimization-demo">

          <div className="demo-header">
            <div>
              <span>LIVE DECISION ENGINE</span>
              <strong>
                {triggered ? "Re-optimization required" : "Decision stable"}
              </strong>
            </div>

            <div className="demo-status">
              <span className={triggered ? "status-dot active" : "status-dot"} />
              {triggered ? "Interrupt detected" : "Monitoring"}
            </div>
          </div>

          <div className="decision-flow">

            <motion.div
              className="decision-card"
              animate={{
                scale: triggered ? 0.96 : 1,
                opacity: triggered ? 0.65 : 1,
              }}
              transition={{ duration: 0.4 }}
            >
              <span>CURRENT DECISION</span>

              <strong>₹6.4L</strong>

              <small>
                Safe to deploy
              </small>
            </motion.div>

            <motion.div
              className="flow-arrow"
              animate={{
                x: triggered ? 8 : 0,
                opacity: triggered ? 1 : 0.4,
              }}
            >
              →
            </motion.div>

            <AnimatePresence mode="wait">
              {!triggered ? (
                <motion.div
                  key="stable"
                  className="interrupt-card"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                >
                  <span>FINANCIAL INTERRUPT</span>

                  <strong>
                    Delayed receivable
                  </strong>

                  <small>
                    Expected payment moved by 14 days
                  </small>
                </motion.div>
              ) : (
                <motion.div
                  key="triggered"
                  className="interrupt-card interrupt-active"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                >
                  <span>RE-OPTIMIZING</span>

                  <strong>
                    Evaluating new conditions...
                  </strong>

                  <small>
                    Liquidity model updating
                  </small>
                </motion.div>
              )}
            </AnimatePresence>

            <motion.div
              className="flow-arrow"
              animate={{
                x: triggered ? 8 : 0,
                opacity: triggered ? 1 : 0.4,
              }}
            >
              →
            </motion.div>

            <motion.div
              className="decision-card new-decision"
              animate={{
                opacity: triggered ? 1 : 0.45,
                scale: triggered ? 1 : 0.96,
              }}
              transition={{ duration: 0.5 }}
            >
              <span>NEW DECISION</span>

              <strong>
                {triggered ? "₹4.1L" : "—"}
              </strong>

              <small>
                {triggered
                  ? "Revised safe deployment"
                  : "Awaiting interrupt"}
              </small>
            </motion.div>

          </div>

          <button
            className="trigger-button"
            onClick={() => setTriggered((value) => !value)}
          >
            {triggered
              ? "Reset simulation"
              : "Trigger financial interrupt"}
          </button>

        </div>

      </div>
    </section>
  );
}

export default ReoptimizationSection;