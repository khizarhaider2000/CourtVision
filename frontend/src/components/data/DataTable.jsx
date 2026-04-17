import { useState, useMemo } from 'react';
import { formatMetric, ratingColorClass } from '../../utils/format.js';
import { metricLabel } from '../../utils/format.js';
import styles from './DataTable.module.css';

const NON_NUMERIC_COLS = new Set(['TEAM_ABBREVIATION', 'TEAM_NAME', 'LINEUP']);

function isNumeric(col) {
  return !NON_NUMERIC_COLS.has(col);
}

export default function DataTable({ rows, showRank = false }) {
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('desc');

  const columns = useMemo(() => {
    if (!rows || rows.length === 0) return [];
    return Object.keys(rows[0]);
  }, [rows]);

  const sorted = useMemo(() => {
    if (!sortCol || !rows) return rows;
    return [...rows].sort((a, b) => {
      const va = a[sortCol] ?? (sortDir === 'desc' ? -Infinity : Infinity);
      const vb = b[sortCol] ?? (sortDir === 'desc' ? -Infinity : Infinity);
      if (sortDir === 'asc') return va < vb ? -1 : va > vb ? 1 : 0;
      return va > vb ? -1 : va < vb ? 1 : 0;
    });
  }, [rows, sortCol, sortDir]);

  function handleSort(col) {
    if (!isNumeric(col)) return;
    if (sortCol === col) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortCol(col);
      setSortDir('desc');
    }
  }

  if (!rows || rows.length === 0) return null;

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            {showRank && <th className={`${styles.th} ${styles.rankTh}`}>#</th>}
            {columns.map((col) => (
              <th
                key={col}
                className={`${styles.th} ${isNumeric(col) ? styles.numericTh : ''} ${
                  sortCol === col ? styles.sorted : ''
                }`}
                onClick={() => handleSort(col)}
                aria-sort={
                  sortCol === col
                    ? sortDir === 'desc'
                      ? 'descending'
                      : 'ascending'
                    : undefined
                }
              >
                <span>{metricLabel(col)}</span>
                {isNumeric(col) && (
                  <span className={styles.sortIndicator}>
                    {sortCol === col ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.TEAM_ABBREVIATION ?? row.LINEUP ?? i} className={styles.row}>
              {showRank && <td className={`${styles.td} ${styles.rankTd}`}>{i + 1}</td>}
              {columns.map((col) => {
                const val = row[col];
                const colorClass = ratingColorClass(col, val);
                const numericCol = isNumeric(col);
                return (
                  <td
                    key={col}
                    className={`${styles.td} ${numericCol ? styles.numericTd : ''}`}
                  >
                    {col === 'TEAM_ABBREVIATION' ? (
                      <span className={styles.teamAbbr}>{val}</span>
                    ) : (
                      <span className={colorClass ? styles[colorClass] : ''}>
                        {formatMetric(col, val)}
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
