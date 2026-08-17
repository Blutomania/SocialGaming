'use client';

import { useEffect, useRef, useState } from 'react';
import CategoryPicker from './CategoryPicker';
import CardHand from './CardHand';
import VoiceInput from './VoiceInput';
import { MIN_WAGER, MAX_WAGER, TOTAL_QUESTIONS, QUESTIONS_PER_ROUND } from '../lib/constants';

export default function GameBoard({ game, myId, socket }) {
  const round = game.roundNumber ?? Math.floor(game.questionIndex / QUESTIONS_PER_ROUND) + 1;
  const questionInRound = (game.questionIndex % QUESTIONS_PER_ROUND) + 1;
  // Round 1 runs with no rule on purpose, so a new player learns the base
  // game first; the server sends id 'none' for it rather than null so nothing
  // downstream has to null-check.
  const rule = game.roundRule && game.roundRule.id !== 'none' ? game.roundRule : null;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4">
      <ScoreStrip game={game} myId={myId} />

      {game.roundAnnouncement && <RoundAnnouncement announcement={game.roundAnnouncement} />}

      <div className="text-center text-sm text-gray-400">
        Round {round} · Question {questionInRound}/{QUESTIONS_PER_ROUND} (
        {game.questionIndex + 1}/{TOTAL_QUESTIONS} total)
      </div>

      {/* The rule stays on screen for the rest of the round — a rule you have
          to remember is one people forget mid-round and then feel cheated by.
          Hidden on the announcement turn itself, where the banner above is
          already saying the same words twice. */}
      {rule && !game.roundAnnouncement && (
        <div className="rounded-lg border border-game-gold/40 bg-game-gold/10 px-4 py-2 text-center">
          <span className="text-lg">{rule.emoji}</span>{' '}
          <span className="font-semibold text-game-gold">{rule.name}</span>
          <span className="ml-2 text-sm text-gray-300">{rule.description}</span>
        </div>
      )}

      <div className="rounded-lg bg-game-card p-4">
        {game.phase === 'CATEGORY' && <CategoryPicker game={game} myId={myId} socket={socket} />}
        {game.phase === 'WAGER' && <WagerPicker game={game} myId={myId} socket={socket} />}
        {game.phase === 'CARD' && <CardPhase game={game} myId={myId} socket={socket} />}
        {game.phase === 'QUESTION' && <p className="text-center">Generating question…</p>}
        {game.phase === 'ANSWER' && <AnswerPhase game={game} myId={myId} socket={socket} />}
        {game.phase === 'EVALUATING' && (
          <p className="text-center">🏆 The host is judging everyone's wrongness…</p>
        )}
        {game.phase === 'RESULT' && <ResultPhase game={game} />}
      </div>

      {game.phase === 'CARD' && <CardHand game={game} myId={myId} socket={socket} />}

      {/* The bank fills in behind the game (see gameState's fact-bank
          section). Surfaced quietly so a slow first question reads as
          "still warming up" rather than "broken" — never as a blocker. */}
      {game.factPrefetch?.active && (
        <p className="text-center text-xs text-gray-600">
          Warming up questions… {game.factPrefetch.completed}/{game.factPrefetch.total}
        </p>
      )}
    </div>
  );
}

// The puzzle itself. Deliberately enormous — the emoji ARE the question, so
// they get the size a question line would normally get, and the hint sits
// under them as the way in rather than as the main event.
function RebusPuzzle({ rebus }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-center gap-3">
        {rebus.pieces.map((emoji, i) => (
          <span key={i} className="flex items-center gap-3">
            {i > 0 && <span className="text-2xl text-gray-600">+</span>}
            <span className="text-5xl sm:text-6xl">{emoji}</span>
          </span>
        ))}
      </div>
      <p className="text-lg font-semibold">{rebus.hint}</p>
      {rebus.phonetic && (
        <p className="text-xs text-gray-500">Say the pictures out loud — this one sounds it out.</p>
      )}
    </div>
  );
}

