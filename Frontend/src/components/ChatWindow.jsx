// Frontend/src/components/ChatWindow.jsx
import React, { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";
import Loader from "./Loader.jsx";

export default function ChatWindow({ messages, isLoading }) {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
      {messages.map((msg, idx) => (
        <MessageBubble key={idx} sender={msg.sender} text={msg.text} />
      ))}
      {isLoading && <Loader />}
      <div ref={chatEndRef} />
    </div>
  );
}
