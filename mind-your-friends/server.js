// Custom Socket.io server wrapping Next.js. All game logic lives in
// lib/gameState.js — this file is the event hub: it validates the socket,
// calls into gameState, and broadcasts the resulting state. The client never
// calls the Claude API directly.

// MUST be first: populates process.env from .env.local before any module below
// reads it at import scope (claudeClient.js builds its API client on import).
// See lib/env.js for why this can't just be a call in this file's body.
import './lib/env.js';

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

// How long post-game superlative voting stays open before the votes that did
// arrive get tallied anyway.
const POST_GAME_VOTE_MS = 90000;

app.prepare().then(() => {
  const httpServer = createServer((req, res) => handle(req, res));
  const io = new Server(httpServer);

  io.on('connection', (socket) => {
    socket.on('game:create', ({ name }) => {
      let game = gameState.createGame(socket.id, name);
      let attempts = 0;
      while (games.has(game.code) && attempts < 10) {
        game = gameState.createGame(socket.id, name);
        attempts++;
      }
      if (games.has(game.code)) {
        socket.emit('error', { message: 'Could not generate a unique game code — try again' });
        return;
      }
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

    // Start is instant now: no fact bank is built here. The bank fills in
    // behind the game — see gameState's fact-bank section — so the room is
    // on the category screen immediately instead of watching a progress bar.
    socket.on('game:start', () => {
      withMyGame(socket, (game) => {
        gameState.startGame(game);
        broadcast(io, game);
        gameState.prefetchFactBank(game, () => broadcast(io, game));
      });
    });

    socket.on('turn:pickCategory', ({ category }) => {
      withMyGame(socket, (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);
        gameState.pickCategory(game, playerId, category);
        broadcast(io, game);
        // Start fetching this category's facts NOW rather than at question
        // time: the wager and card windows are about to run, which is free
        // cover for the round trip. runQuestionPhase awaits the same promise,
        // so this is a head start, not a race.
        gameState.ensureCategoryFacts(game, category);
      });
    });

    socket.on('turn:setWager', ({ amount }) => {
      withMyGame(socket, (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);
        gameState.setWager(game, playerId, amount);
        broadcast(io, game);
        startCardWindow(io, game);
      });
    });

    socket.on('turn:playCard', ({ cardId, payload }) => {
      withMyGame(socket, (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);
        gameState.playCard(game, playerId, cardId, payload);
        broadcast(io, game);
        resolveCardWindow(io, game);
      });
    });

    socket.on('turn:submitAnswer', ({ answer, inputMode }) => {
      withMyGame(socket, async (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);

        if (game.roundRule.submissionBased) {
          const allIn = gameState.submitGroupAnswer(game, playerId, answer, inputMode);
          broadcast(io, game);
          if (allIn) {
            await evaluateGroupAnswers(io, game).catch((err) => recoverFromFailedTurn(io, game, err));
          }
          return;
        }

        // Flow B: the answerer alone for the exclusive window, then everyone.
        // One attempt each and the first correct one ends it; a wrong attempt
        // just locks that player out, so the turn is only over when the phase
        // actually moves.
        await gameState.submitAnswer(game, playerId, answer, inputMode);
        broadcast(io, game);
        if (game.phase === 'RESULT') {
          scheduleNextTurn(io, game);
        }
      });
    });

    // Commit an answer during the answerer's exclusive window. Not evaluated
    // and not revealed — it only becomes a real attempt if its owner buzzes.
    // Ack rather than the global 'error' event: missing the lock deadline is
    // an ordinary outcome, not a page-replacing failure.
    socket.on('turn:lockAnswer', ({ answer, inputMode }, ack) => {
      withMyGame(socket, (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);
        try {
          gameState.lockAnswer(game, playerId, answer, inputMode);
        } catch (err) {
          if (typeof ack === 'function') ack({ ok: false, message: err.message });
          return;
        }
        if (typeof ack === 'function') ack({ ok: true });
        // Broadcast: the room sees the locked-in COUNT rise (never the
        // answers), which is most of the tension this mechanic creates.
        broadcast(io, game);
      });
    });

    // Play a committed answer. The buzz sets the order; the answer was fixed
    // before the answerer fumbled.
    socket.on('turn:buzzIn', (_payload, ack) => {
      withMyGame(socket, async (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);
        try {
          await gameState.buzzIn(game, playerId);
        } catch (err) {
          if (typeof ack === 'function') ack({ ok: false, message: err.message });
          return;
        }
        if (typeof ack === 'function') ack({ ok: true });
        broadcast(io, game);
        if (game.phase === 'RESULT') {
          scheduleNextTurn(io, game);
        }
      });
    });

    // Flow B: the answerer folds. Costs them nothing and opens the buzzer at
    // once. Ack callback rather than the global 'error' event — same reason
    // as turn:attemptLineup: losing a race to the buzzer opening should give
    // local feedback, not replace the whole page.
    socket.on('turn:passAnswer', (_payload, ack) => {
      withMyGame(socket, (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);
        try {
          gameState.passAnswer(game, playerId);
        } catch (err) {
          if (typeof ack === 'function') ack({ ok: false, message: err.message });
          return;
        }
        if (typeof ack === 'function') ack({ ok: true });
        broadcast(io, game);
      });
    });

    // The Lineup: any player may tap any option at any time. Wrong taps are
    // NOT an error (the global 'error' event replaces the whole page — see
    // page.js — wrong on purpose here) so the picker gets an ack callback
    // for local feedback instead; only the winning tap broadcasts state.
    socket.on('turn:attemptLineup', ({ optionId }, ack) => {
      withMyGame(socket, (game, playerId) => {
        gameState.recordPlayerAction(game, playerId);
        const result = gameState.attemptLineupPick(game, playerId, optionId);
        if (typeof ack === 'function') ack(result);
        if (result.correct) {
          broadcast(io, game);
          scheduleNextTurn(io, game);
        }
      });
    });

    // Post-game superlative voting (CLAUDE.md item 35). Uses an ack callback
    // rather than the global 'error' event for the same reason attemptLineup
    // does: a rejected vote should give local feedback, not replace the page.
    socket.on('postgame:vote', ({ categoryId, targetPlayerId }, ack) => {
      withMyGame(socket, async (game, playerId) => {
        try {
          gameState.castSuperlativeVote(game, playerId, categoryId, targetPlayerId);
        } catch (err) {
          if (typeof ack === 'function') ack({ ok: false, message: err.message });
          return;
        }
        if (typeof ack === 'function') ack({ ok: true });
        broadcast(io, game);

        if (gameState.allSuperlativeVotesIn(game)) {
          await gameState.resolveSuperlatives(game);
          broadcast(io, game);
        }
      });
    });

    // "Skip all" — abstain from every remaining award at once. Same ack-based
    // error handling as postgame:vote.
    socket.on('postgame:skip', (_payload, ack) => {
      withMyGame(socket, async (game, playerId) => {
        try {
          gameState.skipSuperlativeVoting(game, playerId);
        } catch (err) {
          if (typeof ack === 'function') ack({ ok: false, message: err.message });
          return;
        }
        if (typeof ack === 'function') ack({ ok: true });
        broadcast(io, game);

        if (gameState.allSuperlativeVotesIn(game)) {
          await gameState.resolveSuperlatives(game);
          broadcast(io, game);
        }
      });
    });

    socket.on('disconnect', () => {
      const entry = sockets.get(socket.id);
      if (entry) {
        const game = games.get(entry.code);
        if (game && game.phase !== 'LOBBY') {
          gameState.disconnectPlayer(game, socket.id);
          broadcast(io, game);
          // No grace period once the game is over. People close the tab the
          // moment they've seen the scores — starting a "wait for our friend?"
          // vote at that point interrupts the post-game screens for everyone
          // still there, to decide whether to resume a game that has ended.
          if (game.phase !== 'GAME_OVER') {
            startGracePeriod(io, game, socket.id);
          } else if (gameState.allSuperlativeVotesIn(game)) {
            // Their leaving may have been the last thing the tally was waiting
            // on — re-check, or the rest of the room waits out the full timer.
            gameState
              .resolveSuperlatives(game)
              .then(() => broadcast(io, game))
              .catch((err) => console.error('Superlative tally failed:', err));
          }
        }
      }
      sockets.delete(socket.id);
    });

    socket.on('game:rejoin', ({ code, name }) => {
      withGame(socket, code, (game) => {
        const existing = game.players.find((p) => p.name === name && !p.connected);
        if (!existing) {
          socket.emit('error', { message: 'No disconnected player with that name found' });
          return;
        }
        const oldId = existing.id;
        gameState.reconnectPlayer(game, oldId, socket.id);
        sockets.set(socket.id, { code, playerId: socket.id });
        socket.join(code);
        broadcast(io, game);
      });
    });

    socket.on('disconnect:vote', ({ vote }) => {
      withMyGame(socket, (game, playerId) => {
        const { resolved, action } = gameState.castDisconnectVote(game, playerId, vote);
        broadcast(io, game);
        if (resolved && action === 'continue' && !gameState.shouldPause(game)) {
          resumeAfterDisconnect(io, game);
        }
      });
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

  // If a Claude API call in the turn pipeline throws (network error,
  // truncated/unparseable JSON, etc.) the turn would otherwise hang forever
  // in QUESTION/ANSWER phase with no client feedback. Skip it and move on.
  function recoverFromFailedTurn(io, game, err) {
    console.error('Turn failed, skipping:', err);
    game.phase = 'RESULT';
    game.skippedTurn = true;
    broadcast(io, game);
    scheduleNextTurn(io, game);
  }

  function startCardWindow(io, game) {
    setTimeout(() => {
      if (game.phase !== 'CARD') return; // already resolved by a card play
      finishCardPhase(io, game).catch((err) => recoverFromFailedTurn(io, game, err));
    }, CARD_WINDOW_MS);
  }

  function resolveCardWindow(io, game) {
    if (game.phase !== 'CARD') return;
    finishCardPhase(io, game).catch((err) => recoverFromFailedTurn(io, game, err));
  }

  async function finishCardPhase(io, game) {
    await gameState.resolveCardSlot(game);
    broadcast(io, game);
    if (game.phase === 'RESULT') {
      // Skip card — turn ends with no question.
      scheduleNextTurn(io, game);
      return;
    }
    await gameState.runQuestionPhase(game);
    broadcast(io, game);
    startActiveWindowTimer(io, game);
    startAnswerTimer(io, game);
  }

  // Flow B's exclusive window. A second timer inside the same ANSWER phase,
  // not a phase of its own — same reasoning as the reading window: every
  // phase-timeout and auto-advance helper here assumes the existing loop.
  //
  // Fires whether or not the answerer acted; expireActiveWindow no-ops if
  // they did, since answering or passing already opened the buzzer.
  function startActiveWindowTimer(io, game) {
    if (game.roundRule.submissionBased || game.roundRule.lineupBased) return;
    setTimeout(() => {
      if (game.phase !== 'ANSWER') return;
      const answerer = game.players[game.answererIndex];
      // Read before the call — expireActiveWindow is what writes the attempt.
      const froze = !game.answerAttempts?.[answerer.id] && !answerer.droppedOut;
      if (!gameState.expireActiveWindow(game)) return;
      // Never acting on your own question is the inactivity signal. It used
      // to be read when the whole window closed; under Flow B the answerer's
      // own window closing is the exact moment it's known, and passing is a
      // real action, so a player who folds is not marked away for it.
      if (froze) gameState.recordAutoAdvance(game, answerer.id);
      broadcast(io, game);
      // This is also the moment locking closes, so it can end the question
      // outright when nobody committed an answer to buzz with.
      if (game.phase === 'RESULT') scheduleNextTurn(io, game);
    }, gameState.getActiveWindowMs(game));
  }

  // One timer covers the whole ANSWER phase: the reading window plus the
  // answer clock (see gameState.getAnswerWindowMs). The reading window is a
  // timestamp on the game, not a phase of its own, so nothing else in this
  // file's timer bookkeeping has to learn about it.
  function startAnswerTimer(io, game) {
    const ms = gameState.getAnswerWindowMs(game);
    setTimeout(() => {
      if (game.phase !== 'ANSWER') return; // already resolved (someone got it, all submitted, or skip path)

      if (game.roundRule.submissionBased) {
        gameState.autoFillMissingSubmissions(game);
        evaluateGroupAnswers(io, game).catch((err) => recoverFromFailedTurn(io, game, err));
        return;
      }

      if (game.roundRule.lineupBased) {
        gameState.expireLineup(game);
        broadcast(io, game);
        scheduleNextTurn(io, game);
        return;
      }

      // Nobody got it in time. The answerer has normally been settled with
      // already — by their own answer or pass, or by startActiveWindowTimer
      // charging them for freezing (which is also where the inactivity signal
      // is now recorded, so there is no second recordAutoAdvance here).
      gameState.expireAnswerWindow(game);
      broadcast(io, game);
      scheduleNextTurn(io, game);
    }, ms);
  }

  // Worst Answer Wins (and future submission-based rules): flips to the
  // transient EVALUATING phase synchronously first, so a submission landing
  // at the exact instant the answer timer also fires can't trigger this
  // twice -- whichever caller runs first wins the phase, the other's
  // `game.phase !== 'ANSWER'` guard then no-ops.
  async function evaluateGroupAnswers(io, game) {
    gameState.beginGroupEvaluation(game);
    broadcast(io, game);
    await gameState.resolveGroupAnswers(game);
    broadcast(io, game);
    scheduleNextTurn(io, game);
  }

  function scheduleNextTurn(io, game) {
    setTimeout(() => {
      if (game.phase !== 'RESULT') return; // already advanced by another path
      gameState.nextTurn(game);
      broadcast(io, game);
      if (game.phase === 'GAME_OVER') startPostGame(io, game);
    }, gameState.RESULT_SCREEN_MS);
  }

  // Kicks off superlative voting once the game ends. Generation is a real
  // Claude call, so the GAME_OVER screen broadcasts first and the voting UI
  // appears a moment later rather than making everyone stare at a spinner.
  //
  // Failure here is deliberately non-fatal: the scoreboard, highlight reel and
  // Shareable Question all work without superlatives, and losing the whole
  // end-of-game screen because one flavor call failed would be a bad trade.
  function startPostGame(io, game) {
    gameState
      .beginSuperlativeVoting(game)
      .then(() => {
        // Claude can return an empty set without throwing. Leaving postGame in
        // place with no categories parks everyone on a "tallying up…" spinner
        // for the full timer with nothing to vote on — drop it instead and let
        // the plain scoreboard + Shareable Question stand on their own.
        if (game.postGame && game.postGame.categories.length === 0) {
          game.postGame = null;
          broadcast(io, game);
          return;
        }
        broadcast(io, game);
        setTimeout(() => {
          // One slow (or departed) player must not strand everyone on the
          // voting screen — tally whatever came in.
          if (game.postGame?.stage !== 'voting') return;
          gameState
            .resolveSuperlatives(game)
            .then(() => broadcast(io, game))
            .catch((err) => console.error('Superlative tally failed:', err));
        }, POST_GAME_VOTE_MS);
      })
      .catch((err) => {
        console.error('Superlative generation failed:', err);
        game.postGame = null; // let the client fall back to the plain scoreboard
        broadcast(io, game);
      });
  }

  function startGracePeriod(io, game, disconnectedPlayerId) {
    setTimeout(() => {
      const player = game.players.find((p) => p.id === disconnectedPlayerId);
      if (!player || player.connected) return;
      gameState.startDisconnectVote(game, disconnectedPlayerId);
      broadcast(io, game);
    }, gameState.DISCONNECT_GRACE_MS);
  }

  function resumeAfterDisconnect(io, game) {
    if (gameState.isPlayerDroppedOut(game, game.activePlayerIndex)) {
      gameState.resumeAfterDrop(game);
    }
    broadcast(io, game);
    // resumeAfterDrop() can itself end the game (skipUnavailablePlayers runs
    // out the question count). That's a second route to GAME_OVER that doesn't
    // pass through scheduleNextTurn, so without this the post-game screens
    // never appear for a game that ended by attrition.
    if (game.phase === 'GAME_OVER') startPostGame(io, game);
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
