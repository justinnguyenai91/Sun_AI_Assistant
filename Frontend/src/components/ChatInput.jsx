// src/components/ChatInput.jsx
import { useState } from "react";

export default function ChatInput({ onSend, isLoading, onCancel, locale }) {
  const [input, setInput] = useState("");

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

  const isVi = String(locale || "en").toLowerCase().startsWith("vi");

  return (
    <div className="chat-input">
      <textarea
        className="chat-input-box"
        placeholder="Nhập tin nhắn..."
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
      <button
        className={`btn-primary${isLoading ? " is-loading" : ""}`}
        onClick={isLoading ? handleCancel : handleSend}
        title={isLoading ? (isVi ? "Huỷ request" : "Cancel request") : (isVi ? "Gửi" : "Send")}
        aria-label={isLoading ? (isVi ? "Huỷ request" : "Cancel request") : (isVi ? "Gửi" : "Send")}
      >
        <span className="btn-inner">
          {isLoading && <span className="btn-spinner" aria-hidden="true" />}
          <span className="btn-text">{isLoading ? (isVi ? "Huỷ" : "Cancel") : isVi ? "Gửi" : "Send"}</span>
        </span>
      </button>
    </div>
  );
}