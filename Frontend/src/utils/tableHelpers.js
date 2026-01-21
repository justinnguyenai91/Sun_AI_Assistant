// src/utils/tableHelpers.js

/**
 * Get color class for metric value based on thresholds
 * @param {number} value - The metric value
 * @param {string} type - The metric type (oee, quality, performance, availability, defectRate)
 * @returns {string} - CSS class name (metric-value high/medium/low)
 */
export function getMetricColorClass(value, type = 'oee') {
  // Convert to number if string
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) return '';
  
  // Thresholds vary by metric type
  const thresholds = {
    oee: { high: 90, medium: 70 },
    quality: { high: 98, medium: 95 },
    performance: { high: 95, medium: 85 },
    availability: { high: 95, medium: 85 },
    defectRate: { high: 2, medium: 5 } // inverted (lower is better)
  };
  
  const thresh = thresholds[type] || thresholds.oee;
  
  // Defect rate is inverted (lower is better)
  if (type === 'defectRate') {
    if (numValue <= thresh.high) return 'metric-value high';
    if (numValue <= thresh.medium) return 'metric-value medium';
    return 'metric-value low';
  }
  
  // Standard metrics (higher is better)
  if (numValue >= thresh.high) return 'metric-value high';
  if (numValue >= thresh.medium) return 'metric-value medium';
  return 'metric-value low';
}

/**
 * Format value with color coding
 * @param {number} value - The metric value
 * @param {string} type - The metric type
 * @param {string} unit - Optional unit (%, pcs, etc.)
 * @returns {object} - { value, colorClass, formatted }
 */
export function formatMetricValue(value, type = 'oee', unit = '%') {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) {
    return { value, colorClass: '', formatted: value };
  }
  
  const colorClass = getMetricColorClass(numValue, type);
  const formatted = `${numValue.toFixed(1)}${unit}`;
  
  return { value: numValue, colorClass, formatted };
}

/**
 * Generate mini bar chart data
 * @param {Array} values - Array of numbers
 * @returns {Array} - Normalized values for rendering (0-100 scale)
 */
export function generateMiniChart(values) {
  if (!values || values.length === 0) return [];
  
  const numValues = values.map(v => typeof v === 'string' ? parseFloat(v) : v).filter(v => !isNaN(v));
  const max = Math.max(...numValues);
  const min = Math.min(...numValues);
  const range = max - min || 1;
  
  return numValues.map(v => ((v - min) / range) * 100);
}

/**
 * Detect metric type from column name
 * @param {string} columnName - The column name
 * @returns {string} - Metric type
 */
export function detectMetricType(columnName) {
  const lower = columnName.toLowerCase();
  
  if (lower.includes('oee')) return 'oee';
  if (lower.includes('quality') || lower.includes('chất lượng')) return 'quality';
  if (lower.includes('performance') || lower.includes('hiệu suất')) return 'performance';
  if (lower.includes('availability') || lower.includes('khả dụng')) return 'availability';
  if (lower.includes('defect') || lower.includes('lỗi')) return 'defectRate';
  
  return 'oee'; // default
}
