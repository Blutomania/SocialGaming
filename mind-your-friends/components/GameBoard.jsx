'use client';

import { useState } from 'react';
import CategoryPicker from './CategoryPicker';
import WagerModal from './WagerModal';
import CardHand from './CardHand';
import QuestionCard from './QuestionCard';

const PHASES = {
  LOBBY: 'lobby',
  CATEGORY: 'category',
  WAGER: 'wager',
  CARD: 'card',
  QUESTION: 'question',
  ANSWER: 'answer',
  RESULT: 'result',
  GAME_OVER: 'game_over',
};

export default function GameBoard({
  gameState,
  socketId,
  emit,
  code,
  lastResult,
  questionReady,
  timerSeconds,
}) {
  const [cardError, setCardError] = useState('');

  const currentPlayer = gameState.players[gameState.currentPlayerIndex];
  const isActivePlayer =
    (gameState.effects?.redirectedTo
      ? gameState.effects.redirectedTo === socketId
      : currentPlayer?.id === socketId);

  const nextPlayerIndex =
    (gameState.currentPlayerIndex + 1) % gameState.players.length;
  const nextPlayer = gameState.players.find(
    (_, i) => i === nextPlayerIndex && gameState.players[nextPlayerIndex]?.connected
  ) || gameState.players.find((p) => p.connected && p.id !== currentPlayer?.id);

  const isWagerer = nextPlayer?.id === socketId;

  function playCard(targetPlayerId) {
    setCardError('');
    emit('turn:playCard', { code, targetPlayerId }, (res) => {
      if (res?.error) setCardError(res.error);
    });
  }

  function skipCard() {
    emit('turn:skipCard', { code }, (res) => {
      if (res?.error) setCardError(res.error);
    });
  }

  const { phase } = gameState;

  return (
    <div className="min-h-screen flex flex-col p-4 max-w-4xl mx-auto w-full">
      {/* Top bar: round info + scores */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="bg-game-accent text-white text-sm font-bold px-3 py-1 rounded-full">
            Round {gameState.roundNumber}/{gameState.maxRounds}
          </span>
          {gameState.roundRule && (
            <span className="bg-game-card border border-gray-700 text-gray-300 text-sm px-3 py-1 rounded-full">
              {gameState.roundRule.emoji} {gameState.roundRule.name}
            </span>
          )}
        </div>
        {/* Score strip */}
        <div className="flex gap-2 flex-wrap">
          {gameState.players
            .filter((p) => p.connected)
            .sort((a, b) => (gameState.scores[b.id] || 0) - (gameState.scores[a.id] || 0))
            .map((p) => (
              <div
                key={p.id}
                className={`text-xs px-2 py-1 rounded-lg font-mono ${
                  p.id === socketId
                    ? 'bg-game-accent text-white'
                    : 'bg-game-card text-gray-300 border border-gray-700'
                }`}
              >
                {p.name}: {gameState.scores[p.id] ?? 1000}
              </div>
            ))}
        </div>
      </div>

      {/* Round rule description */}
      {gameState.roundRule && (
        <div className="bg-game-card border border-gray-700 rounded-xl px-4 py-2 mb-4 text-sm text-gray-400">
          <strong className="text-white">{gameState.roundRule.emoji} Rule: </strong>
          {gameState.roundRule.description}
        </div>
      )}

      {/* Active player banner */}
      <div className="text-center mb-4">
        {isActivePlayer ? (
          <p className="text-game-gold font-bold text-lg animate-pulse-slow">
            It&apos;s your turn!
          </p>
        ) : (
          <p className="text-gray-400 text-lg">
            {gameState.effects?.redirectedTo
              ? `${gameState.players.find((p) => p.id === gameState.effects.redirectedTo)?.name} is answering (redirected)`
              : `${currentPlayer?.name}'s turn`}
          </p>
        )}
        {gameState.selectedCategory && (
          <p className="text-gray-500 text-sm mt-1">Category: <strong className="text-white">{gameState.selectedCategory}</strong></p>
        )}
      </div>

      {/* Phase-specific UI */}
      <div className="flex-1">
        {/* CATEGORY PHASE */}
        {phase === PHASES.CATEGORY && (
          <>
            {isActivePlayer ? (
              <CategoryPicker
                onSelect={(cat) => emit('turn:selectCategory', { code, category: cat })}
              />
            ) : (
              <div className="text-center text-gray-400 mt-16 text-xl animate-pulse">
                {currentPlayer?.name} is picking a category...
              </div>
            )}
          </>
        )}

        {/* WAGER PHASE */}
        {phase === PHASES.WAGER && (
          <>
            {isWagerer ? (
              <WagerModal
                category={gameState.selectedCategory}
                onSetWager={(w) => emit('turn:setWager', { code, wager: w })}
              />
            ) : (
              <div className="text-center text-gray-400 mt-16 text-xl animate-pulse">
                {nextPlayer?.name || 'Someone'} is setting the wager...
              </div>
            )}
          </>
        )}

        {/* CARD PHASE */}
        {phase === PHASES.CARD && (
          <div className="space-y-4">
            <div className="text-center mb-2">
              <p className="text-gray-300 text-lg">
                Wager: <strong className="text-game-gold text-2xl">{gameState.wager} pts</strong>
              </p>
              <p className="text-gray-500 text-sm">Everyone can play a card now, or pass.</p>
            </div>

            <CardHand
              cardId={gameState.myCard}
              players={gameState.players}
              socketId={socketId}
              onPlay={playCard}
              onSkip={skipCard}
              isActivePlayer={isActivePlayer}
              alreadyPlayed={gameState.cardsPlayedThisRound?.some((c) => c.playerId === socketId)}
              phase={phase}
            />

            {cardError && <p className="text-game-red text-center text-sm">{cardError}</p>}

            {/* Cards played this round */}
            {gameState.cardsPlayedThisRound?.length > 0 && (
              <div className="bg-game-card rounded-xl p-3 border border-gray-700">
                <p className="text-gray-400 text-xs uppercase tracking-widest mb-2">Cards Played</p>
                <div className="flex flex-wrap gap-2">
                  {gameState.cardsPlayedThisRound.map((c, i) => {
                    const player = gameState.players.find((p) => p.id === c.playerId);
                    return (
                      <span key={i} className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded-lg">
                        {player?.name}: {c.cardId.replace(/_/g, ' ')}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Active player can finalize the card phase */}
            {isActivePlayer && (
              <button
                onClick={skipCard}
                className="w-full py-3 bg-game-accent rounded-xl text-white font-bold hover:bg-violet-500 transition"
              >
                Proceed to Question →
              </button>
            )}
          </div>
        )}

        {/* QUESTION PHASE — generating */}
        {phase === PHASES.QUESTION && (
          <div className="flex flex-col items-center justify-center h-48 gap-4">
            <div className="w-10 h-10 border-4 border-game-accent border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-400 text-lg animate-pulse">Generating your question...</p>
          </div>
        )}

        {/* ANSWER PHASE */}
        {phase === PHASES.ANSWER && gameState.currentQuestion && (
          <QuestionCard
            question={gameState.currentQuestion}
            roundRule={gameState.roundRule}
            isActivePlayer={isActivePlayer}
            timerSeconds={timerSeconds}
            onSubmit={(answer) => emit('turn:submitAnswer', { code, answer })}
            onHint={() => {}} // hint is in the question object already
            myCard={gameState.myCard}
            onPlayCard={playCard}
            onSkipCard={skipCard}
            alreadyPlayedCard={gameState.cardsPlayedThisRound?.some((c) => c.playerId === socketId)}
            players={gameState.players}
            socketId={socketId}
          />
        )}

        {/* RESULT PHASE */}
        {phase === PHASES.RESULT && lastResult && (
          <div className="flex flex-col items-center justify-center gap-6 mt-8">
            <div
              className={`text-8xl ${lastResult.isCorrect ? 'animate-bounce' : ''}`}
            >
              {lastResult.isCorrect ? '✅' : '❌'}
            </div>
            <div className="text-center">
              <p className={`text-4xl font-display ${lastResult.isCorrect ? 'text-game-green' : 'text-game-red'}`}>
                {lastResult.isCorrect ? 'CORRECT!' : 'WRONG!'}
              </p>
              <p className="text-gray-400 mt-2">{lastResult.explanation}</p>
              {lastResult.correctAnswer && !lastResult.isCorrect && (
                <p className="text-gray-300 mt-2">
                  Answer was: <strong className="text-game-gold">{lastResult.correctAnswer}</strong>
                </p>
              )}
              <p className={`text-2xl font-bold mt-3 ${lastResult.pointDelta >= 0 ? 'text-game-green' : 'text-game-red'}`}>
                {lastResult.pointDelta >= 0 ? '+' : ''}{lastResult.pointDelta} pts
              </p>
            </div>
            <p className="text-gray-500 text-sm animate-pulse">Next turn in a moment...</p>
          </div>
        )}
      </div>

      {/* Effects strip */}
      {gameState.effects && (
        <div className="flex gap-2 flex-wrap mt-4">
          {gameState.effects.safetyNet && (
            <span className="bg-game-green/20 text-game-green text-xs px-2 py-1 rounded-lg border border-game-green/30">
              🛡️ Safety Net Active
            </span>
          )}
          {gameState.effects.pinchPenny && (
            <span className="bg-game-red/20 text-game-red text-xs px-2 py-1 rounded-lg border border-game-red/30">
              💰 Pinch Penny Active
            </span>
          )}
          {gameState.effects.halftime && (
            <span className="bg-yellow-500/20 text-yellow-400 text-xs px-2 py-1 rounded-lg border border-yellow-500/30">
              ⏱️ Halftime Timer
            </span>
          )}
          {gameState.effects.redirectedTo && (
            <span className="bg-game-blue/20 text-game-blue text-xs px-2 py-1 rounded-lg border border-game-blue/30">
              ↩️ Question Redirected
            </span>
          )}
        </div>
      )}
    </div>
  );
}
