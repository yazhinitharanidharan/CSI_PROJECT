import { motion } from "motion/react";
import { Link } from "react-router-dom";

function Hero() {
  return (
    <section className="hero">
      {/* LEFT SIDE */}
      <motion.div
        className="hero-content"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: {
            transition: {
              staggerChildren: 0.12,
              delayChildren: 0.1,
            },
          },
        }}
      >
        <motion.p
          className="hero-eyebrow"
          variants={{
            hidden: {
              opacity: 0,
              y: 15,
            },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                duration: 0.5,
                ease: "easeOut",
              },
            },
          }}
        >
          AUTONOMOUS WORKING CAPITAL INTELLIGENCE
        </motion.p>

        <motion.h1
          variants={{
            hidden: {
              opacity: 0,
              y: 25,
            },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                duration: 0.7,
                ease: "easeOut",
              },
            },
          }}
        >
          Know what cash
          <br />
          you can safely deploy.
        </motion.h1>

        <motion.p
          className="hero-description"
          variants={{
            hidden: {
              opacity: 0,
              y: 20,
            },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                duration: 0.6,
                ease: "easeOut",
              },
            },
          }}
        >
          Zypher Capital evaluates cash, receivables, obligations,
          uncertainty and constraints to continuously determine
          your safest deployment decision.
        </motion.p>

        <motion.div
          className="hero-actions"
          variants={{
            hidden: {
              opacity: 0,
              y: 15,
            },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                duration: 0.5,
                ease: "easeOut",
              },
            },
          }}
        >
          <Link to="/signup" className="primary-button">
            Explore Zypher
          </Link>

          <a href="#how-it-works" className="secondary-button">
            See how it works
          </a>
        </motion.div>
      </motion.div>

      {/* RIGHT SIDE */}
      <motion.div
        className="hero-visual"
        initial={{
          opacity: 0,
          x: 30,
        }}
        animate={{
          opacity: 1,
          x: 0,
        }}
        transition={{
          duration: 0.8,
          delay: 0.35,
          ease: "easeOut",
        }}
      >
        <motion.div
          className="hero-dashboard-card"
          whileHover={{
            y: -6,
            transition: {
              duration: 0.25,
            },
          }}
        >
          <span>SAFE TO DEPLOY</span>

          <strong>₹6.4L</strong>

          <small>
            Based on current liquidity conditions
          </small>
        </motion.div>
      </motion.div>
    </section>
  );
}

export default Hero;