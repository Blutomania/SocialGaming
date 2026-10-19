'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { io } from 'socket.io-client';
import BrandBar from '../../../components/BrandBar';
import HostStage from '../../../components/HostStage';
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

  // Both of these are pages in their own right as far as a player is
  // concerned, so they carry the same chrome as the rest — the brand bar is
  // not something that appears once the game state arrives.
  if (error) {
    return (
      <main className="mx-auto min-h-screen max-w-7xl p-4 md:p-8">
        <BrandBar />
        <p className="pt-10 text-center text-ui-negative">{error}</p>
      </main>
    );
  }

  if (!game) {
    return (
      <main className="mx-auto min-h-screen max-w-7xl p-4 md:p-8">
        <BrandBar />
        {/* Live status, not a sentence: it is still happening (§2g). */}
        <div className="pt-10 text-center">
          <span className="live"><span className="live-text">Connecting…</span></span>
        </div>
      </main>
    );
  }

  const socket = socketRef.current;

  return (
    <main className="mx-auto min-h-screen max-w-7xl p-4 md:p-8">
      {/* Two columns on a desktop, one on a phone (owner's markup, Session
          50): the game takes two thirds and is centred in them; the host's
          9:16 stage takes the last third and is the ONLY thing there.

          The brand bar lives INSIDE the game column for that reason. It used
          to span the whole page, which put the logo on the page's centre line
          and everything beneath it on the game column's — two centres ~170px
          apart at 1280 — and parked the room code above the host's slot. */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="min-w-0">
          <BrandBar code={game.code} showTitle={false} />
          {game.phase === 'LOBBY' && <Lobby game={game} myId={myId} socket={socket} />}
          {game.phase === 'GAME_OVER' && <ScoreBoard game={game} myId={myId} socket={socket} />}
          {game.phase !== 'LOBBY' && game.phase !== 'GAME_OVER' && (
            <GameBoard game={game} myId={myId} socket={socket} />
          )}
        </div>

        <HostStage />
      </div>
    </main>
  );
}