// The reveal. Showing the decomposition is the whole payoff: without it a
// player who missed it never finds out WHY, which is the difference between
// a puzzle and a trick.
function RebusReveal({ rebus, answer }) {
  if (!rebus?.reads) return null;
  return (
    <div className="flex flex-wrap items-center justify-center gap-2 text-sm text-gray-300">
      {rebus.pieces.map((emoji, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && <span className="text-gray-600">+</span>}
          <span className="text-2xl">{emoji}</span>
          <span className="font-mono uppercase">{rebus.reads[i]}</span>
        </span>
      ))}
      <span className="text-gray-600">=</span>
      <span className="font-semibold text-white">{answer}</span>
    </div>
  );
}

// Shown for the first turn of each round. Round 1's banner says explicitly
// that there is no rule yet, so its absence reads as deliberate rather than
// as something failing to load.
function RoundAnnouncement({ announcement }) {
  const plain = announcement.ruleId === 'none';
  return (
    <div className="rounded-lg bg-game-accent/20 px-4 py-4 text-center">
      <p className="text-xs uppercase tracking-widest text-gray-400">Round {announcement.round}</p>
      {plain ? (
        <>
          <p className="mt-1 text-2xl font-bold">Straight trivia</p>
          <p className="mt-1 text-sm text-gray-300">
            No twist this round — get your bearings. Rules start next round.
          </p>
        </>
      ) : (
        <>
          <p className="mt-1 text-2xl font-bold">
            {announcement.emoji} {announcement.name}
          </p>
          <p className="mt-1 text-sm text-gray-300">{announcement.description}</p>
        </>
      )}
    </div>
  );
}

function ScoreStrip({ game, myId }) {
  return (
    <div className="flex flex-wrap gap-2">
      {game.players.map((p, i) => (
        <div
          key={p.id}
          className={`rounded px-3 py-1 text-sm ${
            i === game.activePlayerIndex ? 'bg-game-accent/40' : 'bg-game-card'
          }`}
        >
          {p.name}{p.id === myId && ' (you)'}: <span className="font-mono">{p.score}</span>
        </div>
      ))}
    </div>
  );
}

function WagerPicker({ game, myId, socket }) {
  const wagerPlayer = game.players[(game.activePlayerIndex + 1) % game.players.length];
  const [amount, setAmount] = useState(MIN_WAGER);

  if (wagerPlayer.id !== myId) {
    return <p className="text-center text-gray-300">{wagerPlayer.name} is setting the wager…</p>;
  }

  return (
    <div className="space-y-3 text-center">
      <h2 className="text-xl font-semibold">
        Set {game.players[game.activePlayerIndex].name}'s wager
      </h2>
      {game.roundRule.wagerMultiplier && (
        <p className="text-sm text-game-gold">
          {game.roundRule.name}: this wager will be doubled automatically!
        </p>
      )}
      <input
        type="range"
        min={MIN_WAGER}
        max={MAX_WAGER}
        step={10}
        value={amount}
        onChange={(e) => setAmount(Number(e.target.value))}
        className="w-full"
      />
      <p className="font-mono text-2xl">{amount}</p>
      <button
        className="rounded bg-game-accent px-6 py-2 font-semibold hover:opacity-90"
        onClick={() => socket.emit('turn:setWager', { amount })}
      >
        Confirm
      </button>
    </div>
  );
}

function CardPhase({ game }) {
  return (
    <div className="text-center">
      <p>
        Wager: <span className="font-mono">{game.currentWager}</span> · Category:{' '}
        <span className="font-semibold">{game.currentCategory}</span>
      </p>
      <p className="mt-2 text-sm text-gray-400">
        {game.cardSlot ? 'A card was played!' : 'Anyone may play a card now — first one wins.'}
      </p>
    </div>
  );
}

function AnswerPhase({ game, myId, socket }) {
  if (game.roundRule.submissionBased) {
    return <SubmissionAnswerPhase game={game} socket={socket} />;
  }
  if (game.roundRule.lineupBased) {
    return <LineupPhase game={game} socket={socket} />;
  }
  return <OpenAnswerPhase game={game} myId={myId} socket={socket} />;
}

