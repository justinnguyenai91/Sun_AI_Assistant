// Frontend/src/components/ExportButton.jsx
import React from 'react';
import './ExportButton.css';

export default function ExportButton({ data, filename = 'export', locale = 'vi' }) {
  const exportToCSV = () => {
    if (!data || data.length === 0) {
      alert(locale === 'vi' ? 'Không có dữ liệu để xuất' : 'No data to export');
      return;
    }

    // Get all column headers
    const headers = Object.keys(data[0]);
    
    // Create CSV content
    const csvRows = [];
    
    // Add header row
    csvRows.push(headers.join(','));
    
    // Add data rows
    data.forEach(row => {
      const values = headers.map(header => {
        const value = row[header];
        // Escape quotes and wrap in quotes if contains comma
        const escaped = String(value).replace(/"/g, '""');
        return escaped.includes(',') ? `"${escaped}"` : escaped;
      });
      csvRows.push(values.join(','));
    });
    
    // Create blob and download
    const csvContent = '\uFEFF' + csvRows.join('\n'); // Add BOM for Excel UTF-8 support
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportToJSON = () => {
    if (!data || data.length === 0) {
      alert(locale === 'vi' ? 'Không có dữ liệu để xuất' : 'No data to export');
      return;
    }

    const jsonContent = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0, 10)}.json`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="export-button-group">
      <button
        className="export-btn export-csv"
        onClick={exportToCSV}
        title={locale === 'vi' ? 'Xuất CSV' : 'Export CSV'}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M8 2v8m0 0L5 7m3 3l3-3"/>
          <path d="M2 12h12"/>
        </svg>
        <span>CSV</span>
      </button>
      <button
        className="export-btn export-json"
        onClick={exportToJSON}
        title={locale === 'vi' ? 'Xuất JSON' : 'Export JSON'}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M8 2v8m0 0L5 7m3 3l3-3"/>
          <path d="M2 12h12"/>
        </svg>
        <span>JSON</span>
      </button>
    </div>
  );
}
