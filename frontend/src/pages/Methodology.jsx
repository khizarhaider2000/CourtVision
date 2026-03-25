import styles from './Methodology.module.css';

const METRICS = [
  {
    name: 'Offensive Rating (ORtg)',
    abbr: 'ORtg',
    def: 'Points scored per 100 team possessions.',
    formula: 'ORtg = (PTS / Possessions) × 100',
    notes:
      'A higher ORtg means a more efficient offense. League average is typically 112–116.',
  },
  {
    name: 'Defensive Rating (DRtg)',
    abbr: 'DRtg',
    def: 'Points allowed per 100 opponent possessions.',
    formula: 'DRtg = (Opp PTS / Opp Possessions) × 100',
    notes:
      'Lower is better. Elite defenses post DRtg values around 108–112.',
  },
  {
    name: 'Net Rating (NET_RTG)',
    abbr: 'NET_RTG',
    def: 'Point differential per 100 possessions (ORtg minus DRtg).',
    formula: 'NET_RTG = ORtg − DRtg',
    notes:
      'The single best predictor of team quality. Positive values indicate the team scores more than it allows per possession.',
  },
  {
    name: 'Pace',
    abbr: 'PACE',
    def: 'Estimated number of possessions per 48 minutes.',
    formula: 'Pace = 48 × (Possessions / Minutes)',
    notes:
      'Higher pace teams play faster, generating more possessions per game. Possessions are estimated as FGA + 0.44 × FTA − OREB + TOV.',
  },
  {
    name: 'Points Per Game (PPG)',
    abbr: 'PPG',
    def: 'Average points scored per game over the selected window.',
    notes: 'Straightforward scoring volume — does not adjust for pace.',
  },
  {
    name: 'Effective Field Goal % (eFG%)',
    abbr: 'eFG',
    def: 'Field goal percentage adjusted for the extra value of three-pointers.',
    formula: 'eFG% = (FGM + 0.5 × FG3M) / FGA',
    notes:
      'A three-pointer is worth 50% more than a two-pointer, so eFG% accounts for shot quality and selection.',
  },
  {
    name: 'True Shooting % (TS%)',
    abbr: 'TS',
    def: 'Shooting efficiency accounting for twos, threes, and free throws.',
    formula: 'TS% = PTS / (2 × (FGA + 0.44 × FTA))',
    notes:
      'The most comprehensive single-number measure of offensive scoring efficiency.',
  },
  {
    name: 'Assist Rate (Ast%)',
    abbr: 'AST_RATE',
    def: 'Fraction of made field goals that were assisted.',
    formula: 'Ast% = AST / FGM',
    notes:
      'Displayed as a percentage. Higher values indicate a more ball-movement-oriented offense.',
  },
  {
    name: 'Turnover Rate (TOV%)',
    abbr: 'TOV_RATE',
    def: 'Turnovers as a fraction of total possessions.',
    formula: 'TOV% = TOV / (FGA + 0.44 × FTA + TOV)',
    notes:
      'Lower is better. Teams with TOV% above 16% are giving up significant offensive possessions.',
  },
  {
    name: "Opponent Turnover % (Opp TOV%)",
    abbr: 'Opp_TOV%',
    def: "Turnovers forced as a fraction of opponent possessions.",
    formula: "Opp TOV% = Opp TOV / (Opp FGA + 0.44 × Opp FTA + Opp TOV)",
    notes:
      'A measure of defensive pressure. Higher means the defense forces more turnovers.',
  },
];

const WINDOWS = [
  { key: 'SEASON', label: 'Full Season', desc: 'All games played in the season to date.' },
  { key: 'LAST_5', label: 'Last 5 Games', desc: 'The 5 most recent games for each team. Good for recent form.' },
  { key: 'LAST_10', label: 'Last 10 Games', desc: 'The 10 most recent games. A common "current form" benchmark.' },
  { key: 'LAST_20', label: 'Last 20 Games', desc: 'Roughly the last quarter of a season.' },
];

export default function Methodology() {
  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Methodology</h1>
        <p className={styles.subtitle}>
          How CourtVision computes team metrics and what each number means.
        </p>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Data source</h2>
        <p className={styles.body}>
          All data is fetched from the NBA official stats API via the open-source{' '}
          <code className={styles.code}>nba_api</code> Python library.
          Game logs are pulled at the team level and aggregated server-side.
          The backend caches results for one hour to avoid rate limiting.
        </p>
        <p className={styles.body}>
          Possession counts are estimated using the standard approximation formula —
          accurate to within 1% of play-by-play counts for most teams.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Metrics</h2>
        <div className={styles.metricList}>
          {METRICS.map((m) => (
            <div key={m.abbr} className={styles.metricCard}>
              <div className={styles.metricHeader}>
                <h3 className={styles.metricName}>{m.name}</h3>
                <span className={styles.metricAbbr}>{m.abbr}</span>
              </div>
              <p className={styles.metricDef}>{m.def}</p>
              {m.formula && (
                <pre className={styles.formula}>{m.formula}</pre>
              )}
              <p className={styles.metricNote}>{m.notes}</p>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Time windows</h2>
        <div className={styles.windowList}>
          {WINDOWS.map((w) => (
            <div key={w.key} className={styles.windowRow}>
              <span className={styles.windowLabel}>{w.label}</span>
              <span className={styles.windowDesc}>{w.desc}</span>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Scope and limitations</h2>
        <ul className={styles.limitList}>
          <li>Coverage is team-level only — no player-level statistics.</li>
          <li>Regular season games only — playoffs are not included.</li>
          <li>Possessions are estimated, not from play-by-play data.</li>
          <li>
            Lineup data uses the <code className={styles.code}>LeagueDashLineups</code> endpoint
            with a minimum minutes threshold.
          </li>
          <li>
            Data freshness depends on the nba_api cache (1-hour TTL). Scores from games played
            within the last hour may not appear immediately.
          </li>
        </ul>
      </section>
    </div>
  );
}
