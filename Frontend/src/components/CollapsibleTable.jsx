// src/components/CollapsibleTable.jsx
import { useState, useMemo } from 'react';
import { getMetricColorClass, detectMetricType, generateMiniChart } from '../utils/tableHelpers';

/**
 * Collapsible table card with mini charts and color-coded values
 */
function CollapsibleTable({ title, children, rows = [], columns = [] }) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  return (
    <div className="table-card">
      <div 
        className="table-card-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="table-card-title">
          <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="14" height="14" rx="2"/>
            <line x1="3" y1="8" x2="17" y2="8"/>
            <line x1="8" y1="3" x2="8" y2="17"/>
          </svg>
          <span>{title || 'Data Table'}</span>
          {rows && rows.length > 0 && (
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
              ({rows.length} {rows.length === 1 ? 'row' : 'rows'})
            </span>
          )}
        </div>
        <div className={`table-card-toggle ${isExpanded ? 'expanded' : ''}`}>
          <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </div>
      <div className={`table-card-body ${isExpanded ? 'expanded' : ''}`}>
        {children}
      </div>
    </div>
  );
}

/**
 * Enhanced table cell with color coding for metrics
 */
export function EnhancedTableCell({ value, columnName, allValues = [] }) {
  // Detect if this is a metric column
  const metricColumns = [
    'oee', 'quality', 'performance', 'availability',
    'totalActualQty', 'totalPlanQty', 'totalDefectQty',
    'defectRate', 'yield', 'defect_ppm'
  ];
  
  const isMetric = metricColumns.some(m => 
    columnName.toLowerCase().includes(m.toLowerCase())
  );
  
  if (!isMetric) {
    return <span>{value}</span>;
  }
  
  // Parse numeric value
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) {
    return <span>{value}</span>;
  }
  
  // Detect metric type and get color class
  const metricType = detectMetricType(columnName);
  const colorClass = getMetricColorClass(numValue, metricType);
  
  // Show mini chart if we have historical values
  const showChart = allValues && allValues.length > 3;
  
  return (
    <span className="metric-cell">
      <span className={colorClass}>
        {typeof value === 'number' ? value.toFixed(1) : value}
        {columnName.toLowerCase().includes('rate') && '%'}
      </span>
      {showChart && (
        <span className="mini-chart">
          {generateMiniChart(allValues).map((height, idx) => (
            <span 
              key={idx}
              className="bar-mini"
              style={{ height: `${height}%` }}
            />
          ))}
        </span>
      )}
    </span>
  );
}

export default CollapsibleTable;
