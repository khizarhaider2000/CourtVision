import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { COMPARE_METRICS_DEFAULT, WINDOW_LABELS } from '../utils/constants.js';
import { metricLabel, windowLabel, downloadCsv } from '../utils/format.js';
import DataTable from '../components/data/DataTable.jsx';
import ScatterPlot from '../components/data/ScatterPlot.jsx';
import MetricCompare from '../components/data/MetricCompare.jsx';
import Spinner from '../components/ui/Spinner.jsx';
import ErrorMessage from '../components/ui/ErrorMessage.jsx';
import styles from './Query.module.css';

function ParsedQueryCard({ result, effectiveSeason }) {
  const { chart_type, metric, x_metric, y_metric, window, top_n, order, teams, compare_metrics, season } = result;

  const rows = [];

  if (chart_type) rows.push({ label: 'Chart type', value: chart_type.charAt(0).toUpperCase() + chart_type.slice(1) });
  // Always show the season that will actually be used — parsed season takes priority, fallback to default
  rows.push({ label: 'Season', value: season ?? effectiveSeason ?? '—' });
  if (window) rows.push({ label: 'Window', value: windowLabel(window) });
  if (metric) rows.push({ label: 'Metric', value: metricLabel(metric) });
  if (x_metric) rows.push({ label: 'X axis', value: metricLabel(x_metric) });
  if (y_metric) rows.push({ label: 'Y axis', value: metricLabel(y_metric) });
  if (top_n) rows.push({ label: 'Top', value: `${top_n} teams` });
  if (order) rows.push({ label: 'Order', value: order === 'desc' ? 'Best first' : 'Worst first' });
  if (teams && teams.length > 0) rows.push({ label: 'Teams', value: teams.join(', ') });
  if (compare_metrics && compare_metrics.length > 0)
    rows.push({ label: 'Metrics', value: compare_metrics.map(metricLabel).join(', ') });

  return (
    <div className={styles.parsedCard}>
      <div className={styles.parsedHeader}>
        <span className={styles.parsedBadge}>Query parsed</span>
      </div>
      <dl className={styles.parsedList}>
        {rows.map(({ label, value }) => (
          <div key={label} className={styles.parsedRow}>
            <dt className={styles.parsedDt}>{label}</dt>
            <dd className={styles.parsedDd}>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function ClarifyCard({ message }) {
  return (
    <div className={styles.clarifyCard}>
      <span className={styles.clarifyBadge}>Needs clarification</span>
      <p className={styles.clarifyMessage}>{message}</p>
    </div>
  );
}

function OutOfScopeCard({ message }) {
  return (
    <div className={styles.outOfScopeCard}>
      <span className={styles.outOfScopeBadge}>Out of scope</span>
      <p className={styles.outOfScopeMessage}>
        {message ||
          'CourtVision covers team-level statistics only. Player stats, game-level scores, schedules, and predictions are not supported.'}
      </p>
    </div>
  );
}

function buildQueryParams(parsed, defaultSeason) {
  const base = {
    season: parsed.season ?? defaultSeason,
    chart_type: parsed.chart_type,
    entity: 'team',
    window: parsed.window ?? 'SEASON',
  };

  if (parsed.chart_type === 'leaderboard') {
    return {
      ...base,
      metric: parsed.metric,
      top_n: parsed.top_n ?? 10,
      order: parsed.order ?? 'desc',
    };
  }

  if (parsed.chart_type === 'scatter') {
    return {
      ...base,
      x_metric: parsed.x_metric,
      y_metric: parsed.y_metric,
    };
  }

  // compare
  return {
    ...base,
    teams: parsed.teams,
    compare_metrics: parsed.compare_metrics ?? COMPARE_METRICS_DEFAULT,
  };
}

export default function Query() {
  const [searchParams] = useSearchParams();

  const [query, setQuery] = useState(searchParams.get('q') ?? '');
  const [defaultSeason, setDefaultSeason] = useState('');

  const [parsing, setParsing] = useState(false);
  const [running, setRunning] = useState(false);
  const [parseResult, setParseResult] = useState(null);
  const [queryResult, setQueryResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.seasons()
      .then((data) => setDefaultSeason(data.default))
      .catch(() => {});
  }, []);

  function resetResults() {
    setParseResult(null);
    setQueryResult(null);
    setError(null);
  }

  async function handleParse(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setParsing(true);
    setError(null);
    setParseResult(null);
    setQueryResult(null);
    try {
      const result = await api.aiParse(q);
      setParseResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setParsing(false);
    }
  }

  const handleRunQuery = useCallback(async () => {
    if (!parseResult || parseResult.result_type !== 'QUERY') return;
    setRunning(true);
    setError(null);
    setQueryResult(null);
    try {
      const params = buildQueryParams(parseResult, defaultSeason);
      const result = await api.query(params);
      setQueryResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }, [parseResult, defaultSeason]);

  function renderResults() {
    if (!queryResult) return null;
    const { rows, explanation } = queryResult;
    const ct = parseResult?.chart_type;

    return (
      <div className={styles.results}>
        <div className={styles.resultsHeader}>
          <h2 className={styles.resultsTitle}>Results</h2>
          {rows && rows.length > 0 && (
            <button
              className={styles.downloadBtn}
              onClick={() => downloadCsv(rows, `courtvision-${ct}-${Date.now()}.csv`)}
            >
              Download CSV
            </button>
          )}
        </div>

        {explanation && <p className={styles.explanation}>{explanation}</p>}

        {ct === 'scatter' && rows && rows.length > 0 && (
          <div className={styles.chartBlock}>
            <ScatterPlot
              rows={rows}
              xMetric={parseResult.x_metric}
              yMetric={parseResult.y_metric}
            />
          </div>
        )}

        {ct === 'compare' && rows && rows.length > 0 && (
          
          <div className={styles.chartBlock}>
            <MetricCompare
              rows={rows}
              metrics={parseResult.compare_metrics ?? COMPARE_METRICS_DEFAULT}
            />
          </div>
        )}

        {rows && rows.length > 0 ? (
          <DataTable rows={rows} showRank={ct === 'leaderboard'} />
        ) : (
          <p className={styles.noData}>No data returned for this query.</p>
        )}
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>AI Query</h1>
        <p className={styles.subtitle}>
          Ask a question about NBA team performance in plain English.
        </p>
      </div>

      <form onSubmit={handleParse} className={styles.queryForm}>
        <textarea
          className={styles.queryInput}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (parseResult || queryResult) resetResults();
          }}
          placeholder="e.g. Show the top 10 teams by net rating in the last 10 games"
          rows={3}
          maxLength={500}
          aria-label="NBA analytics query"
        />
        <div className={styles.queryFooter}>
          <span className={styles.charCount}>{query.length}/500</span>
          <button
            type="submit"
            className={styles.parseBtn}
            disabled={parsing || !query.trim()}
          >
            {parsing ? (
              <>
                <Spinner size="sm" />
                <span>Parsing...</span>
              </>
            ) : (
              'Parse Query'
            )}
          </button>
        </div>
      </form>

      {error && (
        <ErrorMessage message={error} onDismiss={() => setError(null)} />
      )}

      {/* Parse result display */}
      {parseResult && (
        <div className={styles.parseOutput}>
          {parseResult.result_type === 'QUERY' && (
            <>
              <ParsedQueryCard result={parseResult} effectiveSeason={defaultSeason} />
              <div className={styles.runRow}>
                <button
                  className={styles.runBtn}
                  onClick={handleRunQuery}
                  disabled={running}
                >
                  {running ? (
                    <>
                      <Spinner size="sm" />
                      <span>Running...</span>
                    </>
                  ) : (
                    'Run This Query'
                  )}
                </button>
                {parseResult._debug?.fallback_used && (
                  <span className={styles.fallbackNote}>
                    Parsed without AI (rule-based fallback)
                  </span>
                )}
              </div>
            </>
          )}

          {parseResult.result_type === 'CLARIFY' && (
            <ClarifyCard message={parseResult.message} />
          )}

          {parseResult.result_type === 'OUT_OF_SCOPE' && (
            <OutOfScopeCard message={parseResult.message} />
          )}
        </div>
      )}

      {renderResults()}
    </div>
  );
}
