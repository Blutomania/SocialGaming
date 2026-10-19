'use client';

import { useEffect, useRef, useState } from 'react';
import CategoryPicker from './CategoryPicker';
import CardHand from './CardHand';
import VoiceInput from './VoiceInput';
import WagerPie from './WagerPie';
import { WAGER_TIERS, QUESTIONS_PER_ROUND } from '../lib/constants';
import { difficultyColor } from '../lib/difficultyColors';
import { CARD_INFO } from '../lib/cards';

// Still happening (style guide §2g): an outlined notice with a slow shimmer.
// Rendered only while the status is live, so the motion leaves with it.
function LiveNotice({ children }) {
  return (
    <div className="text-center">
      <span className="live">
        <span className="live-text">{children}</span>
      </span>
    </div>
  );
}

// The answer, only when there is one (§3a) — a bare "Correct answer:" with
// nothing after it reads as a bug, and some flows (a skipped Lineup) carry none.
function CorrectAnswer({ answer }) {
  if (!answer?.toString().trim()) return null;
  return <p className="text-sm text-ui-faint">Correct answer: {answer}</p>;
}

// Strip quote marks a player (or the generator) already typed before this
// screen wraps the text in its own curly pair — or it reads ““like this””.
function unquote(text) {
  return String(text ?? '').trim().replace(/^["'“”‘’]+|["'“”‘’]+$/g, '');
}

export default function GameBoard({ game, myId, socket }) {
  const round = game.roundNumber ?? Math.floor(game.questionIndex / QUESTIONS_PER_ROUND) + 1;
  const questionInRound = (game.questionIndex % QUESTIONS_PER_ROUND) + 1;
  // Round 1 runs with no rule on purpose, so a new player learns the base
  // game first; the server sends id 'none' for it rather than null so nothing
  // downstream has to null-check.
  const rule = game.roundRule && game.roundRule.id !== 'none' ? game.roundRule : null;

  return (
    // space-y-6, not 4: the gap between plates is where the field shows
    // through, and that is the only thing that makes two stacked plates read
    // as two plates rather than as one tall block. At 10% mark strength a
    // 16px gap is statistically likely to contain no mark at all.
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <ScoreStrip game={game} myId={myId} round={round} questionInRound={questionInRound} />

      {game.roundAnnouncement && (
        <RoundAnnouncement announcement={game.roundAnnouncement} />
      )}

      {/* The rule stays on screen for the rest of the round — a rule you have
          to remember is one people forget mid-round and then feel cheated by.
          Hidden on the announcement turn itself, where the banner above is
          already saying the same words twice, and on the ANSWER screen, where
          item 40 puts it inside the question's own plate instead: Rebus, ELI5
          and Boxed In all change how an answer must be GIVEN, so at the moment
          of answering the rule is part of reading the question rather than a
          box above it. */}
      {rule && !game.roundAnnouncement && game.phase !== 'ANSWER' && (
        <div className="panel px-4 py-2 text-center">
          <span className="text-lg">{rule.emoji}</span>{' '}
          <span className="font-semibold">{rule.name}</span>
          {rule.description && <span className="ml-2 text-sm text-ui-faint">{rule.description}</span>}
        </div>
      )}

      <div className="panel p-4">
        {game.phase === 'CATEGORY' && <CategoryPicker game={game} myId={myId} socket={socket} />}
        {game.phase === 'WAGER' && <WagerPicker game={game} myId={myId} socket={socket} />}
        {game.phase === 'CARD' && <CardPhase game={game} myId={myId} socket={socket} />}
        {game.phase === 'QUESTION' && <LiveNotice>Writing the question</LiveNotice>}
        {game.phase === 'ANSWER' && <AnswerPhase game={game} myId={myId} socket={socket} />}
        {game.phase === 'EVALUATING' && (
          <LiveNotice>The host is judging everyone&apos;s wrongness</LiveNotice>
        )}
        {game.phase === 'RESULT' && <ResultPhase game={game} />}
      </div>

      {game.phase === 'CARD' && <CardHand game={game} myId={myId} socket={socket} />}

      {/* The bank fills in behind the game (see gameState's fact-bank
          section). Surfaced quietly so a slow first question reads as
          "still warming up" rather than "broken" — never as a blocker. */}
      {game.factPrefetch?.active && (
        <p className="text-center text-xs text-ui-faint">
          Warming up questions… {game.factPrefetch.completed}/{game.factPrefetch.total}
        </p>
      )}
    </div>
  );
}

// The puzzle itself. Deliberately enormous — the emoji ARE the question, so
// they get the size a question line would normally get, and the hint sits
// under them as the way in rather than as the main event.
function RebusPuzzle({ rebus }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-center gap-3">
        {rebus.pieces.map((emoji, i) => (
          <span key={i} className="flex items-center gap-3">
            {i > 0 && <span className="text-2xl text-ui-faint">+</span>}
            <span className="text-5xl sm:text-6xl">{emoji}</span>
          </span>
        ))}
      </div>
      {rebus.hint?.trim() && <p className="text-lg font-semibold">{rebus.hint}</p>}
      {rebus.phonetic && (
        <p className="text-xs text-ui-faint">Say the pictures out loud — this one sounds it out.</p>
      )}
    </div>
  );
}

// The reveal. Showing the decomposition is the whole payoff: without it a
// player who missed it never finds out WHY, which is the difference between
// a puzzle and a trick.
function RebusReveal({ rebus, answer }) {
  if (!rebus?.reads) return null;
  return (
    <div className="flex flex-wrap items-center justify-center gap-2 text-sm text-ui-faint">
      {rebus.pieces.map((emoji, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && <span>+</span>}
          <span className="text-2xl">{emoji}</span>
          <span className="font-mono uppercase">{rebus.reads[i]}</span>
        </span>
      ))}
      <span>=</span>
      <span className="font-semibold text-ui-ink">{answer}</span>
    </div>
  );
}