// Flow B (GAME_DESIGN.md → "The Round Loop"). Three windows inside one
// phase: everyone reads, then the answerer has their own question to
// themselves, then the buzzer opens to the room.
//
// The two boundaries arrive as timestamps and are compared against the local
// clock on a 250ms tick — the server only pushes state when something
// changes, so a countdown derived server-side would freeze between pushes.
function OpenAnswerPhase({ game, myId, socket }) {
  const [answer, setAnswer] = useState('');
  const [inputMode, setInputMode] = useState('text');
  const [now, setNow] = useState(Date.now());
  const [actionError, setActionError] = useState(null);
  const autoLocked = useRef(false);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const answerer = game.players[game.answererIndex];
  const isAnswerer = game.iAmAnswerer ?? answerer.id === myId;
  const timer = game.roundRule.timerSeconds;
  const readingLeft = Math.max(0, Math.ceil(((game.answerOpensAt ?? 0) - now) / 1000));
  const exclusiveLeft = Math.max(0, Math.ceil(((game.buzzOpensAt ?? 0) - now) / 1000));
  const lockLeft = Math.max(0, Math.ceil(((game.lockClosesAt ?? 0) - now) / 1000));
  const reading = readingLeft > 0;
  const exclusive = !reading && exclusiveLeft > 0;
  const spent = game.spentAttempts ?? [];

  // The answerer types a live answer; everyone else types a commitment they
  // may never get to play. Same box, different verb — the server rejects
  // whichever one isn't yours, this only keeps it off screen.
  const canAnswer = !reading && isAnswerer && game.iCanAnswer;
  const canLock = !reading && lockLeft > 0 && game.iCanLock;
  const canBuzz = !reading && !exclusive && game.iCanBuzz;
  const canType = canAnswer || canLock;

  const submit = () => {
    if (!canAnswer || !answer.trim()) return;
    socket.emit('turn:submitAnswer', { answer, inputMode });
    setAnswer('');
  };

  const lockIn = (text = answer) => {
    if (!text.trim()) return;
    socket.emit('turn:lockAnswer', { answer: text, inputMode }, (res) => {
      if (res && res.ok === false) setActionError(res.message);
    });
  };

  // Nobody should lose a question to a missing button press. If there's text
  // in the box when locking is about to close, commit it — the deadline is
  // meant to stop late answers, not to punish someone who typed one in time
  // and didn't tap.
  useEffect(() => {
    if (autoLocked.current || !game.iCanLock || !answer.trim()) return;
    if (now < (game.lockClosesAt ?? 0) - 400) return;
    if (now >= (game.lockClosesAt ?? 0)) return;
    autoLocked.current = true;
    lockIn(answer);
  });

  const buzz = () => {
    socket.emit('turn:buzzIn', {}, (res) => {
      if (res && res.ok === false) setActionError(res.message);
    });
  };

  const pass = () => {
    socket.emit('turn:passAnswer', {}, (res) => {
      if (res && res.ok === false) setActionError(res.message);
    });
  };

  return (
    <div className="space-y-3 text-center">
      {game.heckleMessage && (
        <p className="italic text-game-pink">Heckle: "{game.heckleMessage}"</p>
      )}
      <p className="text-game-gold">{game.hostQuip}</p>

      {game.rebus ? (
        <RebusPuzzle rebus={game.rebus} />
      ) : (
        <p className="text-xl font-semibold leading-snug">{game.question}</p>
      )}

      <p className="text-sm text-gray-400">
        {answerer.name}&apos;s question · {game.currentWager} pts for {isAnswerer ? 'you' : 'them'}
        {' · '}
        {game.buzzPoints} for anyone else who takes it off {isAnswerer ? 'you' : 'them'}
      </p>

      {reading && (
        <p className="text-lg font-semibold text-game-blue">
          Read it… {isAnswerer ? 'your window opens' : 'answers open'} in {readingLeft}
        </p>
      )}

      {/* The room's view of the exclusive window. Said plainly, because a
          locked-out buzzer with no explanation reads as a bug. */}
      {exclusive && !isAnswerer && (
        <p className="text-lg font-semibold text-game-blue">
          {answerer.name}&apos;s shot — buzzers open in {exclusiveLeft}
        </p>
      )}

      {exclusive && isAnswerer && game.iCanPass && (
        <p className="text-lg font-semibold text-game-blue">
          Your question, your call — {exclusiveLeft}s before the room can take it
        </p>
      )}

      {canType && (
        <>
          {canLock && (
            <p className="text-sm text-gray-400">
              Lock an answer in now — {lockLeft}s. You can only buzz with one.
            </p>
          )}
          <div className="flex gap-2">
            <input
              autoFocus
              className="flex-1 rounded bg-game-dark px-3 py-2"
              placeholder={canLock ? 'Your answer, ready to go…' : 'Your answer…'}
              value={answer}
              onChange={(e) => {
                setAnswer(e.target.value);
                setInputMode('text');
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') canAnswer ? submit() : lockIn();
              }}
            />
            <VoiceInput
              onTranscript={(transcript) => {
                setAnswer(transcript);
                setInputMode('voice');
              }}
            />
            <button
              className="rounded bg-game-accent px-4 py-2 font-semibold"
              onClick={() => (canAnswer ? submit() : lockIn())}
            >
              {canAnswer ? 'Submit' : 'Lock It In'}
            </button>
          </div>

          {/* Folding is a real move — with a big wager on a category you don't
              know, handing it to the room is legitimate play, and it's the
              only way out of the wager that costs nothing. */}
          {canAnswer && exclusive && game.iCanPass && (
            <button
              className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:bg-game-dark"
              onClick={pass}
            >
              Pass — throw it to the room (costs you nothing)
            </button>
          )}

          <p className="text-xs text-gray-500">
            {canAnswer
              ? `One shot. Wrong or out of time costs you ${game.currentWager} — passing costs nothing.`
              : `A locked answer can't be changed, and you can't type one later. ${game.buzzPoints} pts if you buzz it in first.`}
          </p>
        </>
      )}

      {/* One tap, no typing. The decision was made when the answer was locked
          in; this is only about whether you dare play it first. */}
      {canBuzz && (
        <>
          <button
            className="w-full rounded bg-game-red px-4 py-6 text-2xl font-bold hover:opacity-90"
            onClick={buzz}
          >
            BUZZ — &ldquo;{game.myLockedAnswer}&rdquo;
          </button>
          <p className="text-xs text-gray-500">
            {timer}s on the clock. First correct buzz takes {game.buzzPoints}.
          </p>
        </>
      )}

      {actionError && <p className="text-sm text-game-red">{actionError}</p>}

      {!reading && !canType && !canBuzz && (
        <p className="text-gray-400">
          {game.myAttempt?.passed
            ? 'You passed — it belongs to the room now.'
            : game.myAttempt?.timedOut
            ? `Your window closed without an answer — that's ${game.currentWager} gone.`
            : game.myAttempt
            ? `You played "${game.myAttempt.answer}" — not it. Watch the others.`
            : game.myLockedAnswer
            ? `Locked in: "${game.myLockedAnswer}" — wait for the buzzer.`
            : exclusive
            ? 'Waiting…'
            : "You didn't lock one in — this one's out of your hands."}
        </p>
      )}

      {/* The count, never the answers. Watching "2 locked and ready" climb
          while the answerer sweats is most of the tension here. */}
      {game.lockedCount > 0 && (
        <p className="text-xs text-gray-500">{game.lockedCount} locked and ready</p>
      )}

      {spent.length > 0 && (
        <p className="text-xs text-gray-500">
          Done: {spent
            .map((a) => `${a.name}${a.passed ? ' (passed)' : a.timedOut ? ' (froze)' : ''}`)
            .join(', ')}
        </p>
      )}
    </div>
  );
}

