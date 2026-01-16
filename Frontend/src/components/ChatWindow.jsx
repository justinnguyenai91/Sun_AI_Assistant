// Frontend/src/components/ChatWindow.jsx
import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";
import Loader from "./Loader.jsx";

export default function ChatWindow({ messages, isLoading, locale }) {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      {messages.map((msg, idx) => (
        <MessageBubble key={idx} message={{ ...msg, locale: msg?.locale || locale }} />
      ))}
      {isLoading && <Loader />}
      <div ref={chatEndRef} />
    </div>
  );
}
