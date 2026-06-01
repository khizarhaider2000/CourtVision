import { METRIC_LABELS, ASC_METRICS } from './constants.js';

// Metrics stored as decimals (0.48) that should display as percentages
const DECIMAL_PERCENT_METRICS = new Set([
  'eFG',
  'TS',
  'AST_RATE',
  'TOV_RATE',
  'Opp_TOV%',
  'oreb_pct',
  'dreb_pct',
  'opp_fgpct_rim',
]);

export function formatMetric(metric, value) {
  if (value === null || value === undefined) {
    return metric === 'clutch_net_rating' ? 'N/A' : '—';
  }
  if (typeof value !== 'number') return String(value);
  if (DECIMAL_PERCENT_METRICS.has(metric)) {
    return `${(value * 100).toFixed(1)}%`;
  }
  return value.toFixed(1);
}

export function metricLabel(metric) {
  return METRIC_LABELS[metric] ?? metric;
}

export function windowLabel(window) {
  const map = {
    SEASON: 'Full Season',
    LAST_5: 'Last 5',
    LAST_10: 'Last 10',
    LAST_20: 'Last 20',
  };
  return map[window] ?? window;
}

// Returns 'positive' | 'negative' | '' for CSS class coloring
export function ratingColorClass(metric, value) {
  if (value === null || value === undefined || typeof value !== 'number') return '';
  if (metric === 'NET_RTG') return value > 0 ? 'positive' : value < 0 ? 'negative' : '';
  return '';
}

export function isBetterHigher(metric) {
  return !ASC_METRICS.has(metric);
}

// Generate a CSV string from an array of row objects
export function rowsToCsv(rows) {
  if (!rows || rows.length === 0) return '';
  const cols = Object.keys(rows[0]);
  const header = cols.join(',');
  const body = rows
    .map((r) => cols.map((c) => (r[c] ?? '')).join(','))
    .join('\n');
  return `${header}\n${body}`;
}

export function downloadCsv(rows, filename = 'courtvision-export.csv') {
  const csv = rowsToCsv(rows);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
