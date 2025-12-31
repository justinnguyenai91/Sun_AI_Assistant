// src/components/ChatInput.jsx
import { useState } from "react";

export default function ChatInput({ onSend }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput("");
  };

  return (
    <div className="flex items-center gap-2 p-3 border-t">
      <input
        className="flex-1 border rounded-xl px-3 py-2 focus:outline-none"
        placeholder="Nhập tin nhắn..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
      />
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded-xl"
        onClick={handleSend}
      >
        Gửi
      </button>
    </div>
  );
}