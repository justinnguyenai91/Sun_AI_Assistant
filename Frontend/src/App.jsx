// src/App.jsx
import { useState } from "react";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

// Đọc từ Vite env (dev) hoặc từ localStorage (khi người dùng nhập).
const BASE_URL = import.meta.env.VITE_API_BASE || "http://127.0.0.1:9000";
const DEFAULT_KEY = import.meta.env.VITE_API_KEY || ""; // dev only

function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Lấy API key: ưu tiên Vite env; nếu trống thì lấy từ localStorage (user nhập 1 lần)
  const getApiKey = () => {
    return DEFAULT_KEY || localStorage.getItem("SUN_API_KEY") || "";
  };

  const ensureApiKey = async () => {
    let key = getApiKey();
    if (!key) {
      key = window.prompt("Nhập API key (do DTHAUS cấp):")?.trim() || "";
      if (key) localStorage.setItem("SUN_API_KEY", key);
    }
    return key;
  };

  const sendMessage = async (text) => {
    const userMsg = { sender: "user", text };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const apiKey = await ensureApiKey();
      if (!apiKey) throw new Error("Missing API key");

      // 1. Sửa URL: bỏ v1/chat/completions, chỉ để /chat
      const resp = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "Content-Type": "application/json"
        },
        // 2. Sửa Body: chỉ gửi đúng trường "message" như file main.py yêu cầu
        body: JSON.stringify({
          message: text 
        })
      });

      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      // 3. Sửa cách lấy câu trả lời: lấy từ data.reply (như trong main.py định nghĩa)
      const reply = data.reply || "Xin lỗi, tôi không nhận được phản hồi.";

      setMessages(prev => [...prev, { sender: "ai", text: reply }]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { sender: "ai", text: `⚠️ Lỗi khi gọi API: ${String(err)}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-center gap-3 text-2xl font-semibold py-4 bg-gradient-to-r from-indigo-500 to-blue-500 text-white shadow-md">
        <span className="text-3xl animate-bounce">🤖</span>
        <span>DTHAUS AI Assistant</span>
      </header>
      <ChatWindow messages={messages} isLoading={loading} />
      <ChatInput onSend={sendMessage} />
    </div>
  );
}

export default App;
