/**
 * Mind Your Friends — Custom Next.js + Socket.io server
 * Run with: node server.js
 */

import { createServer } from 'http';
import { parse } from 'url';
import next from 'next';
import { Server } from 'socket.io';
import fs from 'fs';

// ─── Game state imports ───────────────────────────────────────────────────────
import {
  createGame,
  joinGame,
  removePlayer,
  getGame,
  getGameBySocketId,
  setHostPersonality,
  startGame,
  selectCategory,
  setWager,
  playCard,
  skipCard,
  setCurrentQuestion,
  submitAnswer,
  advanceTurn,
  startTimer,
  clearTimer,
  sanitizeForClient,
  getCurrentPlayer,
  PHASES,
} from './lib/gameState.js';

import { generateQuestion, evaluateAnswer } from './lib/claudeClient.js';
import { ROUND_RULES, transformAnswer } from './lib/roundRules.js';

// ─── Bootstrap ───────────────────────────────────────────────────────────────
const dev = process.env.NODE_ENV !== 'production';
const port = parseInt(process.env.PORT || '3000', 10);
const app = next({ dev });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const httpServer = createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  });

  const io = new Server(httpServer, {
    cors: { origin: '*' },
  });

  // ─── Helpers ───────────────────────────────────────────────────────────────

  // Memorable moments log per game code — drives the end-game Highlight Reel
  const momentLogs = new Map(); // code → [{emoji, text}]

  function logMoment(code, emoji, text) {
    if (!momentLogs.has(code)) momentLogs.set(code, []);
    momentLogs.get(code).push({ emoji, text });
  }

  function broadcast(code, event, data) {
    io.to(code).emit(event, data);
  }

  function broadcastState(game) {
    for (const player of game.players) {
      const socket = io.sockets.sockets.get(player.id);
      if (socket) {
        socket.emit('game:state', sanitizeForClient(game, player.id));
      }
    }
  }

  async function triggerQuestionGeneration(game) {
    const rule = game.roundRule;
    const ruleData = ROUND_RULES[rule.id];

    const activePlayer = getCurrentPlayer(game);
    const playerNames = game.players.filter((p) => p.connected).map((p) => p.name);

    try {
      const result = await generateQuestion({
        category: game.selectedCategory,
        roundRule: rule.id,
        roundRuleName: rule.name,
        roundRuleInstruction: ruleData.promptInstruction,
        hostPersonality: game.hostPersonality,
        previousQuestions: game.previousQuestions,
        activePlayerName: activePlayer?.name || '',
        playerNames,
      });

      // Apply "Infamous Last Words" transform — omit last word from question text
      let questionText = result.question;
      if (rule.id === 'INFAMOUS_LAST_WORDS') {
        const words = questionText.trim().split(/\s+/);
        if (words.length > 1) {
          words.pop();
          questionText = words.join(' ') + ' ___?';
        }
      }

      const updatedGame = setCurrentQuestion(game.code, {
        ...result,
        question: questionText,
      });

      broadcastState(updatedGame);
      broadcast(updatedGame.code, 'question:ready', {
        question: questionText,
        hostQuip: result.hostQuip,
        roundRule: rule,
      });

      // Start answer timer
      startTimer(
        updatedGame,
        (secondsLeft) => {
          broadcast(updatedGame.code, 'timer:tick', { secondsLeft });
        },
        () => {
          // Time's up — auto-evaluate as wrong
          handleTimeUp(updatedGame.code);
        }
      );
    } catch (err) {
      console.error('Question generation failed:', err);
      broadcast(game.code, 'error', { message: 'Failed to generate question. Skipping turn.' });
      const updated = advanceTurn(game.code);
      if (updated) broadcastState(updated);
    }
  }

  async function handleTimeUp(code) {
    const game = getGame(code);
    if (!game || game.phase !== PHASES.ANSWER) return;

    const result = submitAnswer(code, getCurrentPlayer(game).id, false, "Time's up!");
    if (result.error) return;

    broadcastState(result.game);
    broadcast(code, 'turn:result', {
      isCorrect: false,
      explanation: "Time's up!",
      pointDelta: result.pointDelta,
      correctAnswer: game.currentQuestion?.correctAnswer,
    });

    // Auto-advance after 4 seconds
    setTimeout(() => {
      const g = getGame(code);
      if (!g || g.phase !== PHASES.RESULT) return;
      const updated = advanceTurn(code);
      if (!updated) return;
      broadcastState(updated);
      if (updated.phase === PHASES.GAME_OVER) {
        broadcast(code, 'game:over', {
          scores: updated.scores,
          players: updated.players,
          moments: momentLogs.get(code) || [],
        });
        momentLogs.delete(code);
      } else {
        broadcast(code, 'round:new', {
          roundNumber: updated.roundNumber,
          roundRule: updated.roundRule,
        });
      }
    }, 4000);
  }

  // ─── Socket.io event handlers ──────────────────────────────────────────────

  io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);

    // ── Lobby ──────────────────────────────────────────────────────────────

    socket.on('lobby:create', ({ playerName }, cb) => {
      if (!playerName?.trim()) return cb?.({ error: 'Name required.' });
      const code = createGame(socket.id, playerName.trim());
      socket.join(code);
      const game = getGame(code);
      cb?.({ code, game: sanitizeForClient(game, socket.id) });
    });

    socket.on('lobby:join', ({ code, playerName }, cb) => {
      if (!code || !playerName?.trim()) return cb?.({ error: 'Code and name required.' });
      const result = joinGame(code.toUpperCase(), socket.id, playerName.trim());
      if (result.error) return cb?.({ error: result.error });
      socket.join(code.toUpperCase());
      broadcastState(result.game);
      cb?.({ game: sanitizeForClient(result.game, socket.id) });
    });

    socket.on('lobby:setPersonality', ({ code, personality }) => {
      const game = setHostPersonality(code, personality);
      if (game) broadcastState(game);
    });

    // ── Game start ─────────────────────────────────────────────────────────

    socket.on('game:start', ({ code }, cb) => {
      const game = getGame(code);
      if (!game) return cb?.({ error: 'Game not found.' });
      if (game.hostId !== socket.id) return cb?.({ error: 'Only the host can start.' });

      const result = startGame(code);
      if (result?.error) return cb?.({ error: result.error });

      broadcastState(result);
      broadcast(code, 'game:started', { roundNumber: result.roundNumber, roundRule: result.roundRule });
      cb?.({ ok: true });
    });

    // ── Category selection ─────────────────────────────────────────────────

    socket.on('turn:selectCategory', ({ code, category }, cb) => {
      const result = selectCategory(code, socket.id, category);
      if (result.error) return cb?.({ error: result.error });
      broadcastState(result.game);
      broadcast(code, 'turn:new', { phase: PHASES.WAGER, category });
      cb?.({ ok: true });
    });

    // ── Wager ──────────────────────────────────────────────────────────────

    socket.on('turn:setWager', ({ code, wager }, cb) => {
      const result = setWager(code, socket.id, parseInt(wager, 10) || 100);
      if (result.error) return cb?.({ error: result.error });
      broadcastState(result.game);
      broadcast(code, 'turn:new', { phase: PHASES.CARD, wager: result.game.wager });
      cb?.({ ok: true });
    });

    // ── Card play / skip ───────────────────────────────────────────────────

    socket.on('turn:playCard', ({ code, targetPlayerId }, cb) => {
      const result = playCard(code, socket.id, targetPlayerId);
      if (result.error) return cb?.({ error: result.error });

      broadcastState(result.game);
      broadcast(code, 'card:played', {
        playerId: socket.id,
        cardId: result.cardId,
        targetPlayerId,
        effects: result.game.effects,
        wager: result.game.wager,
      });

      // Track sabotage cards as memorable moments
      const sabotageMoment = {
        MUTED: { emoji: '🔇', verb: 'silenced' },
        REDIRECT: { emoji: '↩️', verb: 'redirected the question onto' },
        PINCH_PENNY: { emoji: '💸', verb: 'pinched' },
      }[result.cardId];
      if (sabotageMoment && targetPlayerId) {
        const player = result.game.players.find((p) => p.id === socket.id);
        const target = result.game.players.find((p) => p.id === targetPlayerId);
        if (player && target) {
          logMoment(code, sabotageMoment.emoji, `${player.name} ${sabotageMoment.verb} ${target.name}`);
        }
      }
      cb?.({ ok: true });
    });

    socket.on('turn:skipCard', ({ code }, cb) => {
      const result = skipCard(code, socket.id);
      if (result.error) return cb?.({ error: result.error });

      // Move to question phase and generate
      broadcastState(result.game);
      broadcast(code, 'turn:new', { phase: PHASES.QUESTION });

      // Generate question asynchronously
      triggerQuestionGeneration(result.game);
      cb?.({ ok: true });
    });

    // If WHOA_NELLIE was played and question needs regenerating
    socket.on('turn:requestNewQuestion', ({ code }, cb) => {
      const game = getGame(code);
      if (!game) return cb?.({ error: 'Game not found.' });
      if (!game.effects.newQuestion) return cb?.({ error: 'No new question requested.' });
      game.effects.newQuestion = false;
      triggerQuestionGeneration(game);
      cb?.({ ok: true });
    });

    // ── Answer submission ──────────────────────────────────────────────────

    socket.on('turn:submitAnswer', async ({ code, answer }, cb) => {
      const game = getGame(code);
      if (!game || game.phase !== PHASES.ANSWER) return cb?.({ error: 'Wrong phase.' });

      clearTimer(game);

      const answeringPlayerId = game.effects.redirectedTo || getCurrentPlayer(game).id;
      if (socket.id !== answeringPlayerId) return cb?.({ error: 'Not your turn.' });

      if (!game.currentQuestion) return cb?.({ error: 'No question active.' });

      // Apply round rule transform (e.g., BACK_IT_UP reverses the answer)
      const transformedAnswer = transformAnswer(answer, game.roundRule?.id);

      let evalResult;
      try {
        evalResult = await evaluateAnswer(
          transformedAnswer,
          game.currentQuestion.correctAnswer,
          game.currentQuestion.question
        );
      } catch (err) {
        console.error('Answer evaluation failed:', err);
        evalResult = { correct: false, explanation: 'Could not evaluate answer.' };
      }

      const result = submitAnswer(code, socket.id, evalResult.correct, evalResult.explanation);
      if (result.error) return cb?.({ error: result.error });

      broadcastState(result.game);

      // Log memorable wrong answers
      if (!evalResult.correct) {
        const ansPlayer = result.game.players.find((p) => p.id === socket.id);
        if (ansPlayer) {
          logMoment(code, '😬', `${ansPlayer.name} said "${answer}" (answer: ${game.currentQuestion.correctAnswer})`);
        }
      }

      broadcast(code, 'turn:result', {
        isCorrect: evalResult.correct,
        explanation: evalResult.explanation,
        pointDelta: result.pointDelta,
        correctAnswer: game.currentQuestion.correctAnswer,
        answeredBy: socket.id,
      });
      cb?.({ ok: true, isCorrect: evalResult.correct });

      // Auto-advance after 4 seconds
      setTimeout(() => {
        const g = getGame(code);
        if (!g || g.phase !== PHASES.RESULT) return;
        const updated = advanceTurn(code);
        if (!updated) return;
        broadcastState(updated);
        if (updated.phase === PHASES.GAME_OVER) {
          broadcast(code, 'game:over', {
            scores: updated.scores,
            players: updated.players,
            moments: momentLogs.get(code) || [],
          });
          momentLogs.delete(code);
        } else {
          broadcast(code, 'round:new', {
            roundNumber: updated.roundNumber,
            roundRule: updated.roundRule,
          });
        }
      }, 4000);
    });

    // ── Disconnect ─────────────────────────────────────────────────────────

    socket.on('disconnect', () => {
      console.log('Client disconnected:', socket.id);
      const result = removePlayer(socket.id);
      if (!result) return;
      if (result.dissolved) {
        broadcast(result.code, 'game:dissolved', { message: 'The host left and the game ended.' });
      } else if (result.game) {
        broadcastState(result.game);
      }
    });
  });

  httpServer.listen(port, () => {
    console.log(`> Mind Your Friends running on http://localhost:${port}`);
  });
});