// Worst Answer Wins (and future submission-based rules): every player
// submits their own answer to the same question instead of one active
// answerer. `game.mySubmitted`/`submittedCount`/`totalToSubmit` come from
// playerView() so the "waiting on N more" state survives reconnects.
function SubmissionAnswerPhase({ game, socket }) {
  const [answer, setAnswer] = useState('');
  const [inputMode, setInputMode] = useState('text');
  const timer = game.roundRule.timerSeconds;

  const submit = () => socket.emit('turn:submitAnswer', { answer, inputMode });
  const remaining = game.totalToSubmit - game.submittedCount;

  return (
    <div className="space-y-3 text-center">
      <p className="text-game-gold">{game.hostQuip}</p>
      <p className="text-lg font-semibold">{game.question}</p>
      <p className="text-sm text-gray-400">
        Wager: {game.currentWager} · {timer}s · Everyone submits an answer that's confidently wrong!
      </p>

      {game.mySubmitted ? (
        <p className="text-gray-400">
          Answer locked in! Waiting for {remaining} more player{remaining === 1 ? '' : 's'} ({game.submittedCount}/{game.totalToSubmit} in)…
        </p>
      ) : (
        <div className="flex gap-2">
          <input
            className="flex-1 rounded bg-game-dark px-3 py-2"
            placeholder="Your wonderfully wrong answer…"
            value={answer}
            onChange={(e) => {
              setAnswer(e.target.value);
              setInputMode('text');
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit();
            }}
          />
          <VoiceInput
            onTranscript={(transcript) => {
              setAnswer(transcript);
              setInputMode('voice');
            }}
          />
          <button className="rounded bg-game-accent px-4 py-2 font-semibold" onClick={submit}>
            Lock In
          </button>
        </div>
      )}
    </div>
  );
}