// Shown for the first turn of each round. Round 1's banner says explicitly
// that there is no rule yet, so its absence reads as deliberate rather than
// as something failing to load.
// "Round 1: Question 1 of 4" — one component, so the line reads identically
// wherever it appears (owner, August 18 2026). It used to exist twice: once as
// "ROUND 1" inside the announcement and once as "Round 1 · Question 1/4 (1/4
// total)" floating between the boxes. The floating copy is gone; this is what
// replaced both.
// Item 49 made this one component rendered as the first line of whichever box
// led the page. It now has a single fixed home instead — the standings band —
// which keeps that decision's actual point (the fact is written once, never
// twice) while taking a line out of the reading column, and puts the round
// data upper-left where item 40 says chrome goes. Where it lives is now a
// property of the band, not of which box happens to be first.
function RoundLine({ round, questionInRound, className = '' }) {
  return (
    <p className={`text-xs tracking-wide text-ui-faint ${className}`}>
      Round {round}: Question {questionInRound} of {QUESTIONS_PER_ROUND}
    </p>
  );
}

function RoundAnnouncement({ announcement }) {
  const plain = announcement.ruleId === 'none';
  return (
    <div className="panel px-4 py-4 text-center">
      {plain ? (
        <>
          <p className="mt-1 text-2xl font-bold">Straight trivia</p>
          <p className="mt-1 text-sm text-ui-faint">
            No twist this round — get your bearings. Rules start next round.
          </p>
        </>
      ) : (
        <>
          <p className="mt-1 text-2xl font-bold">
            {announcement.emoji} {announcement.name}
          </p>
          {announcement.description && (
            <p className="mt-1 text-sm text-ui-faint">{announcement.description}</p>
          )}
        </>
      )}
    </div>
  );
}

