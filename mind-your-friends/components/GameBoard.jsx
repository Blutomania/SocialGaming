'use client';

import { useState } from 'react';
import CategoryPicker from './CategoryPicker';
import CardHand from './CardHand';
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
  const answerer = game.players[game.answererIndex];
  const isAnswerer = answerer.id === myId;
  const [answer, setAnswer] = useState('');
  const timer = game.timerSecondsOverride ?? game.roundRule.timerSeconds;

  return (
    <div className="space-y-3 text-center">
      {game.heckleMessage && (
        <p className="italic text-game-pink">Heckle: "{game.heckleMessage}"</p>
      )}
      <p className="text-game-gold">{game.currentQuestion.hostQuip}</p>
      <p className="text-lg font-semibold">{game.currentQuestion.question}</p>
      <p className="text-sm text-gray-400">
        Wager: {game.currentWager} · {timer}s · {answerer.name} answers
      </p>

      {isAnswerer ? (
        <div className="flex gap-2">
          <input
            className="flex-1 rounded bg-game-dark px-3 py-2"
            placeholder="Your answer…"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                socket.emit('turn:submitAnswer', { answer, inputMode: 'text' });
              }
            }}
          />
          <button
            className="rounded bg-game-accent px-4 py-2 font-semibold"
            onClick={() => socket.emit('turn:submitAnswer', { answer, inputMode: 'text' })}
          >
            Submit
          </button>
        </div>
      ) : (
        <p className="text-gray-400">Waiting for {answerer.name} to answer…</p>
      )}
    </div>
  );
}

function ResultPhase({ game }) {
  if (game.skippedTurn) {
    return <p className="text-center text-xl">Turn skipped!</p>;
  }
  const result = game.lastResult;
  return (
    <div className="space-y-2 text-center">
      <p className={`text-2xl font-bold ${result.correct ? 'text-game-green' : 'text-game-red'}`}>
        {result.correct ? `Correct! +${result.wager}` : `Wrong! -${result.wager}`}
      </p>
      <p className="text-sm text-gray-400">
        Correct answer: {game.currentQuestion.answer}
      </p>
      <p>{result.feedback}</p>
    </div>
  );
}
