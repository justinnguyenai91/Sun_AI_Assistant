// Frontend/src/components/VoiceInput.jsx
import React, { useEffect, useRef } from 'react';
import './VoiceInput.css';
import { IconMic } from './Icons.jsx';

export default function VoiceInput({ 
  isListening, 
  onStart, 
  onStop, 
  onResult, 
  onError,
  locale = 'vi' 
}) {
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Check browser support
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.warn('Web Speech API not supported');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = locale === 'vi' ? 'vi-VN' : 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      console.log('Voice recognition started');
    };

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('');
      
      if (onResult) {
        onResult(transcript, event.results[0].isFinal);
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      if (onError) {
        onError(event.error);
      }
      if (onStop) {
        onStop();
      }
    };

    recognition.onend = () => {
      console.log('Voice recognition ended');
      if (onStop) {
        onStop();
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [locale, onResult, onError, onStop]);

  useEffect(() => {
    if (!recognitionRef.current) return;

    if (isListening) {
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.error('Failed to start recognition:', e);
      }
    } else {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // Already stopped
      }
    }
  }, [isListening]);

  const handleClick = () => {
    if (isListening) {
      onStop?.();
    } else {
      onStart?.();
    }
  };

  return (
    <button
      className={`voice-input-btn ${isListening ? 'listening' : ''}`}
      onClick={handleClick}
      title={locale === 'vi' ? 'Nhập bằng giọng nói' : 'Voice input'}
      type="button"
    >
      <IconMic size={20} />
    </button>
  );
}