// One plate, not one box per player. N boxes across the top is N things the
// eye decodes separately before it ever reaches the question, and the
// standings are ambient — they want to read as a single band of chrome.
//
// The active player is marked by colour rather than with a ring, because a
// ring redraws the box that the plate just dissolved. The colour is Chosen —
// "this is the one" — not Act: gold means "do this", and whose turn it is is
// not something to press (item 53).
function ScoreStrip({ game, myId, round, questionInRound }) {
  return (
    <div className="panel flex flex-wrap items-center justify-center gap-x-6 gap-y-1 px-4 py-2 text-sm sm:justify-between">
      <RoundLine round={round} questionInRound={questionInRound} />
      <div className="flex flex-wrap justify-center gap-x-6 gap-y-1">
        {game.players.map((p, i) => {
          const active = i === game.activePlayerIndex;
          return (
            <span key={p.id} className={active ? 'font-semibold text-ui-chosen' : 'text-ui-faint'}>
              {p.name}{p.id === myId && ' (you)'}{' '}
              <span className={`font-mono ${active ? '' : 'text-ui-ink'}`}>{p.score}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

// Five tiers, not a slider. The pie beside each one is the whole explanation:
// a bigger wedge is a bigger stake and a harder question, and nobody has to be
// told that. See WAGER_TIERS in lib/constants.js for why the ladder replaced
// a continuous 50–500 range.
//
// Laid out beside the selection on desktop and above it on a phone, per the
// owner's call — the pie is the thing you look at while deciding, so it wants
// the reading position, not a corner.
function WagerPicker({ game, myId, socket }) {
  const wagerPlayer = game.players[(game.activePlayerIndex + 1) % game.players.length];
  const [picked, setPicked] = useState(null);
  const activeName = game.players[game.activePlayerIndex].name;

  if (wagerPlayer.id !== myId) {
    return (
      <div className="space-y-3 text-center">
        <LiveNotice>{wagerPlayer.name} is deciding how much to put on it</LiveNotice>
        <div className="flex justify-center gap-2 opacity-40">
          {WAGER_TIERS.map((t) => (
            <WagerPie key={t.value} tier={t} size={44} />
          ))}
        </div>
      </div>
    );
  }

  const tier = picked ?? WAGER_TIERS[1];

  return (
    <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
      {/* The pie: atop on mobile, to the left on desktop. */}
      <div className="flex shrink-0 flex-col items-center gap-2 lg:w-48">
        <WagerPie tier={tier} selected size={140} />
        <p className="text-2xl font-semibold">{tier.value}</p>
      </div>

      <div className="flex-1 space-y-3 text-center">
        <h2 className="text-xl font-semibold">Set {activeName}&apos;s wager</h2>
        <p className="text-sm text-ui-faint">
          The bigger the wedge, the harder the question {activeName} gets.
        </p>
        {game.roundRule.wagerMultiplier && (
          <p className="text-sm text-ui-caution">
            {game.roundRule.name}: this wager will be doubled automatically!
          </p>
        )}

        {/* Five tiles, one lit (owner, Session 50 — the Mob Rules episode
            picker): the wager value small on top, the difficulty it buys
            large beneath. Every tier is named now, not just the two ends — the
            word is the thing a setter is actually choosing ("give her a Hard
            one"), and the number is the price of it.

            The words come from WAGER_TIERS, so a ladder change moves them
            with it. The small pies that used to sit in each tile are gone:
            the big pie above already draws the chosen stake, and five more
            pies beside five words was saying it twice.

            Stacked rows on a phone, where five tiles across leave ~50px for
            a word like HARDEST; five across from sm up. 25 starts chosen: it
            is what gets locked if the setter just taps Lock in. */}
        <div
          className="grid grid-cols-1 gap-2 sm:grid-cols-5"
          role="radiogroup"
          aria-label="Wager"
        >
          {WAGER_TIERS.map((t) => (
            <button
              key={t.value}
              onClick={() => setPicked(t)}
              aria-pressed={t.value === tier.value}
              className="tile w-full max-sm:flex-row max-sm:items-baseline max-sm:gap-3"
            >
              <span className="tile-num font-mono text-sm">{t.value}</span>
              <span className="text-sm font-bold uppercase tracking-wide lg:text-[0.8rem]">
                {t.difficultyLabel}
              </span>
            </button>
          ))}
        </div>

        {/* Smaller than it was (owner, August 18 2026). */}
        <button
          className="act py-1.5 text-sm"
          onClick={() => socket.emit('turn:setWager', { amount: tier.value })}
        >
          Lock in {tier.value}
        </button>
      </div>
    </div>
  );
}

function CardPhase({ game }) {
  // Name the person and the card (§3f): "a card was played" withheld the only
  // two facts the room cares about at that moment.
  const slot = game.cardSlot;
  const playedBy = slot ? game.players.find((p) => p.id === slot.playerId)?.name : null;
  const cardName = slot ? CARD_INFO[slot.cardId]?.name : null;

  return (
    <div className="text-center">
      <p>
        Wager: <span className="font-mono">{game.currentWager}</span> · Category:{' '}
        <span className="font-semibold">{game.currentCategory}</span>
      </p>
      <p className="mt-2 text-sm text-ui-faint">
        {slot
          ? [playedBy, cardName && `played ${cardName}`].filter(Boolean).join(' ') || 'A card was played'
          : 'Anyone may play a card now — first one wins.'}
      </p>
    </div>
  );
}

function AnswerPhase({ game, myId, socket }) {
  const inner = game.roundRule.submissionBased ? (
    <SubmissionAnswerPhase game={game} socket={socket} />
  ) : game.roundRule.lineupBased ? (
    <LineupPhase game={game} socket={socket} />
  ) : (
    <OpenAnswerPhase game={game} myId={myId} socket={socket} />
  );

  return (
    <div className="space-y-3 text-center">
      <RuleChip rule={game.roundRule} />
      {inner}
    </div>
  );
}

// The rule, as a line rather than as a box of its own (item 40). The
// description stays — "a rule you have to remember is one people forget
// mid-round and then feel cheated by" is why the standalone panel exists, and
// that is just as true at the moment of answering. What was costing this
// screen was the BOX, not the words.
function RuleChip({ rule }) {
  if (!rule || rule.id === 'none') return null;
  return (
    <p className="text-xs text-ui-faint">
      <span className="font-semibold uppercase tracking-[0.2em] text-ui-ink">
        {rule.emoji} {rule.name}
      </span>
      {rule.description && <span className="ml-2">{rule.description}</span>}
    </p>
  );
}

// One instruction, one clock. This replaces four separate blocks that each
// carried a countdown and a sentence of their own — the reading window, the
// room's view of the exclusive window, the answerer's view of it, and the lock
// hint. They were never on screen at the same time, so they were never four
// things; they were one thing wearing four faces, and rendering them as four
// independent `&&` blocks is what made the screen read as four instructions.
//
// `note` is capped at a short clause on purpose. Anything needing a sentence
// is a rule the player learned in round 1, and reprinting it every question is
// most of what "too much going on" was made of.
function AnswerStatus({ verb, seconds, note }) {
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-center gap-3">
        <span className="text-sm uppercase tracking-[0.25em] text-ui-faint">{verb}</span>
        {seconds != null && (
          <span className="font-mono text-3xl tabular-nums text-ui-ink">{seconds}</span>
        )}
      </div>
      {note && <p className="text-xs text-ui-faint">{note}</p>}
    </div>
  );
}

// The stake, stated once. It used to be on screen three times at once — a
// header line, the answerer's fine print and the buzzer's fine print — each
// phrased differently, which is how a player ends up reading all three to
// check that they agree with each other.
function StakeLine({ wager, buzzPoints, isAnswerer, answererName }) {
  return (
    <p className="text-xs text-ui-faint">
      <span className="font-mono text-ui-ink">{wager}</span> on it for{' '}
      {isAnswerer ? 'you' : answererName}
      {' · '}
      <span className="font-mono text-ui-ink">{buzzPoints}</span> to whoever takes it
    </p>
  );
}

// Ambient, and therefore one line at the foot: how many answers are loaded,
// and who has already spent their shot. Neither is an instruction, so neither
// belongs anywhere near the one that is.
function AnswerMargin({ lockedCount, spent }) {
  const bits = [];
  if (lockedCount > 0) bits.push(`${lockedCount} locked and ready`);
  if (spent.length > 0) {
    // Every entry says what happened. A bare name used to mean "answered and
    // got it wrong" purely by implication — the only outcome with no label —
    // which reads as an unexplained name in a list of explained ones. In the
    // ANSWER phase a spent attempt that neither passed nor timed out can only
    // be a wrong answer; a correct one would have ended the question.
    bits.push(
      spent
        .map((a) => `${a.name} (${a.passed ? 'passed' : a.timedOut ? 'froze' : 'missed'})`)
        .join(', ')
    );
  }
  if (bits.length === 0) return null;
  return <p className="text-xs text-ui-faint">{bits.join(' · ')}</p>;
}

// Flow B (GAME_DESIGN.md → "The Round Loop"). Three windows inside one
// phase: everyone reads, then the answerer has their own question to
// themselves, then the buzzer opens to the room.
//
// The two boundaries arrive as timestamps and are compared against the local
// clock on a 250ms tick — the server only pushes state when something
// changes, so a countdown derived server-side would freeze between pushes.
//
// LAYOUT follows the owner's playtest note ("too much going on… I read, I
// answer"), so the screen is three zones and never more: the question, then
// ONE instruction with ONE clock, then the controls that instruction refers
// to. Everything else — the stake, the locked count, who has already gone —
// is chrome and sits below the fold of attention, stated once each.
function OpenAnswerPhase({ game, myId, socket }) {
  const [answer, setAnswer] = useState('');
  const [inputMode, setInputMode] = useState('text');
  const [now, setNow] = useState(Date.now());
  const [actionError, setActionError] = useState(null);
  const autoLocked = useRef(false);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const answerer = game.players[game.answererIndex];
  const isAnswerer = game.iAmAnswerer ?? answerer.id === myId;
  const readingLeft = Math.max(0, Math.ceil(((game.answerOpensAt ?? 0) - now) / 1000));
  const exclusiveLeft = Math.max(0, Math.ceil(((game.buzzOpensAt ?? 0) - now) / 1000));
  const lockLeft = Math.max(0, Math.ceil(((game.lockClosesAt ?? 0) - now) / 1000));
  const reading = readingLeft > 0;
  const exclusive = !reading && exclusiveLeft > 0;
  const spent = game.spentAttempts ?? [];

  // The answerer types a live answer; everyone else types a commitment they
  // may never get to play. Same box, different verb — the server rejects
  // whichever one isn't yours, this only keeps it off screen.
  const canAnswer = !reading && isAnswerer && game.iCanAnswer;
  const canLock = !reading && lockLeft > 0 && game.iCanLock;
  const canBuzz = !reading && !exclusive && game.iCanBuzz;
  const canType = canAnswer || canLock;

  const submit = () => {
    if (!canAnswer || !answer.trim()) return;
    socket.emit('turn:submitAnswer', { answer, inputMode });
    setAnswer('');
  };

  const lockIn = (text = answer) => {
    if (!text.trim()) return;
    socket.emit('turn:lockAnswer', { answer: text, inputMode }, (res) => {
      if (res && res.ok === false) setActionError(res.message);
    });
  };

  // Nobody should lose a question to a missing button press. If there's text
  // in the box when locking is about to close, commit it — the deadline is
  // meant to stop late answers, not to punish someone who typed one in time
  // and didn't tap.
  useEffect(() => {
    if (autoLocked.current || !game.iCanLock || !answer.trim()) return;
    if (now < (game.lockClosesAt ?? 0) - 400) return;
    if (now >= (game.lockClosesAt ?? 0)) return;
    autoLocked.current = true;
    lockIn(answer);
  });

  const buzz = () => {
    socket.emit('turn:buzzIn', {}, (res) => {
      if (res && res.ok === false) setActionError(res.message);
    });
  };

  const pass = () => {
    socket.emit('turn:passAnswer', {}, (res) => {
      if (res && res.ok === false) setActionError(res.message);
    });
  };

  // Exactly one of these is live at a time, which is the whole point of the
  // rewrite: the screen shows one instruction, so it has to be computed as one
  // value rather than as a stack of `&&` blocks that merely happened not to
  // overlap. The ordering is the priority order — what YOU can do beats what
  // is being done to you.
  let status = null;
  let outMessage = null;

  if (reading) {
    status = { verb: 'Read it', seconds: readingLeft };
  } else if (canAnswer) {
    status = exclusive
      ? {
          verb: 'Your shot',
          seconds: exclusiveLeft,
          note: game.iCanPass ? 'Passing costs you nothing' : null,
        }
      : // The exclusive window is over and they still haven't answered: there
        // is no clock that belongs to them any more, so printing one would be
        // a lie. What changed is who they are racing.
        { verb: 'Your shot', seconds: null, note: 'The room can take it now' };
  } else if (canLock) {
    status = { verb: 'Lock one in', seconds: lockLeft, note: 'No lock, no buzz' };
  } else if (canBuzz) {
    status = { verb: 'Buzzers open', seconds: null };
  } else if (exclusive) {
    status = {
      verb: `${answerer.name}'s shot`,
      seconds: exclusiveLeft,
      note: game.myLockedAnswer ? `Locked: “${game.myLockedAnswer}”` : null,
    };
  } else {
    outMessage = game.myAttempt?.passed
      ? 'You passed — it belongs to the room now.'
      : game.myAttempt?.timedOut
      ? `Your window closed without an answer — that's ${game.currentWager} gone.`
      : game.myAttempt
      ? `You played “${game.myAttempt.answer}” — not it.`
      : game.myLockedAnswer
      ? 'Locked in — waiting for the buzzer.'
      : "You didn't lock one in — this one's out of your hands.";
  }

  return (
    <div className="space-y-4 text-center">
      {/* The host, then the question. Quip and heckle are flavour and now read
          as flavour: one small muted line above the question rather than two
          full-size paragraphs competing with it. */}
      {(game.hostQuip || game.heckleMessage) && (
        <p className="text-sm text-ui-faint">
          {game.heckleMessage && (
            <span className="italic text-ui-ink">
              Heckle: &ldquo;{game.heckleMessage}&rdquo;{' '}
            </span>
          )}
          {game.hostQuip}
        </p>
      )}

      {game.rebus ? (
        <RebusPuzzle rebus={game.rebus} />
      ) : (
        // Light and generous rather than heavy bold (item 40): the plate under
        // it carries the legibility, so the question does not have to shout to
        // be the biggest thing on screen.
        //
        // Printed in the green for its wager tier — palest for the easiest
        // question, deepest for the hardest. See lib/difficultyColors.js: every
        // step of that ramp was contrast-checked against the slate GROUND,
        // which is exactly what the plate beneath it now is, so the measured
        // number and the rendered pixel finally describe the same thing.
        <p
          className="text-2xl font-light leading-snug"
          style={{ color: difficultyColor(game.difficultyTier) }}
        >
          {game.question}
        </p>
      )}

      {status ? (
        <AnswerStatus {...status} />
      ) : (
        <p className="text-sm text-ui-faint">{outMessage}</p>
      )}

      {canType && (
        <div className="space-y-2">
          <div className="flex gap-2">
            {/* min-w-0 is load-bearing, not tidying: a flex item defaults to
                `min-width: auto`, so `flex-1` alone will not let an <input>
                shrink below its intrinsic size (~20 characters). At 390px that
                pushed the button 22px off the right edge — and only on the
                answerer's screen, because "Submit" is one word and cannot wrap
                its way out of the squeeze the way "Lock It In" does. */}
            <input
              autoFocus
              className="field min-w-0 flex-1"
              placeholder={canLock ? 'Your answer, ready to go…' : 'Your answer…'}
              value={answer}
              onChange={(e) => {
                setAnswer(e.target.value);
                setInputMode('text');
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') canAnswer ? submit() : lockIn();
              }}
            />
            <VoiceInput
              onTranscript={(transcript) => {
                setAnswer(transcript);
                setInputMode('voice');
              }}
            />
            <button
              className="act"
              disabled={!answer.trim()}
              onClick={() => (canAnswer ? submit() : lockIn())}
            >
              {canAnswer ? 'Submit' : 'Lock It In'}
            </button>
          </div>

          {/* Folding is a real move — with a big wager on a category you don't
              know, handing it to the room is legitimate play, and it's the
              only way out of the wager that costs nothing. */}
          {canAnswer && exclusive && game.iCanPass && (
            <button className="act text-sm" onClick={pass}>
              Pass — throw it to the room
            </button>
          )}
        </div>
      )}

      {/* One tap, no typing. The decision was made when the answer was locked
          in; this is only about whether you dare play it first. */}
      {canBuzz && (
        // The biggest action on the screen, and still an action box: gold
        // outline, Act fill under the finger. It used to be solid red — but
        // red is "negative", and buzzing is the one thing here worth doing.
        <button className="act w-full py-6 text-2xl font-bold" onClick={buzz}>
          BUZZ — &ldquo;{game.myLockedAnswer}&rdquo;
        </button>
      )}

      {actionError && <p className="text-sm text-ui-negative">{actionError}</p>}

      <StakeLine
        wager={game.currentWager}
        buzzPoints={game.buzzPoints}
        isAnswerer={isAnswerer}
        answererName={answerer.name}
      />
      <AnswerMargin lockedCount={game.lockedCount ?? 0} spent={spent} />
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
  const timer = game.roundRule.timerSeconds;

  const submit = () => socket.emit('turn:submitAnswer', { answer, inputMode });
  const remaining = game.totalToSubmit - game.submittedCount;

  return (
    <div className="space-y-3 text-center">
      {game.hostQuip && <p className="text-sm text-ui-faint">{game.hostQuip}</p>}
      <p className="text-lg font-semibold">{game.question}</p>
      <p className="text-sm text-ui-faint">
        Wager: {game.currentWager} · {timer}s · Everyone submits an answer that&apos;s confidently wrong!
      </p>

      {/* Two states, two shapes: your answer is settled (a stamp), the room is
          still filling in (a live notice that goes the moment it is full). */}
      {game.mySubmitted ? (
        <div className="space-y-3">
          <span className="stamp">Answer locked in</span>
          {remaining > 0 && (
            <LiveNotice>
              Waiting for {remaining} more player{remaining === 1 ? '' : 's'} ({game.submittedCount}/
              {game.totalToSubmit} in)
            </LiveNotice>
          )}
        </div>
      ) : (
        <div className="flex gap-2">
          <input
            className="field min-w-0 flex-1"
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
          <button className="act" disabled={!answer.trim()} onClick={submit}>
            Lock In
          </button>
        </div>
      )}
    </div>
  );
}

// The Lineup: anyone may tap any option, any number of times, until someone
// gets it right or the timer runs out. Wrong taps get a brief red flash via
// the ack callback (server doesn't broadcast on a wrong guess — see
// server.js) rather than a real error, since being wrong here is the
// expected common case, not a failure.
function LineupPhase({ game, socket }) {
  const [wrongId, setWrongId] = useState(null);
  const timer = game.roundRule.timerSeconds;
  const isColor = game.lineup?.flavor === 'color';

  const pick = (optionId) => {
    socket.emit('turn:attemptLineup', { optionId }, (res) => {
      if (res && res.correct === false) {
        setWrongId(optionId);
        setTimeout(() => setWrongId((cur) => (cur === optionId ? null : cur)), 500);
      }
    });
  };

  return (
    <div className="space-y-3 text-center">
      {game.hostQuip && <p className="text-sm text-ui-faint">{game.hostQuip}</p>}
      <p className="text-lg font-semibold">{game.question}</p>
      <p className="text-sm text-ui-faint">
        Wager: {game.currentWager} · {timer}s · Anyone can tap — first correct pick wins!
      </p>

      <div className="space-y-2">
        {game.lineup?.options.map((opt, i) => (
          <button
            key={opt.id}
            onClick={() => pick(opt.id)}
            // Whole row is the hit target (§5). A wrong tap flashes the
            // negative outline for half a second and nothing else — being
            // wrong here is the common case, not an error.
            className={`choice flex w-full items-center gap-3 px-3 py-2 text-left ${
              wrongId === opt.id ? '!border-ui-negative' : ''
            }`}
          >
            <span className="font-mono text-sm text-ui-faint">{i + 1}.</span>
            {isColor ? (
              <span className="h-10 flex-1" style={{ backgroundColor: opt.hex }} />
            ) : (
              <span>{opt.label}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function ResultPhase({ game }) {
  if (game.skippedTurn) {
    // Skip is a card, so somebody played it — say who (§3f).
    const skipper = game.cardSlot
      ? game.players.find((p) => p.id === game.cardSlot.playerId)?.name
      : null;
    return (
      <p className="text-center text-xl">
        {skipper ? `${skipper} played Skip — turn skipped` : 'Turn skipped'}
      </p>
    );
  }
  const result = game.lastResult;

  if (result.submissionBased) {
    return <WorstAnswerResults game={game} result={result} />;
  }

  if (result.lineupWinner !== undefined) {
    return <LineupResults game={game} result={result} />;
  }

  const answerer = game.players[game.answererIndex];
  const answererName = answerer?.name ?? 'the answerer';
  // A fold and a freeze both end with the answerer not answering, but only
  // one of them costs the wager — so the headline must not report them the
  // same way. `wagerLost` is the server's own record of which happened.
  const headline = result.buzzedIn
    ? `${result.winnerName} buzzed in and took it! +${result.points}`
    : result.correct
    ? `${result.winnerName ?? 'Correct'}! +${result.points}`
    : result.wagerLost
    ? `Nobody got it — ${answererName} drops ${result.wager}`
    : result.activeOutcome === 'passed'
    ? `${answererName} passed — and nobody else got it either`
    : 'Nobody got it.';

  // Only alongside a buzz-in win: otherwise the headline has already said it,
  // and saying it twice reads as a bug rather than as emphasis.
  const asideForActive = !result.buzzedIn
    ? null
    : result.activeOutcome === 'passed'
      ? `${answererName} passed on ${result.wager} — it cost them nothing.`
      : result.activeOutcome === 'timedOut'
      ? `${answererName} never answered — ${result.wager} gone.`
      : null;

  // Every attempt, so the room sees who swung and missed — that's the part
  // people talk about, and it's invisible if only the winner is shown.
  const misses = (result.attempts ?? []).filter((a) => !a.correct && a.answer);

  return (
    <div className="space-y-2 text-center">
      <p className={`text-2xl font-bold ${result.correct ? 'text-ui-positive' : 'text-ui-negative'}`}>
        {headline}
      </p>
      {asideForActive && <p className="text-sm text-ui-faint">{asideForActive}</p>}
      {game.rebus ? (
        <RebusReveal rebus={game.rebus} answer={game.answer} />
      ) : (
        <CorrectAnswer answer={game.answer} />
      )}
      {result.feedback && <p>{result.feedback}</p>}
      {misses.length > 0 && (
        <div className="pt-2 text-sm text-ui-faint">
          {misses.map((a) => (
            <p key={a.playerId}>
              <span className="text-ui-ink">{a.name}</span> played &ldquo;{unquote(a.answer)}&rdquo;
            </p>
          ))}
        </div>
      )}

      {/* The answers nobody got to play. This is the loudest moment the
          lock-in mechanic produces — somebody in the room had it and sat on
          it, and only the reveal tells them so. */}
      {(result.unplayedAnswers ?? []).length > 0 && (
        <div className="pt-2 text-sm text-ui-faint">
          <p className="text-xs uppercase tracking-widest">Never played</p>
          {result.unplayedAnswers.map((a) => (
            <p key={a.playerId}>
              <span className="text-ui-ink">{a.name}</span> had &ldquo;{unquote(a.answer)}&rdquo;
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// The Lineup result: either someone spotted it first, or the timer ran out
// unclaimed. Reveals the correct option (swatch for color flavor, label for
// text) alongside the rest of the lineup.
function LineupResults({ game, result }) {
  return (
    <div className="space-y-3 text-center">
      {result.lineupWinner ? (
        <p className="text-2xl font-bold text-ui-positive">
          {result.winnerName} spotted it! +{result.wager}
        </p>
      ) : (
        <p className="text-2xl font-bold text-ui-negative">
          Nobody spotted it — {result.wager} pts unclaimed!
        </p>
      )}
      <CorrectAnswer answer={game.answer} />

      <div className="space-y-2">
        {game.lineup?.options.map((opt, i) => {
          const isCorrect = opt.id === result.correctOptionId;
          return (
            <div
              key={opt.id}
              className={`flex items-center gap-3 border-2 bg-ui-surface px-3 py-2 ${
                isCorrect ? 'border-ui-positive' : 'border-transparent'
              }`}
            >
              <span className="font-mono text-sm text-ui-faint">{i + 1}.</span>
              {opt.hex ? (
                <span className="h-10 flex-1" style={{ backgroundColor: opt.hex }} />
              ) : (
                <span className="flex-1 text-left">{opt.label}</span>
              )}
              {isCorrect && <span className="font-bold text-ui-positive">✓</span>}
            </div>
          );
        })}
      </div>
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
      {winners && (
        <p className="text-2xl font-bold text-ui-positive">
          {winners} nailed it! +{result.wager}
        </p>
      )}
      <CorrectAnswer answer={game.answer} />
      <p className="text-sm text-ui-faint">Lowest total score wins</p>

      <div className="space-y-2 text-left">
        {sorted.map((entry) => (
          <div
            key={entry.playerId}
            className={`border-2 bg-ui-surface p-3 ${
              entry.isWinner ? 'border-ui-chosen' : 'border-transparent'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold">
                {entry.name}
                {entry.isWinner && <span className="stamp ml-2 px-2 py-0 text-xs">Winner</span>}
              </span>
              <span className="font-mono text-sm text-ui-faint">Total: {entry.total}/30</span>
            </div>
            {/* Quote marks only around words somebody actually said (§3c). The
                "no answer" placeholder used to sit inside quotes too, which
                put words in the mouth of a player who said nothing. */}
            {entry.answer?.trim() ? (
              <p className="mt-1 text-sm italic">&ldquo;{unquote(entry.answer)}&rdquo;</p>
            ) : (
              <p className="mt-1 text-sm text-ui-faint">No answer submitted</p>
            )}
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ui-faint">
              <span>Factually wrong: {entry.factuallyWrong}/10</span>
              <span>Creatively wrong: {entry.creativelyWrong}/10</span>
              <span>Plausibility: {entry.plausibility}/10</span>
            </div>
            {entry.feedback && <p className="mt-2 text-sm">{entry.feedback}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
