'use client';

// DEV-ONLY screen preview. Not linked from anywhere and not part of the game.
//
// Why it exists: the aesthetics passes are done by looking at renderings, and
// looking at the answer screen used to mean playing a real three-player game
// with real Claude calls until the state you wanted to judge came up — which
// costs money, takes minutes, and cannot reliably produce "the room's view
// during the exclusive window" on demand at all. This renders every Flow B
// moment side by side from fixtures, instantly and for nothing.
//
// The fixtures are hand-written to match playerView()'s ANSWER-phase branch in
// lib/gameState.js. They are a rendering aid, NOT a contract test: if that
// branch changes shape, this page will render something wrong rather than
// fail, so check it against the real thing when the view changes.

import { useEffect, useState } from 'react';
import BrandBar from '../../../components/BrandBar';
import GameBoard from '../../../components/GameBoard';
import HostStage from '../../../components/HostStage';

const noopSocket = { emit: () => {} };

const PLAYERS = [
  { id: 'p1', name: 'Priya', score: 340, registered: true, connected: true },
  { id: 'p2', name: 'Marcus', score: 275, registered: true, connected: true },
  { id: 'p3', name: 'Sarah', score: 410, registered: true, connected: true },
];

const RULE = {
  id: 'eli5',
  name: 'ELI5',
  emoji: '🍼',
  description: 'The host asks it like you are five. Answer normally.',
  submissionBased: false,
  lineupBased: false,
  timerSeconds: 40,
};

function base(now) {
  return {
    phase: 'ANSWER',
    code: 'WXYZ',
    players: PLAYERS,
    myPlayerId: 'p2',
    questionIndex: 2,
    roundNumber: 1,
    activePlayerIndex: 0,
    answererIndex: 0,
    roundRule: RULE,
    currentWager: 100,
    buzzPoints: 75,
    difficultyTier: 3,
    question: 'Which planet in our solar system spins backwards compared with the rest?',
    hostQuip: 'Marcus, you have been quiet — suspiciously quiet.',
    lockedCount: 1,
    spentAttempts: [],
    answerOpensAt: now,
    buzzOpensAt: now,
    lockClosesAt: now,
    activeWindowSeconds: 8,
    iAmAnswerer: false,
    iCanAnswer: false,
    iCanPass: false,
    iCanLock: false,
    iCanBuzz: false,
    myLockedAnswer: null,
    myAttempt: null,
  };
}

// Each entry is one moment of Flow B, as one specific player sees it.
function states(now) {
  const s = (extra) => ({ ...base(now), ...extra });
  return [
    ['Reading window — everyone', s({
      answerOpensAt: now + 4000, buzzOpensAt: now + 12000, lockClosesAt: now + 12000,
    })],
    ['Exclusive window — the answerer', s({
      myPlayerId: 'p1', iAmAnswerer: true, iCanAnswer: true, iCanPass: true,
      answerOpensAt: now - 1000, buzzOpensAt: now + 7000, lockClosesAt: now + 7000,
    })],
    ['Exclusive window — the room, still typing', s({
      iCanLock: true,
      answerOpensAt: now - 1000, buzzOpensAt: now + 7000, lockClosesAt: now + 7000,
    })],
    ['Exclusive window — the room, already locked', s({
      myLockedAnswer: 'Venus', lockedCount: 2,
      answerOpensAt: now - 1000, buzzOpensAt: now + 7000, lockClosesAt: now + 7000,
    })],
    ['Buzzers open — locked and holding it', s({
      iCanBuzz: true, myLockedAnswer: 'Venus', lockedCount: 2,
      answerOpensAt: now - 9000, buzzOpensAt: now - 1000, lockClosesAt: now - 1000,
      spentAttempts: [{ playerId: 'p1', name: 'Priya', correct: false, passed: false, timedOut: false }],
    })],
    ['Buzzers open — never locked, out of it', s({
      answerOpensAt: now - 9000, buzzOpensAt: now - 1000, lockClosesAt: now - 1000,
      lockedCount: 2,
      spentAttempts: [{ playerId: 'p1', name: 'Priya', correct: false, passed: true, timedOut: false }],
    })],
  ];
}

