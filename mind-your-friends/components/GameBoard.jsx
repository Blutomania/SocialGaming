'use client';

import { useState } from 'react';
import CategoryPicker from './CategoryPicker';
import CardHand from './CardHand';
import VoiceInput from './VoiceInput';
import { MIN_WAGER, MAX_WAGER, TOTAL_QUESTIONS, QUESTIONS_PER_ROUND } from '../lib/constants';

export default function GameBoard({ game, myId, socket }) {
  const round = Math.floor(game.questionIndex / QUESTIONS_PER_ROUND) + 1;
  const questionInRound = (game.questionIndex % QUESTIONS_PER_ROUND) + 1;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <ScoreStrip game={game} myId={myId} />

      <div className="text-center text-sm text-gray-400">
        Round {round} · Question {questionInRound}/{QUESTIONS_PER_ROUND} (
        {game.questionIndex + 1}/{TOTAL_QUESTIONS} total)
        {game.roundRule && (
          <span className="ml-2">
            {game.roundRule.emoji} {game.roundRule.name}
          </span>
        )}
      </div>

      <div className="rounded-lg bg-game-card p-4">
        {game.phase === 'CATEGORY' && <CategoryPicker game={game} myId={myId} socket={socket} />}
        {game.phase === 'WAGER' && <WagerPicker game={game} myId={myId} socket={socket} />}
        {game.phase === 'CARD' && <CardPhase game={game} myId={myId} socket={socket} />}
        {game.phase === 'QUESTION' && <p className="text-center">Generating question…</p>}
        {game.phase === 'ANSWER' && <AnswerPhase game={game} myId={myId} socket={socket} />}
        {game.phase === 'EVALUATING' && (
          <p className="text-center">🏆 The host is judging everyone's wrongness…</p>
        )}
        {game.phase === 'STEAL' && <StealPhase game={game} socket={socket} />}
        {game.phase === 'RESULT' && <ResultPhase game={game} />}
      </div>

      {game.phase === 'CARD' && <CardHand game={game} myId={myId} socket={socket} />}
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

  const answerer = game.players[game.answererIndex];
  const isAnswerer = answerer.id === myId;
  const [answer, setAnswer] = useState('');
  const [inputMode, setInputMode] = useState('text');
  const timer = game.timerSecondsOverride ?? game.roundRule.timerSeconds;

  const submit = () => socket.emit('turn:submitAnswer', { answer, inputMode });

  return (
    <div className="space-y-3 text-center">
      {game.heckleMessage && (
        <p className="italic text-game-pink">Heckle: "{game.heckleMessage}"</p>
      )}
      <p className="text-game-gold">{game.hostQuip}</p>
      <p className="text-lg font-semibold">{game.question}</p>
      <p className="text-sm text-gray-400">
        Wager: {game.currentWager} · {timer}s · {answerer.name} answers
      </p>

      {isAnswerer ? (
        <div className="flex gap-2">
          <input
            className="flex-1 rounded bg-game-dark px-3 py-2"
            placeholder="Your answer…"
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
            Submit
          </button>
        </div>
      ) : (
        <p className="text-gray-400">Waiting for {answerer.name} to answer…</p>
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
  const timer = game.timerSecondsOverride ?? game.roundRule.timerSeconds;

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

function StealPhase({ game, socket }) {
  const [answer, setAnswer] = useState('');
  const [inputMode, setInputMode] = useState('text');

  const submit = () => socket.emit('turn:claimSteal', { answer, inputMode });

  if (game.stealClaimed) {
    return <p className="text-center text-gray-300">Steal claimed — evaluating…</p>;
  }

  if (!game.stealEligible) {
    return (
      <p className="text-center text-gray-300">
        Wrong answer! Waiting to see if anyone steals the wager…
      </p>
    );
  }

  return (
    <div className="space-y-3 text-center">
      <p className="font-semibold text-game-red">Wrong answer! Buzz in to steal the wager.</p>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded bg-game-dark px-3 py-2"
          placeholder="Your steal answer…"
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
        <button className="rounded bg-game-red px-4 py-2 font-semibold" onClick={submit}>
          Steal!
        </button>
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

  const halfWager = Math.round(result.wager / 2);
  const headline = result.stolen
    ? result.correct
      ? `${result.stealerName} stole it! +${result.wager}`
      : `${result.stealerName}'s steal missed! -${halfWager}`
    : result.correct
    ? `Correct! +${result.wager}`
    : `Wrong! -${result.wager}`;

  return (
    <div className="space-y-2 text-center">
      <p className={`text-2xl font-bold ${result.correct ? 'text-game-green' : 'text-game-red'}`}>
        {headline}
      </p>
      <p className="text-sm text-gray-400">
        Correct answer: {game.answer}
      </p>
      <p>{result.feedback}</p>
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
