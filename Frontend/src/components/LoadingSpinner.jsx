// Frontend/src/components/LoadingSpinner.jsx
import React from 'react';
import './LoadingSpinner.css';

export default function LoadingSpinner({ message, locale = 'vi' }) {
  const defaultMessage = locale === 'vi' 
    ? 'Đang lấy dữ liệu từ MES...' 
    : 'Fetching data from MES...';

  return (
    <div className="loading-spinner-container">
      <div className="loading-spinner-wrapper">
        <div className="loading-spinner-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <circle 
              cx="20" 
              cy="20" 
              r="16" 
              stroke="url(#spinner-gradient)" 
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray="80 20"
              className="spinner-circle"
            />
            <defs>
              <linearGradient id="spinner-gradient" x1="0" y1="0" x2="40" y2="40">
                <stop offset="0%" stopColor="#3B82F6"/>
                <stop offset="100%" stopColor="#8B5CF6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div className="loading-spinner-text">
          <span>{message || defaultMessage}</span>
          <span className="loading-dots">
            <span className="dot">.</span>
            <span className="dot">.</span>
            <span className="dot">.</span>
          </span>
        </div>
      </div>
    </div>
  );
}
