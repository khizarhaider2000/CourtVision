import { useState, useEffect } from 'react';
import { api } from '../api/client.js';
import {
  ALL_METRICS,
  WINDOWS,
  WINDOW_LABELS,
  NBA_TEAMS,
  COMPARE_METRICS_DEFAULT,
} from '../utils/constants.js';
import { metricLabel, downloadCsv } from '../utils/format.js';
import DataTable from '../components/data/DataTable.jsx';
import ScatterPlot from '../components/data/ScatterPlot.jsx';
import MetricCompare from '../components/data/MetricCompare.jsx';
import Spinner from '../components/ui/Spinner.jsx';
import ErrorMessage from '../components/ui/ErrorMessage.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import styles from './Analytics.module.css';

const CHART_TYPES = [
  { id: 'leaderboard', label: 'Leaderboard' },
  { id: 'scatter', label: 'Scatter' },
  { id: 'compare', label: 'Compare' },
];

const TOP_N_OPTIONS = [5, 10, 15, 20, 30];

export default function Analytics() {
  // Seasons
  const [seasons, setSeasons] = useState([]);
  const [season, setSeason] = useState('');
  const [seasonsLoading, setSeasonsLoading] = useState(true);

  // Shared params
  const [chartType, setChartType] = useState('leaderboard');
  const [timeWindow, setTimeWindow] = useState('SEASON');

  // Leaderboard params
  const [metric, setMetric] = useState('NET_RTG');
  const [topN, setTopN] = useState(10);
  const [order, setOrder] = useState('desc');

  // Scatter params
  const [xMetric, setXMetric] = useState('ORtg');
  const [yMetric, setYMetric] = useState('DRtg');

  // Compare params
  const [selectedTeams, setSelectedTeams] = useState(['BOS', 'LAL']);
  const [compareMetrics, setCompareMetrics] = useState([...COMPARE_METRICS_DEFAULT]);

  // Result state
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.seasons()
      .then((data) => {
        setSeasons(data.seasons);
        setSeason(data.default);
      })
      .catch((err) => setError(err.message))
      .finally(() => setSeasonsLoading(false));
  }, []);

  function handleChartTypeChange(type) {
    setChartType(type);
    setResult(null);
    setError(null);
  }

  function buildParams() {
    const base = {
      season,
      entity: 'team',
      chart_type: chartType,
      window: timeWindow,
    };
    if (chartType === 'leaderboard') {
      return { ...base, metric, top_n: topN, order };
    }
    if (chartType === 'scatter') {
      return { ...base, x_metric: xMetric, y_metric: yMetric };
    }
    // compare
    return {
      ...base,
      teams: selectedTeams,
      compare_metrics: compareMetrics,
    };
  }

  async function runQuery() {
    if (!season) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.query(buildParams());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function toggleTeam(abbr) {
    setSelectedTeams((prev) =>
      prev.includes(abbr) ? prev.filter((t) => t !== abbr) : [...prev, abbr]
    );
  }

  function toggleCompareMetric(m) {
    setCompareMetrics((prev) =>
      prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]
    );
  }

  function renderControls() {
    return (
      <div className={styles.controls}>
        {/* Shared: Season + Window */}
        <div className={styles.controlRow}>
          <div className={styles.controlGroup}>
            <label className={styles.label}>Season</label>
            {seasonsLoading ? (
              <Spinner size="sm" />
            ) : (
              <select
                className={styles.select}
                value={season}
                onChange={(e) => setSeason(e.target.value)}
              >
                {seasons.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className={styles.controlGroup}>
            <label className={styles.label}>Window</label>
            <select
              className={styles.select}
              value={timeWindow}
              onChange={(e) => setTimeWindow(e.target.value)}
            >
              {WINDOWS.map((w) => (
                <option key={w} value={w}>
                  {WINDOW_LABELS[w]}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Leaderboard-specific */}
        {chartType === 'leaderboard' && (
          <div className={styles.controlRow}>
            <div className={styles.controlGroup}>
              <label className={styles.label}>Metric</label>
              <select
                className={styles.select}
                value={metric}
                onChange={(e) => setMetric(e.target.value)}
              >
                {ALL_METRICS.map((m) => (
                  <option key={m} value={m}>
                    {metricLabel(m)}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.controlGroup}>
              <label className={styles.label}>Top N</label>
              <select
                className={styles.select}
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
              >
                {TOP_N_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n} teams
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.controlGroup}>
              <label className={styles.label}>Order</label>
              <select
                className={styles.select}
                value={order}
                onChange={(e) => setOrder(e.target.value)}
              >
                <option value="desc">Best first</option>
                <option value="asc">Worst first</option>
              </select>
            </div>
          </div>
        )}

        {/* Scatter-specific */}
        {chartType === 'scatter' && (
          <div className={styles.controlRow}>
            <div className={styles.controlGroup}>
              <label className={styles.label}>X axis</label>
              <select
                className={styles.select}
                value={xMetric}
                onChange={(e) => setXMetric(e.target.value)}
              >
                {ALL_METRICS.map((m) => (
                  <option key={m} value={m}>
                    {metricLabel(m)}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.controlGroup}>
              <label className={styles.label}>Y axis</label>
              <select
                className={styles.select}
                value={yMetric}
                onChange={(e) => setYMetric(e.target.value)}
              >
                {ALL_METRICS.map((m) => (
                  <option key={m} value={m}>
                    {metricLabel(m)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Compare-specific */}
        {chartType === 'compare' && (
          <div className={styles.compareControls}>
            <div className={styles.compareGroup}>
              <p className={styles.label}>Teams (select 2 or more)</p>
              <div className={styles.teamGrid}>
                {NBA_TEAMS.map((abbr) => (
                  <label key={abbr} className={styles.checkLabel}>
                    <input
                      type="checkbox"
                      checked={selectedTeams.includes(abbr)}
                      onChange={() => toggleTeam(abbr)}
                      className={styles.checkbox}
                    />
                    <span>{abbr}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className={styles.compareGroup}>
              <p className={styles.label}>Metrics</p>
              <div className={styles.metricsCheckGrid}>
                {ALL_METRICS.map((m) => (
                  <label key={m} className={styles.checkLabel}>
                    <input
                      type="checkbox"
                      checked={compareMetrics.includes(m)}
                      onChange={() => toggleCompareMetric(m)}
                      className={styles.checkbox}
                    />
                    <span>{metricLabel(m)}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className={styles.runRow}>
          <button
            className={styles.runBtn}
            onClick={runQuery}
            disabled={
              loading ||
              !season ||
              (chartType === 'compare' && selectedTeams.length < 2) ||
              (chartType === 'compare' && compareMetrics.length === 0)
            }
          >
            {loading ? (
              <>
                <Spinner size="sm" />
                <span>Loading...</span>
              </>
            ) : (
              'Run'
            )}
          </button>
          {chartType === 'compare' && selectedTeams.length < 2 && (
            <span className={styles.validationNote}>Select at least 2 teams</span>
          )}
        </div>
      </div>
    );
  }

  function renderResult() {
    if (!result) return null;
    const { rows, explanation } = result;

    return (
      <div className={styles.resultSection}>
        <div className={styles.resultHeader}>
          <h2 className={styles.resultTitle}>Results</h2>
          {rows && rows.length > 0 && (
            <button
              className={styles.downloadBtn}
              onClick={() =>
                downloadCsv(rows, `courtvision-${chartType}-${season}-${timeWindow}.csv`)
              }
            >
              Download CSV
            </button>
          )}
        </div>

        {explanation && <p className={styles.explanation}>{explanation}</p>}

        {!rows || rows.length === 0 ? (
          <EmptyState title="No data returned" description="Try adjusting your filters." />
        ) : (
          <>
            {chartType === 'scatter' && (
              <ScatterPlot rows={rows} xMetric={xMetric} yMetric={yMetric} />
            )}
            {chartType === 'compare' && (
              <MetricCompare rows={rows} metrics={compareMetrics} />
            )}
            <DataTable rows={rows} showRank={chartType === 'leaderboard'} />
          </>
        )}
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Analytics</h1>
        <p className={styles.subtitle}>
          Build structured queries — no natural language required.
        </p>
      </div>

      {/* Chart type tabs */}
      <div className={styles.tabs} role="tablist">
        {CHART_TYPES.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={chartType === id}
            className={chartType === id ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            onClick={() => handleChartTypeChange(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <ErrorMessage message={error} onDismiss={() => setError(null)} />
      )}

      {renderControls()}
      {renderResult()}
    </div>
  );
}
