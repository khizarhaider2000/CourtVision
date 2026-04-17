import { useMemo } from 'react';
import { metricLabel, formatMetric } from '../../utils/format.js';
import styles from './ScatterPlot.module.css';

const W = 700;
const H = 460;
const PAD = { top: 28, right: 36, bottom: 56, left: 68 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;
const TICK_COUNT = 6;

function buildScale(values, size) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = range * 0.1;
  const lo = min - pad;
  const hi = max + pad;
  return {
    map: (v) => ((v - lo) / (hi - lo)) * size,
    lo,
    hi,
  };
}

function linSpace(lo, hi, n) {
  return Array.from({ length: n }, (_, i) => lo + (i / (n - 1)) * (hi - lo));
}

export default function ScatterPlot({ rows, xMetric, yMetric }) {
  const { xScale, yScale, xTicks, yTicks } = useMemo(() => {
    const xs = rows.map((r) => r[xMetric] ?? 0);
    const ys = rows.map((r) => r[yMetric] ?? 0);
    const xScale = buildScale(xs, PLOT_W);
    const yScale = buildScale(ys, PLOT_H);
    const xTicks = linSpace(xScale.lo, xScale.hi, TICK_COUNT);
    const yTicks = linSpace(yScale.lo, yScale.hi, TICK_COUNT);
    return { xScale, yScale, xTicks, yTicks };
  }, [rows, xMetric, yMetric]);

  return (
    <div className={styles.wrapper}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className={styles.svg}
        aria-label={`Scatter plot: ${metricLabel(xMetric)} vs ${metricLabel(yMetric)}`}
      >
        {/* Horizontal grid lines */}
        {yTicks.map((t, i) => {
          const y = PAD.top + PLOT_H - yScale.map(t);
          return (
            <line
              key={i}
              x1={PAD.left}
              x2={PAD.left + PLOT_W}
              y1={y}
              y2={y}
              stroke="var(--border)"
              strokeWidth={1}
            />
          );
        })}

        {/* Vertical grid lines */}
        {xTicks.map((t, i) => {
          const x = PAD.left + xScale.map(t);
          return (
            <line
              key={i}
              x1={x}
              x2={x}
              y1={PAD.top}
              y2={PAD.top + PLOT_H}
              stroke="var(--border)"
              strokeWidth={1}
            />
          );
        })}

        {/* Y axis tick labels */}
        {yTicks.map((t, i) => {
          const y = PAD.top + PLOT_H - yScale.map(t);
          return (
            <text
              key={i}
              x={PAD.left - 10}
              y={y}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={10}
              fill="#9C9894"
              fontVariantNumeric="tabular-nums"
            >
              {t.toFixed(1)}
            </text>
          );
        })}

        {/* X axis tick labels */}
        {xTicks.map((t, i) => {
          const x = PAD.left + xScale.map(t);
          return (
            <text
              key={i}
              x={x}
              y={PAD.top + PLOT_H + 18}
              textAnchor="middle"
              fontSize={10}
              fill="#9C9894"
              fontVariantNumeric="tabular-nums"
            >
              {t.toFixed(1)}
            </text>
          );
        })}

        {/* X axis label */}
        <text
          x={PAD.left + PLOT_W / 2}
          y={H - 8}
          textAnchor="middle"
          fontSize={11}
          fontWeight="600"
          fill="#5C5955"
          letterSpacing="0.05em"
        >
          {metricLabel(xMetric).toUpperCase()}
        </text>

        {/* Y axis label (rotated) */}
        <text
          x={-(PAD.top + PLOT_H / 2)}
          y={16}
          textAnchor="middle"
          fontSize={11}
          fontWeight="600"
          fill="#5C5955"
          letterSpacing="0.05em"
          transform="rotate(-90)"
        >
          {metricLabel(yMetric).toUpperCase()}
        </text>

        {/* Data points */}
        {rows.map((row) => {
          const cx = PAD.left + xScale.map(row[xMetric] ?? 0);
          const cy = PAD.top + PLOT_H - yScale.map(row[yMetric] ?? 0);
          const abbr = row.TEAM_ABBREVIATION;
          return (
            <g key={abbr} className={styles.point}>
              <circle cx={cx} cy={cy} r={5} fill="var(--accent)" opacity={0.82} />
              <text
                x={cx}
                y={cy - 10}
                textAnchor="middle"
                fontSize={9}
                fontWeight="700"
                fill="var(--text)"
                letterSpacing="0.04em"
              >
                {abbr}
              </text>
              <title>
                {abbr} — {metricLabel(xMetric)}: {formatMetric(xMetric, row[xMetric])},{' '}
                {metricLabel(yMetric)}: {formatMetric(yMetric, row[yMetric])}
              </title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
