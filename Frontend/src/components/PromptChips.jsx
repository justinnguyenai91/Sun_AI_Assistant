// Frontend/src/components/PromptChips.jsx
import React from 'react';
import './PromptChips.css';

export default function PromptChips({ onSelect, locale = 'vi', visible = true }) {
  if (!visible) return null;

  const prompts = locale === 'vi' ? [
    { id: 1, icon: '📊', text: 'Thống kê sản lượng hôm nay' },
    { id: 2, icon: '⚠️', text: 'Top 5 lỗi nhiều nhất tháng này' },
    { id: 3, icon: '📈', text: 'OEE của các line tuần này' },
    { id: 4, icon: '🏭', text: 'So sánh chất lượng giữa các nhà máy' },
    { id: 5, icon: '⏱️', text: 'Thời gian downtime trung bình' },
    { id: 6, icon: '🎯', text: 'Tỷ lệ đạt kế hoạch tháng này' },
  ] : [
    { id: 1, icon: '📊', text: 'Production stats today' },
    { id: 2, icon: '⚠️', text: 'Top 5 defects this month' },
    { id: 3, icon: '📈', text: 'OEE by line this week' },
    { id: 4, icon: '🏭', text: 'Quality comparison by factory' },
    { id: 5, icon: '⏱️', text: 'Average downtime' },
    { id: 6, icon: '🎯', text: 'Plan achievement this month' },
  ];

  return (
    <div className="prompt-chips-container">
      <div className="prompt-chips-label">
        {locale === 'vi' ? '💡 Gợi ý câu hỏi:' : '💡 Suggested queries:'}
      </div>
      <div className="prompt-chips-grid">
        {prompts.map(prompt => (
          <button
            key={prompt.id}
            className="prompt-chip"
            onClick={() => onSelect(prompt.text)}
          >
            <span className="prompt-chip-icon">{prompt.icon}</span>
            <span className="prompt-chip-text">{prompt.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
