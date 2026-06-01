import { metricLabel, formatMetric } from '../../utils/format.js';
import { COMPARE_METRICS_DEFAULT } from '../../utils/constants.js';
import { isBetterHigher } from '../../utils/format.js';
import styles from './MetricCompare.module.css';

const DEFAULT_TEAM_COLOR = '#111111';
const TEAM_COLORS = {
  NYK: '#F58426',
  SAS: '#111111',
};

function teamColor(team) {
  return TEAM_COLORS[team] ?? DEFAULT_TEAM_COLOR;
}

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
    const pct = ((value - min) / (max - min)) * 100;
    return isBetterHigher(metric) ? pct : 100 - pct;
  }

  function isBestValue(metric, value) {
    if (value === null || value === undefined) return false;
    const vals = rows.map((r) => r[metric]).filter((v) => v !== null && v !== undefined);
    if (vals.length === 0) return false;
    const best = isBetterHigher(metric) ? Math.max(...vals) : Math.min(...vals);
    return value === best;
  }

  return (
    <div className={styles.root}>
      {/* Header row: blank metric col + team columns */}
      <div
        className={styles.headerRow}
        style={{ gridTemplateColumns: `180px repeat(${teams.length}, 1fr)` }}
      >
        <div className={styles.headerMetric}>Metric</div>
        {teams.map((team) => (
          <div
            key={team}
            className={styles.headerTeam}
            style={{ color: teamColor(team) }}
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
          {rows.map((row) => {
            const val = row[metric];
            const pct = barPct(metric, val);
            const isBest = isBestValue(metric, val);
            const color = isBest ? teamColor(row.TEAM_ABBREVIATION) : 'var(--border)';
            return (
              <div key={row.TEAM_ABBREVIATION} className={styles.valueCell}>
                <div className={styles.barTrack}>
                  <div
                    className={styles.bar}
                    style={{
                      width: `${pct}%`,
                      background: color,
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
