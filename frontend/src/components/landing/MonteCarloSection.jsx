import { motion } from "motion/react";

const paths = [
  "M 0 170 C 80 155, 130 190, 200 145 S 330 115, 400 135 S 520 80, 620 105 S 760 55, 900 75",
  "M 0 170 C 70 135, 140 165, 210 125 S 330 150, 410 100 S 540 125, 620 75 S 780 95, 900 55",
  "M 0 170 C 90 185, 145 130, 220 155 S 350 85, 430 120 S 540 65, 650 95 S 790 45, 900 35",
  "M 0 170 C 80 145, 150 175, 230 135 S 350 130, 430 90 S 560 105, 650 65 S 800 80, 900 45",
  "M 0 170 C 70 160, 140 120, 220 145 S 340 100, 420 140 S 550 85, 650 110 S 790 65, 900 90",
  "M 0 170 C 80 125, 150 150, 220 110 S 350 115, 430 75 S 550 95, 650 50 S 790 70, 900 25",
  "M 0 170 C 90 175, 160 145, 230 160 S 350 120, 430 130 S 560 100, 650 120 S 790 85, 900 70",
  "M 0 170 C 75 145, 150 180, 220 130 S 340 90, 430 110 S 550 70, 650 100 S 780 50, 900 60",
];

function MonteCarloSection() {
  return (
    <section className="section monte-carlo-section">
      <div className="monte-carlo-header">
        <div>
          <p className="section-eyebrow">
            PROBABILISTIC INTELLIGENCE
          </p>

          <h2>
            Don't predict
            <br />
            one future.
          </h2>
        </div>

        <p className="monte-carlo-description">
          Zypher evaluates thousands of possible liquidity
          outcomes to understand the range of future financial
          conditions before making a deployment decision.
        </p>
      </div>

      <motion.div
        className="simulation-card"
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.7 }}
      >
        <div className="simulation-top">
          <div>
            <span className="simulation-label">
              SIMULATED LIQUIDITY OUTCOMES
            </span>

            <h3>Possible future states</h3>
          </div>

          <div className="simulation-status">
            <span className="status-dot" />
            Simulation active
          </div>
        </div>

        <div className="chart-container">
          <div className="chart-y-labels">
            <span>₹30L</span>
            <span>₹20L</span>
            <span>₹10L</span>
            <span>₹0</span>
          </div>

          <svg
            className="simulation-chart"
            viewBox="0 0 900 210"
            preserveAspectRatio="none"
          >
            <line
              x1="0"
              y1="45"
              x2="900"
              y2="45"
              className="chart-grid-line"
            />

            <line
              x1="0"
              y1="95"
              x2="900"
              y2="95"
              className="chart-grid-line"
            />

            <line
              x1="0"
              y1="145"
              x2="900"
              y2="145"
              className="chart-grid-line"
            />

            <line
              x1="0"
              y1="195"
              x2="900"
              y2="195"
              className="chart-grid-line"
            />

            {paths.map((path, index) => (
              <motion.path
                key={index}
                d={path}
                className="simulation-path"
                initial={{
                  pathLength: 0,
                  opacity: 0,
                }}
                whileInView={{
                  pathLength: 1,
                  opacity: 0.32,
                }}
                viewport={{
                  once: true,
                  amount: 0.3,
                }}
                transition={{
                  duration: 1.8,
                  delay: index * 0.12,
                  ease: "easeOut",
                }}
              />
            ))}

            <motion.path
              d="M 0 170 C 90 150, 150 155, 220 135 S 350 105, 430 115 S 550 80, 650 85 S 790 65, 900 55"
              className="simulation-primary-path"
              initial={{
                pathLength: 0,
              }}
              whileInView={{
                pathLength: 1,
              }}
              viewport={{
                once: true,
                amount: 0.3,
              }}
              transition={{
                duration: 2.2,
                delay: 0.7,
                ease: "easeOut",
              }}
            />

            <motion.line
              x1="0"
              y1="125"
              x2="900"
              y2="125"
              className="deployment-line"
              initial={{
                opacity: 0,
              }}
              whileInView={{
                opacity: 1,
              }}
              viewport={{
                once: true,
              }}
              transition={{
                delay: 1.7,
                duration: 0.5,
              }}
            />
          </svg>
        </div>

        <div className="simulation-bottom">
          <div>
            <span>SIMULATIONS</span>
            <strong>10,000+</strong>
          </div>

          <div>
            <span>CONFIDENCE</span>
            <strong>87%</strong>
          </div>

          <div>
            <span>SAFE DEPLOYMENT</span>
            <strong>₹6.4L</strong>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

export default MonteCarloSection;