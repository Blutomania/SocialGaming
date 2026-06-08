'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { io } from 'socket.io-client';
import Lobby from '../../../components/Lobby';
import GameBoard from '../../../components/GameBoard';
import ScoreBoard from '../../../components/ScoreBoard';

export default function GamePage() {
  const { code } = useParams();
  const router = useRouter();
  const socketRef = useRef(null);
  const [socketId, setSocketId] = useState(null);
  const [gameState, setGameState] = useState(null);
  const [phase, setPhase] = useState('connecting'); // connecting | lobby | playing | game_over | error
  const [errorMsg, setErrorMsg] = useState('');
  const [notification, setNotification] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [moments, setMoments] = useState([]);
  const [questionReady, setQuestionReady] = useState(null);
  const [timerSeconds, setTimerSeconds] = useState(15);

  const showNotification = useCallback((msg, color = 'game-accent') => {
    setNotification({ msg, color });
    setTimeout(() => setNotification(null), 3500);
  }, []);

  useEffect(() => {
    const playerName = sessionStorage.getItem('playerName');
    if (!playerName) {
      router.push('/');
      return;
    }

    const socket = io({ path: '/socket.io', transports: ['websocket', 'polling'] });
    socketRef.current = socket;

    socket.on('connect', () => {
      setSocketId(socket.id);
      // Attempt to join/rejoin — server will reject if game already started
      // In that case we stay in connecting state until game:state arrives (won't)
      // so we redirect home gracefully.
      socket.emit('lobby:join', { code, playerName }, (res) => {
        if (res?.error && res.error !== 'Game already in progress.') {
          setErrorMsg(res.error);
          setPhase('error');
        }
        // If 'Game already in progress', game:state won't come — show error
        if (res?.error === 'Game already in progress.') {
          setErrorMsg('This game has already started. You can only join from the lobby.');
          setPhase('error');
        }
      });
    });

    socket.on('game:state', (state) => {
      setGameState(state);
      setTimerSeconds(state.timerSeconds ?? 15);
      if (state.phase === 'lobby') setPhase('lobby');
      else if (state.phase === 'game_over') setPhase('game_over');
      else setPhase('playing');
    });

    socket.on('game:started', ({ roundNumber, roundRule }) => {
      setPhase('playing');
      showNotification(`Round ${roundNumber} — ${roundRule?.emoji} ${roundRule?.name}!`, 'game-gold');
    });

    socket.on('round:new', ({ roundNumber, roundRule }) => {
      showNotification(`Round ${roundNumber} — ${roundRule?.emoji} ${roundRule?.name}!`, 'game-gold');
      setLastResult(null);
      setQuestionReady(null);
    });

    socket.on('question:ready', (data) => {
      setQuestionReady(data);
    });

    socket.on('timer:tick', ({ secondsLeft }) => {
      setTimerSeconds(secondsLeft);
    });

    socket.on('turn:result', (data) => {
      setLastResult(data);
    });

    socket.on('card:played', ({ playerId, cardId, effects, wager }) => {
      showNotification(`A card was played! Wager: ${wager} pts`, 'game-pink');
    });

    socket.on('game:over', ({ scores, players, moments: m }) => {
      if (m) setMoments(m);
      setPhase('game_over');
    });

    socket.on('game:dissolved', ({ message }) => {
      setErrorMsg(message);
      setPhase('error');
    });

    socket.on('error', ({ message }) => {
      showNotification(message, 'game-red');
    });

    return () => {
      socket.disconnect();
    };
  }, [code, router, showNotification]);

  function emit(event, data, cb) {
    socketRef.current?.emit(event, data, cb);
  }

  if (phase === 'connecting') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-400 text-xl animate-pulse">Connecting to game...</p>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6">
        <p className="text-game-red text-2xl font-bold">{errorMsg || 'Something went wrong.'}</p>
        <button
          onClick={() => router.push('/')}
          className="px-6 py-3 bg-game-accent rounded-xl text-white font-bold"
        >
          Back to Home
        </button>
      </div>
    );
  }

  if (phase === 'game_over' && gameState) {
    return <ScoreBoard gameState={gameState} moments={moments} onHome={() => router.push('/')} />;
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Notification banner */}
      {notification && (
        <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 px-6 py-3 rounded-xl font-bold text-lg shadow-2xl bg-game-accent text-white animate-bounce`}>
          {notification.msg}
        </div>
      )}

      {phase === 'lobby' && gameState && (
        <Lobby
          gameState={gameState}
          socketId={socketId}
          emit={emit}
          code={code}
        />
      )}

      {phase === 'playing' && gameState && (
        <GameBoard
          gameState={gameState}
          socketId={socketId}
          emit={emit}
          code={code}
          lastResult={lastResult}
          questionReady={questionReady}
          timerSeconds={timerSeconds}
        />
      )}
    </div>
  );
}
