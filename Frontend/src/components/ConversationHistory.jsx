// Frontend/src/components/ConversationHistory.jsx
import React, { useState } from "react";
import { t } from "../utils/i18n.js";
import "./ConversationHistory.css";
import { IconTrash } from "./Icons.jsx";

export default function ConversationHistory({ 
  sessions, 
  currentSessionId, 
  onNewChat, 
  onSelectSession, 
  onDeleteSession,
  locale,
  theme,
  onThemeToggle,
  onQuickFilter,
  isMobileOpen,
  onCloseMobile
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return locale === "vi" ? "Vừa xong" : "Just now";
    if (diffMins < 60) return `${diffMins} ${locale === "vi" ? "phút trước" : "min ago"}`;
    if (diffHours < 24) return `${diffHours} ${locale === "vi" ? "giờ trước" : "hr ago"}`;
    if (diffDays < 7) return `${diffDays} ${locale === "vi" ? "ngày trước" : "day ago"}`;
    
    return date.toLocaleDateString(locale === "vi" ? "vi-VN" : "en-US", {
      month: "short",
      day: "numeric",
    });
  };

  const getSessionTitle = (session) => {
    if (session.title) return session.title;
    
    // Find first user message for title
    const firstUserMsg = session.messages?.find(m => 
      m?.sender === 'user' || m?.sender === 'human' || m?.sender === 'me'
    );
    const firstMessage = firstUserMsg?.text || firstUserMsg?.content || session.messages?.[0]?.content || "";
    
    if (firstMessage) {
      // Create smart summary based on keywords
      const lower = firstMessage.toLowerCase();
      if (lower.includes('oee')) return '📊 OEE ' + (firstMessage.length > 25 ? firstMessage.substring(0, 25) + '...' : firstMessage);
      if (lower.includes('lỗi') || lower.includes('defect')) return '⚠️ ' + (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage);
      if (lower.includes('sản lượng') || lower.includes('production')) return '📈 ' + (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage);
      if (lower.includes('line')) return '🏭 ' + (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage);
      if (lower.includes('chất lượng') || lower.includes('quality')) return '✓ ' + (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage);
      if (lower.includes('downtime')) return '⏱️ ' + (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage);
      if (lower.includes('so sánh') || lower.includes('compare')) return '⚖️ ' + (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage);
      if (lower.includes('thống kê') || lower.includes('statistic')) return '📊 ' + (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage);
      
      // Fallback: use first 35 chars of the message
      if (firstMessage.length > 35) {
        return '💬 ' + firstMessage.substring(0, 35) + "...";
      }
      return '💬 ' + firstMessage;
    }
    return locale === "vi" ? "💬 Cuộc trò chuyện mới" : "💬 New conversation";
  };

  const quickFilters = [
    { 
      id: 'today_stats',
      icon: '📊',
      label: locale === "vi" ? "Thống kê hôm nay" : "Today's Stats",
      query: locale === "vi" ? "Thống kê sản lượng hôm nay" : "Today's production stats"
    },
    { 
      id: 'top_defects',
      icon: '⚠️',
      label: locale === "vi" ? "Lỗi nhiều nhất" : "Top Defects",
      query: locale === "vi" ? "Top 5 lỗi nhiều nhất hôm nay" : "Top 5 defects today"
    },
    { 
      id: 'oee_lines',
      icon: '📈',
      label: locale === "vi" ? "OEE các line" : "OEE by Lines",
      query: locale === "vi" ? "OEE của các line hôm nay" : "OEE of all lines today"
    },
    { 
      id: 'database',
      icon: '🗄️',
      label: locale === "vi" ? "Truy vấn dữ liệu" : "Database Query",
      query: locale === "vi" ? "Cho tôi xem dữ liệu line A hôm nay" : "Show me line A data today"
    },
  ];

  const groupSessionsByTime = () => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    const grouped = {
      today: [],
      yesterday: [],
      lastWeek: [],
      older: [],
    };

    sessions.forEach((session) => {
      const sessionDate = new Date(session.timestamp);
      if (sessionDate >= today) {
        grouped.today.push(session);
      } else if (sessionDate >= yesterday) {
        grouped.yesterday.push(session);
      } else if (sessionDate >= lastWeek) {
        grouped.lastWeek.push(session);
      } else {
        grouped.older.push(session);
      }
    });

    return grouped;
  };

  const grouped = groupSessionsByTime();

  const renderGroup = (title, sessionsList) => {
    if (!sessionsList || sessionsList.length === 0) return null;

    return (
      <div className="session-group" key={title}>
        <div className="session-group-title">{title}</div>
        {sessionsList.map((session) => (
          <div
            key={session.id}
            className={`session-item ${session.id === currentSessionId ? "active" : ""}`}
            onClick={() => onSelectSession(session.id)}
          >
            <div className="session-info">
              <div className="session-title">{getSessionTitle(session)}</div>
              <div className="session-meta">
                <span className="session-time">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                  {formatTimestamp(session.timestamp)}
                </span>
                <span className="session-count">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  {session.messageCount || session.messages?.length || 0}
                </span>
              </div>
            </div>
            <button
              className="session-delete"
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm(locale === "vi" ? "Xóa cuộc trò chuyện này?" : "Delete this conversation?")) {
                  onDeleteSession(session.id);
                }
              }}
              title={locale === "vi" ? "Xóa" : "Delete"}
            >
              <IconTrash size={16} />
            </button>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className={`conversation-history ${isCollapsed ? "collapsed" : ""} ${isMobileOpen ? "mobile-open" : ""}`}>
      {/* Mobile overlay to close sidebar */}
      {isMobileOpen && (
        <div 
          className="mobile-overlay"
          onClick={onCloseMobile}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 999
          }}
        />
      )}
      <div className="history-header">
        <button
          className="toggle-sidebar"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? (locale === "vi" ? "Mở rộng" : "Expand") : (locale === "vi" ? "Thu gọn" : "Collapse")}
          aria-label="Toggle sidebar"
          style={{ fontSize: '18px', fontWeight: 'bold' }}
        >
          {isCollapsed ? "▶" : "◀"}
        </button>
        {!isCollapsed && (
          <>
            <div className="header-title-row">
              <h3>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{display: 'inline', marginRight: '8px', verticalAlign: 'middle'}}>
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                {locale === "vi" ? "DTHAUS AI" : "DTHAUS AI"}
              </h3>
              <button 
                className="theme-toggle-btn" 
                onClick={onThemeToggle}
                title={theme === "dark" ? (locale === "vi" ? "Chế độ sáng" : "Light Mode") : (locale === "vi" ? "Chế độ tối" : "Dark Mode")}
              >
                {theme === "dark" ? "Light" : "Dark"}
              </button>
            </div>
            <button className="new-chat-btn" onClick={onNewChat} title={locale === "vi" ? "Trò chuyện mới" : "New chat"}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span>{locale === "vi" ? "Mới" : "New"}</span>
            </button>
          </>
        )}
      </div>

      {!isCollapsed && (
        <>
          {/* Quick Filters Section */}
          <div className="quick-filters">
            <div className="quick-filters-title">{locale === "vi" ? "⚡ Truy vấn nhanh" : "⚡ Quick Actions"}</div>
            {quickFilters.map((filter) => (
              <button
                key={filter.id}
                className="quick-filter-btn"
                onClick={() => onQuickFilter?.(filter.query)}
                title={filter.query}
              >
                <span className="filter-icon">{filter.icon}</span>
                <span className="filter-label">{filter.label}</span>
              </button>
            ))}
          </div>

          {/* Sessions List */}
          <div className="sessions-list">
            {sessions.length === 0 ? (
              <div className="no-sessions">
                {locale === "vi" ? "Chưa có cuộc trò chuyện nào" : "No conversations yet"}
              </div>
            ) : (
              <>
                {renderGroup(locale === "vi" ? "Hôm nay" : "Today", grouped.today)}
                {renderGroup(locale === "vi" ? "Hôm qua" : "Yesterday", grouped.yesterday)}
                {renderGroup(locale === "vi" ? "7 ngày qua" : "Last 7 days", grouped.lastWeek)}
                {renderGroup(locale === "vi" ? "Cũ hơn" : "Older", grouped.older)}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
