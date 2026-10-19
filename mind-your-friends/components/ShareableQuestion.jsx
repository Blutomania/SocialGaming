'use client';

import { useRef, useState } from 'react';

// Shareable Question (CLAUDE.md item 35, GAME_DESIGN.md → "Shareable Question").
//
// The shareable artifact is a QUESTION from the game framed as a challenge to
// the sharer's own following — not a scoreboard. A scoreboard only means
// something to the people who were in the room; a hard trivia question travels,
// because guessing it drives replies.
//
// The card deliberately does NOT show the answer. That's the mechanic, not an
// oversight: a card with the answer is a flashcard, a card without one is an
// argument. The answer is a separate card the sharer can post as a follow-up.
//
// Rendered client-side to a canvas and shared via the Web Share API (download
// fallback), so this needs no image host, no storage, and no database — which
// matters because MYF deliberately has none (CLAUDE.md → What NOT to Do).

const CARD_SIZE = 1080; // square — the safest single size across social platforms

export default function ShareableQuestion({ questionLog, gameCode }) {
  const canvasRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const [showingAnswer, setShowingAnswer] = useState(false);
  const [status, setStatus] = useState('');

  const questions = questionLog ?? [];
  if (questions.length === 0) return null;

  const choose = (entry) => {
    setSelected(entry);
    setShowingAnswer(false);
    setStatus('');
    // Defer so the canvas exists before we draw into it.
    requestAnimationFrame(() => drawCard(canvasRef.current, entry, false, gameCode));
  };

  const toggleAnswer = () => {
    const next = !showingAnswer;
    setShowingAnswer(next);
    drawCard(canvasRef.current, selected, next, gameCode);
  };

  const share = async () => {
    const canvas = canvasRef.current;
    if (!canvas || !selected) return;

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    if (!blob) {
      setStatus('Could not render the card.');
      return;
    }

    const file = new File([blob], `mind-your-friends-${gameCode}.png`, { type: 'image/png' });

    // navigator.share with files is mobile-mostly; canShare() is the only
    // reliable feature test, and it must be called with the actual payload.
    if (navigator.canShare?.({ files: [file] })) {
      try {
        await navigator.share({ files: [file] });
        setStatus('Shared!');
        return;
      } catch (err) {
        // A user cancelling the share sheet lands here too — not an error.
        if (err?.name === 'AbortError') return;
      }
    }

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = file.name;
    link.click();
    URL.revokeObjectURL(url);
    setStatus('Downloaded — post it wherever you like.');
  };

  return (
    <div className="space-y-4 text-left">
      <div>
        <h3 className="text-xl font-semibold">Share a question</h3>
        <p className="text-sm text-ui-faint">
          Pick the one that broke the room. Your followers won&apos;t see the answer.
        </p>
      </div>

      <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
        {questions.map((entry) => (
          <li key={entry.index}>
            <button
              type="button"
              onClick={() => choose(entry)}
              // One question is picked at a time and stays picked: a choice.
              aria-pressed={selected?.index === entry.index}
              className="choice w-full p-3 text-left text-sm"
            >
              <span className="block">{entry.question}</span>
              <span className="mt-1 block text-xs opacity-80">
                {entry.category}
                {entry.roomMissedIt && ' — nobody got it'}
              </span>
            </button>
          </li>
        ))}
      </ul>

      {/* Kept mounted but visually scaled down; drawing targets the full-size
          backing store so the exported PNG is 1080px regardless of display. */}
      <div className={selected ? 'space-y-3' : 'hidden'}>
        <canvas
          ref={canvasRef}
          width={CARD_SIZE}
          height={CARD_SIZE}
          className="w-full max-w-xs border-2 border-ui-line"
        />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={share} className="act">
            Share
          </button>
          <button
            type="button"
            onClick={toggleAnswer}
            className="act text-sm"
          >
            {showingAnswer ? 'Hide answer' : 'Make answer card'}
          </button>
        </div>
        {status && <p className="text-sm text-ui-faint">{status}</p>}
      </div>
    </div>
  );
}

// --- Canvas rendering --------------------------------------------------------

// The exported image keeps its own colours on purpose for now: this card is
// parked and frozen by owner decision (CLAUDE.md → Parked), and the image is
// what a sharer's followers see, so changing it is a product call, not a
// restyle. It predates slate and does not use lib/palette.js — flagged in
// docs/DECISIONS.md item 53.
function drawCard(canvas, entry, withAnswer, gameCode) {
  if (!canvas || !entry) return;
  const ctx = canvas.getContext('2d');
  const S = CARD_SIZE;

  ctx.fillStyle = '#12101c';
  ctx.fillRect(0, 0, S, S);

  ctx.fillStyle = '#f5c518';
  ctx.fillRect(0, 0, S, 12);

  const pad = 84;
  let y = 168;

  ctx.fillStyle = '#f5c518';
  ctx.font = 'bold 34px system-ui, sans-serif';
  ctx.fillText(entry.category?.toUpperCase() ?? 'TRIVIA', pad, y);

  if (entry.categoryAttribution) {
    y += 46;
    ctx.fillStyle = '#8f8aa3';
    ctx.font = '30px system-ui, sans-serif';
    ctx.fillText(`submitted by ${entry.categoryAttribution}`, pad, y);
  }

  y += 92;
  ctx.fillStyle = '#ffffff';
  y = wrapText(ctx, entry.question, pad, y, S - pad * 2, 66, 'bold 56px system-ui, sans-serif');

  if (withAnswer) {
    y += 60;
    ctx.fillStyle = '#f5c518';
    ctx.font = 'bold 34px system-ui, sans-serif';
    ctx.fillText('ANSWER', pad, y);
    y += 60;
    ctx.fillStyle = '#ffffff';
    y = wrapText(ctx, entry.answer, pad, y, S - pad * 2, 56, 'bold 46px system-ui, sans-serif');
  }

  // Hook line, pinned to the bottom. This is what turns the card from a
  // flashcard into a challenge, so it gets its own visual weight.
  const hook = withAnswer
    ? 'Did you get it?'
    : entry.roomMissedIt
    ? 'Nobody in the room got this.'
    : entry.outcomeSummary ?? 'Can you get it?';

  ctx.fillStyle = '#8f8aa3';
  ctx.font = '32px system-ui, sans-serif';
  ctx.fillText(hook, pad, S - 148);

  ctx.fillStyle = '#4c4860';
  ctx.font = '28px system-ui, sans-serif';
  ctx.fillText(`Mind Your Friends · game ${gameCode ?? ''}`.trim(), pad, S - 88);
}

// Wraps text to a max width and returns the y position after the last line.
function wrapText(ctx, text, x, y, maxWidth, lineHeight, font) {
  ctx.font = font;
  const words = String(text ?? '').split(' ');
  let line = '';
  let cursorY = y;

  for (const word of words) {
    const attempt = line ? `${line} ${word}` : word;
    if (ctx.measureText(attempt).width > maxWidth && line) {
      ctx.fillText(line, x, cursorY);
      line = word;
      cursorY += lineHeight;
    } else {
      line = attempt;
    }
  }
  if (line) {
    ctx.fillText(line, x, cursorY);
    cursorY += lineHeight;
  }
  return cursorY;
}
