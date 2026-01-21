// src/components/ChatInput.jsx
import { useState } from "react";
import VoiceInput from "./VoiceInput";
import { IconSend } from "./Icons.jsx";

export default function ChatInput({ onSend, isLoading, onCancel, locale }) {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);

  const handleSend = () => {
    if (isLoading) return;
    if (!input.trim()) return;
    onSend(input);
    setInput("");
  };

  const handleCancel = () => {
    if (!isLoading) return;
    onCancel?.();
  };

  const handleVoiceResult = (transcript, isFinal) => {
    setInput(transcript);
    if (isFinal) {
      setIsListening(false);
    }
  };

  const handleQuickAction = (action) => {
    if (isLoading) return;
    const queries = {
      summary_vi: "Tóm tắt dữ liệu sản lượng hôm nay",
      summary_en: "Summarize today's production data",
      defect_vi: "Thống kê lỗi nhiều nhất hôm nay",
      defect_en: "Show top defects today",
      oee_vi: "Tính OEE các dây chuyền hôm nay",
      oee_en: "Calculate OEE for all lines today",
    };
    const query = queries[`${action}_${locale}`] || queries[action];
    if (query) {
      setInput(query);
    }
  };

  const isVi = String(locale || "en").toLowerCase().startsWith("vi");

  return (
    <div className="chat-input">
      {/* Quick Actions */}
      <div className="quick-actions">
        <button 
          className="quick-action-btn" 
          onClick={() => handleQuickAction('summary')}
          disabled={isLoading}
        >
          <span>📊</span>
          <span>{isVi ? "Tóm tắt" : "Summary"}</span>
        </button>
        <button 
          className="quick-action-btn" 
          onClick={() => handleQuickAction('defect')}
          disabled={isLoading}
        >
          <span>⚠️</span>
          <span>{isVi ? "Lỗi" : "Defects"}</span>
        </button>
        <button 
          className="quick-action-btn" 
          onClick={() => handleQuickAction('oee')}
          disabled={isLoading}
        >
          <span>📈</span>
          <span>OEE</span>
        </button>
      </div>

      {/* Input Area */}
      <div className="input-wrapper">
        <textarea
          className="chat-input-box"
          placeholder={isVi ? "Nhập câu hỏi của bạn hoặc nói..." : "Type or speak your question..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          rows={1}
        />
        <VoiceInput
          isListening={isListening}
          onStart={() => setIsListening(true)}
          onStop={() => setIsListening(false)}
          onResult={handleVoiceResult}
          onError={(error) => {
            console.error('Voice input error:', error);
            setIsListening(false);
          }}
          locale={locale}
        />
        <button
          className={`btn-primary${isLoading ? " is-loading" : ""}`}
          onClick={isLoading ? handleCancel : handleSend}
          title={isLoading ? (isVi ? "Huỷ request" : "Cancel request") : (isVi ? "Gửi" : "Send")}
          aria-label={isLoading ? (isVi ? "Huỷ request" : "Cancel request") : (isVi ? "Gửi" : "Send")}
        >
          <span className="btn-inner">
            {isLoading && <span className="btn-spinner" aria-hidden="true" />}
            {!isLoading && <IconSend size={16} />}
            <span className="btn-text">{isLoading ? (isVi ? "Huỷ" : "Cancel") : isVi ? "Gửi" : "Send"}</span>
          </span>
        </button>
      </div>
    </div>
  );
}