// Names every element whose box runs past the viewport, worst first.
//
// This exists because a horizontal overflow has now broken a phone layout
// twice (the brand bar at 390px, and this screen), and both times the build
// was perfectly happy and the screenshot only showed that SOMETHING was cut —
// never what. Reading it off the DOM turns "it's broken on a phone" into a
// element and a number.
function OverflowReport() {
  const [rows, setRows] = useState([]);
  const [dims, setDims] = useState({ vw: 0, sw: 0 });

  useEffect(() => {
    const id = setTimeout(() => {
      const vw = document.documentElement.clientWidth;
      const found = [];
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.right <= vw + 0.5) continue;
        // Only the innermost offender is interesting: an ancestor is wide
        // because of its child, and listing the whole chain buries the cause.
        if ([...el.children].some((c) => c.getBoundingClientRect().right > vw + 0.5)) continue;
        found.push({
          over: Math.round(r.right - vw),
          tag: el.tagName.toLowerCase(),
          cls: (typeof el.className === 'string' ? el.className : '').slice(0, 70),
          text: (el.textContent || '').trim().slice(0, 40),
        });
      }
      found.sort((a, b) => b.over - a.over);
      setRows(found.slice(0, 8));
      setDims({ vw, sw: document.documentElement.scrollWidth });
    }, 300);
    return () => clearTimeout(id);
  }, []);

  // Quiet when the layout is fine, loud when it isn't — a permanent red bar
  // across every screenshot is noise, and noise is what gets ignored.
  const bad = rows.length > 0;
  return (
    <div
      id="overflow-report"
      className={`px-4 py-1 text-xs ${bad ? 'bg-game-red text-white' : 'text-gray-600'}`}
    >
      <p className={bad ? 'font-bold' : ''}>
        viewport {dims.vw} · document {dims.sw} · {rows.length} overflowing
      </p>
      {rows.map((r, i) => (
        <p key={i}>
          +{r.over}px · &lt;{r.tag}&gt; {r.cls} · “{r.text}”
        </p>
      ))}
    </div>
  );
}

export default function AnswerPreview() {
  const [now, setNow] = useState(null);
  const [only, setOnly] = useState(null);
  // `?code=ABCD` swaps the room code, which is what selects the logo palette
  // and the title treatment — the only way to see both marks without starting
  // two real games.
  const [code, setCode] = useState(null);

  useEffect(() => {
    setNow(Date.now());
    const q = new URLSearchParams(window.location.search);
    const n = q.get('only');
    setOnly(n === null ? null : Number(n));
    setCode(q.get('code'));
  }, []);

  if (now === null) return null;

  // `?only=N` renders a single state, which is how you judge one screen
  // instead of six: a screenshot of the stack is always mostly other screens.
  const all = states(now).map(([label, game]) => [label, code ? { ...game, code } : game]);
  const shown = only === null || Number.isNaN(only) ? all : [all[only]].filter(Boolean);

  return (
    <>
      <OverflowReport />
      {shown.map(([label, game]) => (
        <section key={label}>
          <h2 className="px-4 pt-8 text-xs uppercase tracking-[0.3em] text-game-accent md:px-8">
            {label}
          </h2>
          {/* Mirrors app/game/[code]/page.js's wrapper exactly — the brand bar
              and the host-stage column are part of what the answer screen has
              to share the page with, so a preview without them judges a screen
              nobody ever sees. Keep this in step if that layout changes. */}
          <main className="mx-auto max-w-7xl p-4 md:p-8">
            <BrandBar code={game.code} />
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="min-w-0">
                <GameBoard game={game} myId={game.myPlayerId} socket={noopSocket} />
              </div>
              <HostStage />
            </div>
          </main>
        </section>
      ))}
    </>
  );
}
