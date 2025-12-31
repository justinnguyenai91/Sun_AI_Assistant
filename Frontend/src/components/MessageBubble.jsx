// Frontend/src/components/MessageBubble.jsx
import React from "react";

export default function MessageBubble({ sender, text }) {
  const isUser = sender === "user";
  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-2`}
    >
      <div
        className={`max-w-[70%] px-4 py-2 rounded-2xl ${
          isUser
            ? "bg-blue-500 text-white rounded-br-none"
            : "bg-gray-200 text-gray-800 rounded-bl-none"
        }`}
      >
        {text}
      </div>
    </div>
  );
}
