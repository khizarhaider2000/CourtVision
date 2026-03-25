import { useNavigate, Link } from 'react-router-dom';
import { EXAMPLE_QUERIES } from '../utils/constants.js';
import styles from './Home.module.css';

export default function Home() {
  const navigate = useNavigate();

  function goToQuery(q) {
    navigate(`/query?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className={styles.page}>
      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.heroText}>
          <h1 className={styles.headline}>
            NBA team analytics,<br />
            built for real questions.
          </h1>
          <p className={styles.subhead}>
            CourtVision turns natural language into structured NBA team performance
            analysis. Query in plain English, explore ratings, compare franchises,
            and understand how stats are built.
          </p>
          <div className={styles.heroCtas}>
            <Link to="/query" className={styles.ctaPrimary}>
              Query with AI
            </Link>
            <Link to="/analytics" className={styles.ctaSecondary}>
              Build analytics
            </Link>
          </div>
        </div>
        <div className={styles.heroMeta}>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Seasons</span>
            <span className={styles.metaValue}>2016&ndash;2026</span>
          </div>
          <div className={styles.metaDivider} />
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Coverage</span>
            <span className={styles.metaValue}>All 30 teams</span>
          </div>
          <div className={styles.metaDivider} />
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Source</span>
            <span className={styles.metaValue}>NBA official stats</span>
          </div>
        </div>
      </section>

      {/* Example prompts */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What you can ask</h2>
        <p className={styles.sectionDesc}>
          Type any of these into the query interface, or write your own.
        </p>
        <div className={styles.exampleGrid}>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              className={styles.exampleCard}
              onClick={() => goToQuery(q)}
            >
              <span className={styles.exampleArrow}>→</span>
              <span>{q}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What CourtVision covers</h2>
        <div className={styles.capabilityGrid}>
          <div className={styles.capability}>
            <h3 className={styles.capTitle}>Leaderboards</h3>
            <p className={styles.capDesc}>
              Rank all 30 teams by any metric — net rating, pace, offensive
              efficiency — over any time window.
            </p>
          </div>
          <div className={styles.capability}>
            <h3 className={styles.capTitle}>Scatter Analysis</h3>
            <p className={styles.capDesc}>
              Plot two metrics against each other to identify efficiency
              landscapes, outliers, and stylistic clusters.
            </p>
          </div>
          <div className={styles.capability}>
            <h3 className={styles.capTitle}>Team Comparisons</h3>
            <p className={styles.capDesc}>
              Compare any two or more franchises head-to-head across the full
              metric set, filtered by time window.
            </p>
          </div>
          <div className={styles.capability}>
            <h3 className={styles.capTitle}>Time Windows</h3>
            <p className={styles.capDesc}>
              Analyze full-season trends or zoom into the last 5, 10, or 20
              games to capture current form.
            </p>
          </div>
        </div>
      </section>

      {/* Secondary nav */}
      <section className={styles.navRow}>
        <Link to="/teams" className={styles.navCard}>
          <span className={styles.navCardTitle}>All Teams</span>
          <span className={styles.navCardDesc}>
            Full metrics table for every team, sortable by any stat
          </span>
        </Link>
        <Link to="/methodology" className={styles.navCard}>
          <span className={styles.navCardTitle}>Methodology</span>
          <span className={styles.navCardDesc}>
            How ratings, pace, and efficiency metrics are calculated
          </span>
        </Link>
      </section>
    </div>
  );
}
