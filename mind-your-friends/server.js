// Custom Socket.io server wrapping Next.js. All game logic lives in
// lib/gameState.js — this file is the event hub: it validates the socket,
// calls into gameState, and broadcasts the resulting state. The client never
// calls the Claude API directly.

import { createServer } from 'http';
import next from 'next';
import { Server } from 'socket.io';
import * as gameState from './lib/gameState.js';

const dev = process.env.NODE_ENV !== 'production';
const port = process.env.PORT || 3000;
const app = next({ dev });
const handle = app.getRequestHandler();

// code -> game object (lib/gameState.js)
const games = new Map();
// socket.id -> { code, playerId }
const sockets = new Map();

// How long the FCFS card window stays open before auto-resolving.
const CARD_WINDOW_MS = 8000;

app.prepare().then(() => {
  const httpServer = createServer((req, res) => handle(req, res));
  const io = new Server(httpServer);

  io.on('connection', (socket) => {
    socket.on('game:create', ({ name }) => {
      const game = gameState.createGame(socket.id, name);
      games.set(game.code, game);
      sockets.set(socket.id, { code: game.code, playerId: socket.id });
      socket.join(game.code);
      broadcast(io, game);
    });

    socket.on('game:join', ({ code, name }) => {
      withGame(socket, code, (game) => {
        gameState.addPlayer(game, socket.id, name);
        sockets.set(socket.id, { code, playerId: socket.id });
        socket.join(code);
        broadcast(io, game);
      });
    });

    socket.on('player:register', ({ categories, pickedCardId }) => {
      withMyGame(socket, (game, playerId) => {
        gameState.registerPlayer(game, playerId, { categories, pickedCardId });
        broadcast(io, game);
      });
    });

    socket.on('game:start', () => {
      withMyGame(socket, (game) => {
        gameState.startGame(game);
        broadcast(io, game);
      });
    });

    socket.on('turn:pickCategory', ({ category }) => {
      withMyGame(socket, (game, playerId) => {
        gameState.pickCategory(game, playerId, category);
        broadcast(io, game);
      });
    });

    socket.on('turn:setWager', ({ amount }) => {
      withMyGame(socket, (game, playerId) => {
        gameState.setWager(game, playerId, amount);
        broadcast(io, game);
        startCardWindow(io, game);
      });
    });

    socket.on('turn:playCard', ({ cardId, payload }) => {
      withMyGame(socket, (game, playerId) => {
        gameState.playCard(game, playerId, cardId, payload);
        broadcast(io, game);
        // First card played closes the window immediately.
        resolveCardWindow(io, game);
      });
    });

    socket.on('turn:submitAnswer', ({ answer, inputMode }) => {
      withMyGame(socket, async (game, playerId) => {
        await gameState.submitAnswer(game, playerId, answer, inputMode);
        broadcast(io, game);
        scheduleNextTurn(io, game);
      });
    });

    socket.on('disconnect', () => {
      sockets.delete(socket.id);
      // TODO: handle mid-game disconnects (pause, remove player, etc.)
    });
  });

  // --- helpers ---------------------------------------------------------

  function withGame(socket, code, fn) {
    const game = games.get(code);
    if (!game) {
      socket.emit('error', { message: `Game ${code} not found` });
      return;
    }
    try {
      fn(game);
    } catch (err) {
      socket.emit('error', { message: err.message });
    }
  }

  function withMyGame(socket, fn) {
    const entry = sockets.get(socket.id);
    if (!entry) {
      socket.emit('error', { message: 'Not in a game' });
      return;
    }
    const game = games.get(entry.code);
    if (!game) {
      socket.emit('error', { message: `Game ${entry.code} not found` });
      return;
    }
    try {
      const result = fn(game, entry.playerId);
      if (result instanceof Promise) {
        result.catch((err) => socket.emit('error', { message: err.message }));
      }
    } catch (err) {
      socket.emit('error', { message: err.message });
    }
  }

  function startCardWindow(io, game) {
    setTimeout(() => {
      if (game.phase !== 'CARD') return; // already resolved by a card play
      finishCardPhase(io, game);
    }, CARD_WINDOW_MS);
  }

  function resolveCardWindow(io, game) {
    if (game.phase !== 'CARD') return;
    finishCardPhase(io, game);
  }

  async function finishCardPhase(io, game) {
    gameState.resolveCardSlot(game);
    broadcast(io, game);
    if (game.phase === 'RESULT') {
      // Skip card — turn ends with no question.
      scheduleNextTurn(io, game);
      return;
    }
    await gameState.runQuestionPhase(game);
    broadcast(io, game);
    startAnswerTimer(io, game);
  }

  function startAnswerTimer(io, game) {
    const ms = gameState.getTimerSeconds(game) * 1000;
    setTimeout(() => {
      if (game.phase !== 'ANSWER') return; // already answered
      // Timeout = wrong answer with empty submission.
      gameState
        .submitAnswer(game, game.players[game.answererIndex].id, '', 'text')
        .then(() => {
          broadcast(io, game);
          scheduleNextTurn(io, game);
        });
    }, ms);
  }

  function scheduleNextTurn(io, game) {
    setTimeout(() => {
      gameState.nextTurn(game);
      broadcast(io, game);
    }, gameState.RESULT_SCREEN_MS);
  }

  function broadcast(io, game) {
    const room = io.sockets.adapter.rooms.get(game.code);
    if (!room) return;
    for (const socketId of room) {
      const entry = sockets.get(socketId);
      if (!entry) continue;
      io.to(socketId).emit('game:state', gameState.playerView(game, entry.playerId));
    }
  }

  httpServer.listen(port, () => {
    console.log(`> Mind Your Friends ready on http://localhost:${port}`);
  });
});
