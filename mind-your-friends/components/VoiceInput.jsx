'use client';

import { useState, useRef, useCallback } from 'react';

const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

export default function VoiceInput({ onTranscript, disabled }) {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef(null);

  const start = useCallback(() => {
    if (!SpeechRecognition || disabled) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const current = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join('');
      setTranscript(current);

      if (event.results[0].isFinal) {
        setListening(false);
        onTranscript(current);
      }
    };

    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [disabled, onTranscript]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  if (!SpeechRecognition) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        disabled={disabled}
        onClick={listening ? stop : start}
        className={`rounded-full p-3 transition ${
          listening
            ? 'bg-game-red animate-pulse'
            : 'bg-game-card hover:bg-game-accent'
        } disabled:opacity-40`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
          <path d="M12 14a3 3 0 003-3V5a3 3 0 10-6 0v6a3 3 0 003 3zm5-3a5 5 0 01-10 0H5a7 7 0 0014 0h-2zm-5 9a1 1 0 01-1-1v-2h2v2a1 1 0 01-1 1z"/>
        </svg>
      </button>
      {transcript && (
        <span className="text-sm text-gray-400 italic">{transcript}</span>
      )}
    </div>
  );
}
