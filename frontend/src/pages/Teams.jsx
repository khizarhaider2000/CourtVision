import { useState, useEffect } from 'react';
import { api } from '../api/client.js';
import { WINDOWS, WINDOW_LABELS } from '../utils/constants.js';
import { downloadCsv } from '../utils/format.js';
import DataTable from '../components/data/DataTable.jsx';
import Spinner from '../components/ui/Spinner.jsx';
import ErrorMessage from '../components/ui/ErrorMessage.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import styles from './Teams.module.css';

export default function Teams() {
  const [seasons, setSeasons] = useState([]);
  const [season, setSeason] = useState('');
  const [timeWindow, setTimeWindow] = useState('SEASON');
  const [seasonsLoading, setSeasonsLoading] = useState(true);

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasFetched, setHasFetched] = useState(false);

  useEffect(() => {
    api.seasons()
      .then((data) => {
        setSeasons(data.seasons);
        setSeason(data.default);
      })
      .catch((err) => setError(err.message))
      .finally(() => setSeasonsLoading(false));
  }, []);

  // Auto-load on first season set
  useEffect(() => {
    if (season && !hasFetched) {
      fetchMetrics(season, timeWindow);
    }
  }, [season]);

  async function fetchMetrics(s, w) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.metrics({ season: s, window: w });
      setResult(data);
      setHasFetched(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleRefresh() {
    fetchMetrics(season, timeWindow);
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Teams</h1>
        <p className={styles.subtitle}>
          Full metrics table for all 30 teams. Click any column header to sort.
        </p>
      </div>

      {/* Controls */}
      <div className={styles.controls}>
        <div className={styles.controlGroup}>
          <label className={styles.label} htmlFor="teams-season">Season</label>
          {seasonsLoading ? (
            <Spinner size="sm" />
          ) : (
            <select
              id="teams-season"
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
          <label className={styles.label} htmlFor="teams-window">Window</label>
          <select
            id="teams-window"
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
        <button
          className={styles.loadBtn}
          onClick={handleRefresh}
          disabled={loading || !season}
        >
          {loading ? <Spinner size="sm" /> : 'Load'}
        </button>
        {result && result.rows && result.rows.length > 0 && (
          <button
            className={styles.downloadBtn}
            onClick={() =>
              downloadCsv(result.rows, `courtvision-teams-${season}-${timeWindow}.csv`)
            }
          >
            Download CSV
          </button>
        )}
      </div>

      {error && (
        <ErrorMessage message={error} onDismiss={() => setError(null)} />
      )}

      {/* Result context */}
      {result && !loading && (
        <div className={styles.resultMeta}>
          <span className={styles.resultMetaText}>
            {result.season} &mdash; {WINDOW_LABELS[result.window] ?? result.window} &mdash;{' '}
            {result.rows.length} teams
          </span>
        </div>
      )}

      {/* Table */}
      {loading && (
        <div className={styles.loadingState}>
          <Spinner size="lg" />
          <span className={styles.loadingLabel}>Loading team data...</span>
        </div>
      )}

      {!loading && result && result.rows && result.rows.length > 0 && (
        <DataTable rows={result.rows} />
      )}

      {!loading && result && result.rows && result.rows.length === 0 && (
        <EmptyState
          title="No data for this period"
          description="The selected season or window may not have data yet. Try a different combination."
        />
      )}

      {!loading && !result && !error && (
        <EmptyState
          title="Select a season and window"
          description="Use the controls above to load team stats."
        />
      )}
    </div>
  );
}
