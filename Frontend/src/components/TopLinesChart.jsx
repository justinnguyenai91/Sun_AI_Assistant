import React, { useMemo } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { t } from '../utils/i18n.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

export default function TopLinesChart({ rows = [], topN = 10, locale = 'en' }) {
  const data = useMemo(() => {
    // aggregate by lineName or lineId
    const map = new Map();
    rows.forEach((r) => {
      const key = r.lineName || r.lineId || 'unknown';
      const prev = map.get(key) || { plan: 0, actual: 0 };
      prev.plan += Number(r.totalPlanQty || 0);
      prev.actual += Number(r.totalActualQty || 0);
      map.set(key, prev);
    });

    const arr = Array.from(map.entries()).map(([k, v]) => ({ line: k, ...v }));
    arr.sort((a, b) => b.actual - a.actual);
    const top = arr.slice(0, topN);

    return {
      labels: top.map((t) => t.line),
      datasets: [
        {
          label: t('terms.plannedQty', locale),
          backgroundColor: 'rgba(54,162,235,0.6)',
          borderColor: 'rgba(54,162,235,1)',
          borderWidth: 1,
          data: top.map((t) => t.plan),
        },
        {
          label: t('terms.actualQty', locale),
          backgroundColor: 'rgba(75,192,192,0.6)',
          borderColor: 'rgba(75,192,192,1)',
          borderWidth: 1,
          data: top.map((t) => t.actual),
        },
      ],
    };
  }, [rows, topN, locale]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'top' } },
    scales: { y: { beginAtZero: true } },
  };

  return (
    <div style={{ width: '100%', height: 420 }}>
      <Bar data={data} options={options} />
    </div>
  );
}
