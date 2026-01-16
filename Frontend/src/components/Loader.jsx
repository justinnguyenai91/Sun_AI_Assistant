// Frontend/src/components/Loader.jsx
import React from "react";

export default function Loader() {
  return (
    <div className="message-row left">
      <div className="message-bubble ai">
        <span className="loader-text">AI đang phản hồi...</span>
      </div>
    </div>
  );
}
