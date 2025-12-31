// Frontend/src/components/Loader.jsx
import React from "react";

export default function Loader() {
  return (
    <div className="flex justify-start mb-2">
      <div className="bg-gray-200 text-gray-700 px-4 py-2 rounded-2xl">
        <span className="animate-pulse">AI đang phản hồi...</span>
      </div>
    </div>
  );
}
