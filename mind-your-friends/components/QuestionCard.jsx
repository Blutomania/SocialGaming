'use client';

import { useState, useEffect } from 'react';

export default function QuestionCard({
  question,
  roundRule,
  isActivePlayer,
  timerSeconds,
  onSubmit,
  myCard,
  onPlayCard,
  onSkipCard,
  alreadyPlayedCard,
  players,
  socketId,
}) {
  const [answer, setAnswer] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [showHint, setShowHint] = useState(false);

  const ruleEffect = roundRule?.uiEffect;
  const isBlurry = ruleEffect === 'blur';
  const isFlicker = ruleEffect === 'flicker';
  const isHideLastWord = ruleEffect === 'hideLastWord';

  // BACK_IT_UP label
  const isBackItUp = roundRule?.id === 'BACK_IT_UP';

  const timerPct = Math.max(0, (timerSeconds / 15) * 100);
  const timerColor =
    timerSeconds > 8 ? 'bg-game-green' : timerSeconds > 4 ? 'bg-game-gold' : 'bg-game-red';

  function handleSubmit() {
    if (!answer.trim() || submitted) return;
    setSubmitted(true);
    onSubmit(answer.trim());
  }

  function renderQuestionText() {
    let text = question.question;
    if (isHideLastWord) {
      // The server already appended ___? but let's ensure rendering
      return (
        <span>
          {text}
        </span>
      );
    }
    return text;
  }

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">
      {/* Timer bar */}
      <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${timerColor}`}
          style={{ width: `${timerPct}%` }}
        />
      </div>
      <div className="text-center">
        <span className={`font-mono text-2xl font-bold ${timerSeconds <= 4 ? 'text-game-red animate-pulse' : 'text-white'}`}>
          {timerSeconds}s
        </span>
      </div>

      {/* Host quip */}
      {question.hostQuip && (
        <div className="bg-game-card border border-gray-700 rounded-xl px-4 py-2 text-gray-400 text-sm italic text-center">
          &ldquo;{question.hostQuip}&rdquo;
        </div>
      )}

      {/* Question box */}
      <div
        className={`bg-game-card border-2 border-game-accent rounded-2xl p-6 text-center cursor-pointer select-none ${
          isBlurry && !revealed ? 'blurred-text' : isBlurry && revealed ? '' : ''
        } ${isFlicker ? 'flicker-text' : ''}`}
        onClick={() => {
          if (isBlurry) setRevealed(true);
        }}
      >
        {isBlurry && !revealed && (
          <p className="text-gray-500 text-sm mb-2">Tap to reveal question</p>
        )}
        <p className="text-white text-2xl sm:text-3xl font-bold leading-snug">
          {renderQuestionText()}
        </p>
        {isBackItUp && (
          <p className="text-game-gold text-sm mt-3 font-medium">
            Remember: type your answer BACKWARDS!
          </p>
        )}
      </div>

      {/* Hint */}
      {showHint && question.hint && (
        <div className="bg-yellow-900/30 border border-yellow-600/40 rounded-xl px-4 py-3 text-yellow-300 text-sm text-center">
          Hint: {question.hint}
        </div>
      )}

      {/* Answer input — only for active player */}
      {isActivePlayer && !submitted && (
        <div className="space-y-3">
          <input
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder={isBackItUp ? 'Type backwards...' : 'Your answer...'}
            autoFocus
            className="w-full bg-gray-800 rounded-xl px-4 py-4 text-white text-xl placeholder-gray-500 border border-gray-700 focus:outline-none focus:border-game-accent"
          />
          <div className="flex gap-3">
            <button
              onClick={handleSubmit}
              disabled={!answer.trim()}
              className="flex-1 py-4 rounded-xl bg-game-accent hover:bg-violet-500 text-white font-bold text-lg transition disabled:opacity-40"
            >
              Submit Answer
            </button>
            {!showHint && (
              <button
                onClick={() => setShowHint(true)}
                className="px-4 py-4 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-400 transition text-sm"
                title="Show hint"
              >
                💡
              </button>
            )}
          </div>
        </div>
      )}

      {isActivePlayer && submitted && (
        <div className="text-center text-gray-400 animate-pulse py-4">
          Evaluating your answer...
        </div>
      )}

      {!isActivePlayer && (
        <div className="text-center text-gray-500 py-4">
          Waiting for the active player to answer...
        </div>
      )}
    </div>
  );
}
