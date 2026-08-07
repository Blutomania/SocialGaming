'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { io } from 'socket.io-client';
import Lobby from '../../../components/Lobby';
import GameBoard from '../../../components/GameBoard';
import ScoreBoard from '../../../components/ScoreBoard';

export default function GamePage() {
  const params = useParams();
  const socketRef = useRef(null);
  const [game, setGame] = useState(null);
  const [myId, setMyId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const name = sessionStorage.getItem('myf:name') || 'Player';
    const action = sessionStorage.getItem('myf:action') || 'join';

    const socket = io();
    socketRef.current = socket;

    socket.on('connect', () => {
      setMyId(socket.id);
      if (action === 'create') {
        socket.emit('game:create', { name });
      } else {
        socket.emit('game:join', { code: params.code, name });
      }
    });

    socket.on('game:state', (state) => setGame(state));
    socket.on('error', ({ message }) => setError(message));

    return () => socket.disconnect();
  }, [params.code]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center p-8">
        <p className="text-game-red">{error}</p>
      </main>
    );
  }

  if (!game) {
    return (
      <main className="flex min-h-screen items-center justify-center p-8">
        <p>Connecting…</p>
      </main>
    );
  }

  const socket = socketRef.current;

  return (
    <main className="min-h-screen p-4 md:p-8">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-game-accent">Mind Your Friends</h1>
        <span className="rounded bg-game-card px-3 py-1 font-mono text-lg tracking-widest">
          {game.code}
        </span>
      </header>

      {game.phase === 'LOBBY' && <Lobby game={game} myId={myId} socket={socket} />}
      {game.phase === 'GAME_OVER' && <ScoreBoard game={game} myId={myId} />}
      {game.phase !== 'LOBBY' && game.phase !== 'GAME_OVER' && (
        <GameBoard game={game} myId={myId} socket={socket} />
      )}
    </main>
  );
}
