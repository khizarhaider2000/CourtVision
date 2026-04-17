import { metricLabel, formatMetric } from '../../utils/format.js';
import { COMPARE_METRICS_DEFAULT } from '../../utils/constants.js';
import styles from './MetricCompare.module.css';

// Up to 5 distinct team colors (non-purple palette)
const TEAM_COLORS = ['#D4290D', '#1A5FA8', '#186234', '#8A5C00', '#5A3A7A'];

export default function MetricCompare({ rows, metrics }) {
  if (!rows || rows.length === 0) return null;

  const displayMetrics = metrics && metrics.length > 0 ? metrics : COMPARE_METRICS_DEFAULT;
  const teams = rows.map((r) => r.TEAM_ABBREVIATION);

  // For each metric, compute min/max across teams for bar scaling
  function getRange(metric) {
    const vals = rows.map((r) => r[metric]).filter((v) => v !== null && v !== undefined);
    if (vals.length === 0) return { min: 0, max: 1 };
    return { min: Math.min(...vals), max: Math.max(...vals) };
  }

  function barPct(metric, value) {
    if (value === null || value === undefined) return 0;
    const { min, max } = getRange(metric);
    if (max === min) return 50;
    return ((value - min) / (max - min)) * 100;
  }

  return (
    <div className={styles.root}>
      {/* Header row: blank metric col + team columns */}
      <div
        className={styles.headerRow}
        style={{ gridTemplateColumns: `180px repeat(${teams.length}, 1fr)` }}
      >
        <div className={styles.headerMetric}>Metric</div>
        {teams.map((team, i) => (
          <div
            key={team}
            className={styles.headerTeam}
            style={{ color: TEAM_COLORS[i % TEAM_COLORS.length] }}
          >
            {team}
          </div>
        ))}
      </div>

      {/* Metric rows */}
      {displayMetrics.map((metric) => (
        <div
          key={metric}
          className={styles.metricRow}
          style={{ gridTemplateColumns: `180px repeat(${teams.length}, 1fr)` }}
        >
          <div className={styles.metricLabel}>{metricLabel(metric)}</div>
          {rows.map((row, i) => {
            const val = row[metric];
            const pct = barPct(metric, val);
            return (
              <div key={row.TEAM_ABBREVIATION} className={styles.valueCell}>
                <div className={styles.barTrack}>
                  <div
                    className={styles.bar}
                    style={{
                      width: `${pct}%`,
                      background: TEAM_COLORS[i % TEAM_COLORS.length],
                    }}
                  />
                </div>
                <span className={styles.value}>{formatMetric(metric, val)}</span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