// The Lineup: anyone may tap any option, any number of times, until someone
// gets it right or the timer runs out. Wrong taps get a brief red flash via
// the ack callback (server doesn't broadcast on a wrong guess — see
// server.js) rather than a real error, since being wrong here is the
// expected common case, not a failure.
function LineupPhase({ game, socket }) {
  const [wrongId, setWrongId] = useState(null);
  const timer = game.roundRule.timerSeconds;
  const isColor = game.lineup?.flavor === 'color';

  const pick = (optionId) => {
    socket.emit('turn:attemptLineup', { optionId }, (res) => {
      if (res && res.correct === false) {
        setWrongId(optionId);
        setTimeout(() => setWrongId((cur) => (cur === optionId ? null : cur)), 500);
      }
    });
  };

  return (
    <div className="space-y-3 text-center">
      <p className="text-game-gold">{game.hostQuip}</p>
      <p className="text-lg font-semibold">{game.question}</p>
      <p className="text-sm text-gray-400">
        Wager: {game.currentWager} · {timer}s · Anyone can tap — first correct pick wins!
      </p>

      <div className="space-y-2">
        {game.lineup?.options.map((opt, i) => (
          <button
            key={opt.id}
            onClick={() => pick(opt.id)}
            className={`flex w-full items-center gap-3 rounded px-3 py-2 text-left transition ${
              wrongId === opt.id ? 'ring-2 ring-game-red' : ''
            } ${isColor ? 'hover:opacity-80' : 'bg-game-dark font-semibold hover:bg-game-accent/40'}`}
          >
            <span className="font-mono text-sm text-gray-400">{i + 1}.</span>
            {isColor ? (
              <span className="h-10 flex-1 rounded" style={{ backgroundColor: opt.hex }} />
            ) : (
              <span>{opt.label}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function ResultPhase({ game }) {
  if (game.skippedTurn) {
    return <p className="text-center text-xl">Turn skipped!</p>;
  }
  const result = game.lastResult;

  if (result.submissionBased) {
    return <WorstAnswerResults game={game} result={result} />;
  }

  if (result.lineupWinner !== undefined) {
    return <LineupResults game={game} result={result} />;
  }

  const answerer = game.players[game.answererIndex];
  const answererName = answerer?.name ?? 'the answerer';
  // A fold and a freeze both end with the answerer not answering, but only
  // one of them costs the wager — so the headline must not report them the
  // same way. `wagerLost` is the server's own record of which happened.
  const headline = result.buzzedIn
    ? `${result.winnerName} buzzed in and took it! +${result.points}`
    : result.correct
    ? `${result.winnerName ?? 'Correct'}! +${result.points}`
    : result.wagerLost
    ? `Nobody got it — ${answererName} drops ${result.wager}`
    : result.activeOutcome === 'passed'
    ? `${answererName} passed — and nobody else got it either`
    : 'Nobody got it.';

  // Only alongside a buzz-in win: otherwise the headline has already said it,
  // and saying it twice reads as a bug rather than as emphasis.
  const asideForActive = !result.buzzedIn
    ? null
    : result.activeOutcome === 'passed'
      ? `${answererName} passed on ${result.wager} — it cost them nothing.`
      : result.activeOutcome === 'timedOut'
      ? `${answererName} never answered — ${result.wager} gone.`
      : null;

  // Every attempt, so the room sees who swung and missed — that's the part
  // people talk about, and it's invisible if only the winner is shown.
  const misses = (result.attempts ?? []).filter((a) => !a.correct && a.answer);

  return (
    <div className="space-y-2 text-center">
      <p className={`text-2xl font-bold ${result.correct ? 'text-game-green' : 'text-game-red'}`}>
        {headline}
      </p>
      {asideForActive && <p className="text-sm text-gray-400">{asideForActive}</p>}
      {game.rebus ? (
        <RebusReveal rebus={game.rebus} answer={game.answer} />
      ) : (
        <p className="text-sm text-gray-400">Correct answer: {game.answer}</p>
      )}
      {result.feedback && <p>{result.feedback}</p>}
      {misses.length > 0 && (
        <div className="pt-2 text-sm text-gray-400">
          {misses.map((a) => (
            <p key={a.playerId}>
              <span className="text-gray-300">{a.name}</span> played &ldquo;{a.answer}&rdquo;
            </p>
          ))}
        </div>
      )}

      {/* The answers nobody got to play. This is the loudest moment the
          lock-in mechanic produces — somebody in the room had it and sat on
          it, and only the reveal tells them so. */}
      {(result.unplayedAnswers ?? []).length > 0 && (
        <div className="pt-2 text-sm text-gray-500">
          <p className="text-xs uppercase tracking-widest">Never played</p>
          {result.unplayedAnswers.map((a) => (
            <p key={a.playerId}>
              <span className="text-gray-300">{a.name}</span> had &ldquo;{a.answer}&rdquo;
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// The Lineup result: either someone spotted it first, or the timer ran out
// unclaimed. Reveals the correct option (swatch for color flavor, label for
// text) alongside the rest of the lineup.
function LineupResults({ game, result }) {
  return (
    <div className="space-y-3 text-center">
      {result.lineupWinner ? (
        <p className="text-2xl font-bold text-game-green">
          {result.winnerName} spotted it! +{result.wager}
        </p>
      ) : (
        <p className="text-2xl font-bold text-game-red">
          Nobody spotted it — {result.wager} pts unclaimed!
        </p>
      )}
      <p className="text-sm text-gray-400">Correct answer: {game.answer}</p>

      <div className="space-y-2">
        {game.lineup?.options.map((opt, i) => {
          const isCorrect = opt.id === result.correctOptionId;
          return (
            <div
              key={opt.id}
              className={`flex items-center gap-3 rounded px-3 py-2 ${
                isCorrect ? 'ring-2 ring-game-gold' : 'bg-game-dark'
              }`}
            >
              <span className="font-mono text-sm text-gray-400">{i + 1}.</span>
              {opt.hex ? (
                <span className="h-10 flex-1 rounded" style={{ backgroundColor: opt.hex }} />
              ) : (
                <span className="flex-1 text-left">{opt.label}</span>
              )}
              {isCorrect && <span className="text-game-gold">✓</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Worst Answer Wins result: transparent, per-player, per-axis breakdown --
// not just who won, but the exact scores the host judged them on. Sorted by
// total ascending (lowest/best first), winner(s) highlighted.
function WorstAnswerResults({ game, result }) {
  const sorted = [...result.entries].sort((a, b) => a.total - b.total);
  const winners = sorted.filter((e) => e.isWinner).map((e) => e.name).join(' & ');

  return (
    <div className="space-y-3 text-center">
      <p className="text-2xl font-bold text-game-gold">
        {winners} nailed it! +{result.wager}
      </p>
      <p className="text-sm text-gray-400">
        Correct answer: {game.answer} · lowest total score wins
      </p>

      <div className="space-y-2 text-left">
        {sorted.map((entry) => (
          <div
            key={entry.playerId}
            className={`rounded p-3 ${
              entry.isWinner ? 'border border-game-gold bg-game-gold/10' : 'bg-game-dark'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold">
                {entry.name}
                {entry.isWinner && ' 🏆'}
              </span>
              <span className="font-mono text-sm text-gray-400">Total: {entry.total}/30</span>
            </div>
            <p className="mt-1 italic text-sm text-gray-300">"{entry.answer || '(no answer submitted)'}"</p>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
              <span>Factually wrong: {entry.factuallyWrong}/10</span>
              <span>Creatively wrong: {entry.creativelyWrong}/10</span>
              <span>Plausibility: {entry.plausibility}/10</span>
            </div>
            <p className="mt-2 text-sm">{entry.feedback}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
