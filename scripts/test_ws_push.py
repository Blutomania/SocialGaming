#!/usr/bin/env python3
"""
test_ws_push.py -- that what one player does actually reaches the others' screens.

WHY THIS EXISTS. The Session 49 playtest stalled at round 2: the three seated
players paid their share checkpoint (their terminal said so), but the host's
screen still showed them owing, so "Open the next round" never enabled. The
server's state was right the whole time. The PUSH never left: _broadcast_sync
asked a worker thread for an event loop, got a RuntimeError, and swallowed it.
Every plain `def` route -- joins, APF shares, round openings -- pushed nothing.

No other checker could see it. walk_apf_game.py and test_apf.py both READ state
by polling, which was never broken; nothing LISTENED. This one listens.

It also pins the opposite failure: a player announced twice. The socket used to
announce whoever connected, on top of the announcement /join already made, so
the lobby showed the host twice (screen 1 of the same playtest).

Starts its own server on a spare port in a background thread -- no running
server, no API key, zero API cost. Needs `websockets`, which uvicorn[standard]
in server/requirements.txt already installs.

Run: python3 scripts/test_ws_push.py
"""

import asyncio
import json
import os
import socket
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
import websockets

from server.main import app

FAILURES = []


def ok(label, cond, detail=""):
    print(("  ok    " if cond else "  FAIL  ") + label + ("" if cond else f"  -- {detail}"))
    if not cond:
        FAILURES.append(label)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = free_port()
BASE = f"http://127.0.0.1:{PORT}"


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read() or b"{}")


def start_server() -> uvicorn.Server:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            return server
        time.sleep(0.1)
    raise SystemExit("server did not start")


async def walk() -> list:
    """The host listens; everyone else acts over plain HTTP, as seat_players.py
    and the phones do. Returns every event the host's socket received."""
    ready = [m["slug"] for m in call("GET", "/mysteries") if m.get("apf_ready")]
    if not ready:
        raise SystemExit("no apf_ready mystery on disk to play")
    g = call("POST", "/games/create",
             {"mystery_slug": ready[0], "host_name": "Host", "difficulty": "MEDIUM"})
    gid, host = g["game_id"], g["player_id"]

    got = []
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/{gid}?player_id={host}") as ws:
        async def listen():
            async for msg in ws:
                got.append(json.loads(msg))
        listener = asyncio.create_task(listen())

        # urllib blocks, so each call goes to a thread: the listener must keep
        # draining the socket while the server handles the request.
        def act(*a):
            return asyncio.to_thread(call, *a)

        others = [(await act("POST", f"/games/{gid}/join", {"player_name": n}))["player_id"]
                  for n in ("Bardsley", "Chen", "Okonjo")]
        await act("POST", f"/games/{gid}/apf/open", {"player_id": host})
        await act("POST", f"/games/{gid}/apf/round/next", {"player_id": host})
        await act("POST", f"/games/{gid}/apf/round/next", {"player_id": host})
        mine = await act("GET", f"/games/{gid}/apf/state?player_id={others[0]}")
        await act("POST", f"/games/{gid}/apf/share",
                  {"player_id": others[0], "finding_ids": [mine["casefile"][0]["id"]]})

        await asyncio.sleep(1.0)       # let the last pushes land
        listener.cancel()
    return got


def main() -> int:
    print("test_ws_push -- does the host hear what the others do?")
    start_server()
    events = asyncio.run(walk())
    names = [e.get("event") for e in events]

    joined = [e["data"].get("name") for e in events if e.get("event") == "player_joined"]
    ok("each of the three joins reaches the host", joined.count("Bardsley") == 1
       and joined.count("Chen") == 1 and joined.count("Okonjo") == 1, str(joined))
    ok("the host is never announced to itself", "Host" not in joined, str(joined))
    ok("opening the assignment is pushed", "apf_opened" in names, str(names))

    states = [e["data"] for e in events if e.get("event") == "apf_state"]
    ok("round changes and shares are pushed", len(states) >= 2, str(names))
    if states:
        last = states[-1]
        by_name = {p["name"]: p["shared"] for p in last.get("players", [])}
        ok("the host learns Bardsley shared -- the push the round-2 stall was missing",
           by_name.get("Bardsley") == 1, str(by_name))
        ok("and sees it in the shared pool", len(last.get("shared_pool", [])) >= 1,
           str(last.get("shared_pool")))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
