// Rebus round data: a library of reusable PIECES, plus PUZZLES that are
// nothing but lists of piece keys.
//
// Why a piece library rather than self-contained puzzles: the same atoms
// recur constantly (MAN appears in six puzzles here, SUN in four), so keying
// them means one emoji choice per concept instead of one per puzzle, and a
// piece improved in one place improves everywhere it's used. It also gives
// any future generation path a fixed vocabulary to compose from — which is
// the whole reliability problem with AI-built rebuses. Asking Claude for
// "a rebus for Sherman" gets plausible-looking pieces that don't reconstruct
// the word; asking it to pick from a known piece list can be validated
// mechanically before a player ever sees it.
//
// Nothing here costs an API call. Same reasoning as lineupData.js's colour
// table: a rebus that doesn't decompose is unsolvable, and a room can't tell
// "we're stupid" from "the game is broken". Curated content removes that
// class of failure entirely rather than trying to catch it at runtime.

// key -> { emoji, reads }. `reads` is what the piece stands for when the
// puzzle is read aloud; it's shown in the answer reveal so the "ohhh" lands.
//
// A few emoji appear under two keys on purpose (🦶 is both FOOT and TOE, 🎵
// is both NOTE and TUNE, 💧 is both WATER and DROP). That ambiguity is normal
// rebus grammar — the solver resolves it from what makes a word — but it does
// mean a puzzle shouldn't lean on the reading being obvious in isolation.
export const REBUS_PIECES = {
  sun: { emoji: '☀️', reads: 'SUN' },
  moon: { emoji: '🌙', reads: 'MOON' },
  star: { emoji: '⭐', reads: 'STAR' },
  rain: { emoji: '🌧️', reads: 'RAIN' },
  snow: { emoji: '❄️', reads: 'SNOW' },
  fire: { emoji: '🔥', reads: 'FIRE' },
  ice: { emoji: '🧊', reads: 'ICE' },
  water: { emoji: '💧', reads: 'WATER' },
  sea: { emoji: '🌊', reads: 'SEA' },
  cloud: { emoji: '☁️', reads: 'CLOUD' },
  storm: { emoji: '🌩️', reads: 'STORM' },
  lightning: { emoji: '⚡', reads: 'LIGHTNING' },
  night: { emoji: '🌃', reads: 'NIGHT' },
  land: { emoji: '🏞️', reads: 'LAND' },
  forest: { emoji: '🌲', reads: 'FOREST' },

  man: { emoji: '🧑', reads: 'MAN' },
  boy: { emoji: '👦', reads: 'BOY' },
  lady: { emoji: '👩', reads: 'LADY' },
  monk: { emoji: '🧎', reads: 'MONK' },
  writer: { emoji: '✍️', reads: 'WRITER' },
  fisher: { emoji: '🎣', reads: 'FISHER' },
  ghost: { emoji: '👻', reads: 'GHOST' },
  spider: { emoji: '🕷️', reads: 'SPIDER' },
  bat: { emoji: '🦇', reads: 'BAT' },
  brain: { emoji: '🧠', reads: 'BRAIN' },
  eye: { emoji: '👁️', reads: 'EYE' },
  ear: { emoji: '👂', reads: 'EAR' },
  foot: { emoji: '🦶', reads: 'FOOT' },
  toe: { emoji: '🦶', reads: 'TOE' },
  hand: { emoji: '✋', reads: 'HAND' },
  tooth: { emoji: '🦷', reads: 'TOOTH' },
  heart: { emoji: '❤️', reads: 'HEART' },

  bee: { emoji: '🐝', reads: 'BEE' },
  cat: { emoji: '🐈', reads: 'CAT' },
  dog: { emoji: '🐕', reads: 'DOG' },
  pet: { emoji: '🐕', reads: 'PET' },
  cow: { emoji: '🐄', reads: 'COW' },
  horse: { emoji: '🐴', reads: 'HORSE' },
  mare: { emoji: '🐎', reads: 'MARE' },
  fish: { emoji: '🐟', reads: 'FISH' },
  bird: { emoji: '🐦', reads: 'BIRD' },
  fox: { emoji: '🦊', reads: 'FOX' },
  rat: { emoji: '🐀', reads: 'RAT' },
  bug: { emoji: '🐛', reads: 'BUG' },
  worm: { emoji: '🪱', reads: 'WORM' },
  fly: { emoji: '🪰', reads: 'FLY' },
  lion: { emoji: '🦁', reads: 'LION' },

  flower: { emoji: '🌼', reads: 'FLOWER' },
  plant: { emoji: '🌱', reads: 'PLANT' },
  mushroom: { emoji: '🍄', reads: 'MUSHROOM' },
  leaf: { emoji: '🍃', reads: 'LEAF' },
  weed: { emoji: '🌿', reads: 'WEED' },
  corn: { emoji: '🌽', reads: 'CORN' },
  apple: { emoji: '🍏', reads: 'APPLE' },
  melon: { emoji: '🍈', reads: 'MELON' },

  egg: { emoji: '🥚', reads: 'EGG' },
  butter: { emoji: '🧈', reads: 'BUTTER' },
  honey: { emoji: '🍯', reads: 'HONEY' },
  milk: { emoji: '🥛', reads: 'MILK' },
  dough: { emoji: '🍩', reads: 'DOUGH' },
  pie: { emoji: '🥧', reads: 'PIE' },
  cake: { emoji: '🎂', reads: 'CAKE' },
  pan: { emoji: '🍳', reads: 'PAN' },
  cup: { emoji: '🥤', reads: 'CUP' },
  tea: { emoji: '🍵', reads: 'TEA' },
  food: { emoji: '🍔', reads: 'FOOD' },
  cream: { emoji: '🍦', reads: 'CREAM' },
  hot: { emoji: '🥵', reads: 'HOT' },

  house: { emoji: '🏠', reads: 'HOUSE' },
  wall: { emoji: '🧱', reads: 'WALL' },
  place: { emoji: '📍', reads: 'PLACE' },
  book: { emoji: '📖', reads: 'BOOK' },
  key: { emoji: '🔑', reads: 'KEY' },
  board: { emoji: '🛹', reads: 'BOARD' },
  ball: { emoji: '⚽', reads: 'BALL' },
  shoe: { emoji: '👟', reads: 'SHOE' },
  coat: { emoji: '🧥', reads: 'COAT' },
  glasses: { emoji: '👓', reads: 'GLASSES' },
  ring: { emoji: '💍', reads: 'RING' },
  bow: { emoji: '🎀', reads: 'BOW' },
  tie: { emoji: '👔', reads: 'TIE' },
  bag: { emoji: '👜', reads: 'BAG' },
  pipe: { emoji: '🚬', reads: 'PIPE' },
  nail: { emoji: '🔨', reads: 'NAIL' },
  brush: { emoji: '🖌️', reads: 'BRUSH' },
  log: { emoji: '🪵', reads: 'LOG' },
  shell: { emoji: '🐚', reads: 'SHELL' },
  sword: { emoji: '🗡️', reads: 'SWORD' },
  crown: { emoji: '👑', reads: 'KING' },
  print: { emoji: '🖨️', reads: 'PRINT' },
  light: { emoji: '💡', reads: 'LIGHT' },
  car: { emoji: '🚗', reads: 'CAR' },
  way: { emoji: '🛣️', reads: 'WAY' },
  pool: { emoji: '🏊', reads: 'POOL' },
  walk: { emoji: '🚶', reads: 'WALK' },
  rise: { emoji: '📈', reads: 'RISE' },
  fall: { emoji: '🍂', reads: 'FALL' },
  drop: { emoji: '💧', reads: 'DROP' },
  dust: { emoji: '💨', reads: 'DUST' },
  beat: { emoji: '🥁', reads: 'BEAT' },
  tune: { emoji: '🎵', reads: 'TUNE' },
  note: { emoji: '🎵', reads: 'NOTE' },
  burn: { emoji: '🔥', reads: 'BURN' },
  post: { emoji: '📮', reads: 'POST' },
  gold: { emoji: '🥇', reads: 'GOLD' },
  black: { emoji: '⬛', reads: 'BLACK' },
  green: { emoji: '🟢', reads: 'GREEN' },
  loo: { emoji: '🚽', reads: 'LOO' },
  nation: { emoji: '🏳️', reads: 'NATION' },
  sure: { emoji: '💯', reads: 'SURE' },
  two: { emoji: '2️⃣', reads: 'TWO' },
  four: { emoji: '4️⃣', reads: 'FOUR' },
  lips: { emoji: '👄', reads: 'LIPS' },
};

// Puzzles are piece keys plus the answer and a one-line hint. The hint keeps
// this trivia rather than pure wordplay — without it a rebus is a guessing
// game with no way in.
//
// `phonetic: true` means the pieces SOUND like the answer rather than
// spelling it. That distinction is load-bearing, not decorative: the test
// suite checks every non-phonetic puzzle reconstructs its answer exactly,
// letter for letter, so a typo can't ship. Phonetic ones opt out of that
// check, which is why each has to be marked deliberately.
export const REBUS_PUZZLES = [
  // --- Literal: the pieces spell the answer ---
  { answer: 'Sunflower', hint: 'A tall yellow bloom that tracks the sky', pieces: ['sun', 'flower'] },
  { answer: 'Starfish', hint: 'Five arms, no brain, lives in a tide pool', pieces: ['star', 'fish'] },
  { answer: 'Moonlight', hint: 'What you read by when the power is out', pieces: ['moon', 'light'] },
  { answer: 'Butterfly', hint: 'It used to be a caterpillar', pieces: ['butter', 'fly'] },
  { answer: 'Horseshoe', hint: 'Lucky if you nail it above a door', pieces: ['horse', 'shoe'] },
  { answer: 'Eggplant', hint: 'Purple, and a divisive emoji', pieces: ['egg', 'plant'] },
  { answer: 'Rainbow', hint: 'Seven colours, no pot of gold included', pieces: ['rain', 'bow'] },
  { answer: 'Brainstorm', hint: 'A meeting where every idea is a good idea', pieces: ['brain', 'storm'] },
  { answer: 'Birdhouse', hint: 'Tiny real estate, nailed to a pole', pieces: ['bird', 'house'] },
  { answer: 'Seahorse', hint: 'The father carries the babies', pieces: ['sea', 'horse'] },
  { answer: 'Sunglasses', hint: 'Worn indoors by people being mysterious', pieces: ['sun', 'glasses'] },
  { answer: 'Honeymoon', hint: 'Where you go straight after the wedding', pieces: ['honey', 'moon'] },
  { answer: 'Firefox', hint: 'A browser named after a red panda', pieces: ['fire', 'fox'] },
  { answer: 'Ghostwriter', hint: 'Wrote the celebrity memoir, got no cover credit', pieces: ['ghost', 'writer'] },
  { answer: 'Snowman', hint: 'Two lumps of coal and a carrot', pieces: ['snow', 'man'] },
  { answer: 'Fisherman', hint: 'Famous for exaggerating a size', pieces: ['fisher', 'man'] },
  { answer: 'Apple pie', hint: 'As American as', pieces: ['apple', 'pie'] },
  { answer: 'Mushroom cloud', hint: 'The shape nobody wants to see on the horizon', pieces: ['mushroom', 'cloud'] },
  { answer: 'Lightning bug', hint: 'Summer evenings in a jar', pieces: ['lightning', 'bug'] },
  { answer: 'Watermelon', hint: '92% of the thing it is named after', pieces: ['water', 'melon'] },
  { answer: 'Iceland', hint: 'Greener than the one called Green', pieces: ['ice', 'land'] },
  { answer: 'Cornwall', hint: 'England kicking its foot into the Atlantic', pieces: ['corn', 'wall'] },
  { answer: 'Cowboy', hint: 'Yeehaw', pieces: ['cow', 'boy'] },
  { answer: 'Fireman', hint: 'Slides down a pole to go to work', pieces: ['fire', 'man'] },
  { answer: 'Spiderman', hint: 'Bitten, and it worked out well', pieces: ['spider', 'man'] },
  { answer: 'Batman', hint: 'His superpower is being rich', pieces: ['bat', 'man'] },
  { answer: 'Postman', hint: 'Natural enemy of the dog', pieces: ['post', 'man'] },
  { answer: 'Raincoat', hint: 'Yellow, in every childhood photo', pieces: ['rain', 'coat'] },
  { answer: 'Snowball', hint: 'Effects are named after it rolling downhill', pieces: ['snow', 'ball'] },
  { answer: 'Football', hint: 'Depends entirely which country you ask', pieces: ['foot', 'ball'] },
  { answer: 'Keyboard', hint: 'QWERTY', pieces: ['key', 'board'] },
  { answer: 'Seashell', hint: 'Hold it up and hear the ocean', pieces: ['sea', 'shell'] },
  { answer: 'Toothbrush', hint: 'Replace it every three months, allegedly', pieces: ['tooth', 'brush'] },
  { answer: 'Raindrop', hint: 'Keeps falling on my head', pieces: ['rain', 'drop'] },
  { answer: 'Sunrise', hint: 'Worth setting an alarm for, once', pieces: ['sun', 'rise'] },
  { answer: 'Moonwalk', hint: 'Michael Jackson going backwards', pieces: ['moon', 'walk'] },
  { answer: 'Catfish', hint: 'Whiskers, or a fake dating profile', pieces: ['cat', 'fish'] },
  { answer: 'Doghouse', hint: 'Where you sleep after forgetting the anniversary', pieces: ['dog', 'house'] },
  { answer: 'Bookworm', hint: 'Reads at parties', pieces: ['book', 'worm'] },
  { answer: 'Eyeball', hint: 'You have two, hopefully', pieces: ['eye', 'ball'] },
  { answer: 'Heartbeat', hint: 'About 100,000 a day', pieces: ['heart', 'beat'] },
  { answer: 'Cupcake', hint: 'A muffin that went to finishing school', pieces: ['cup', 'cake'] },
  { answer: 'Pancake', hint: 'Flat, stacked, drowned in syrup', pieces: ['pan', 'cake'] },
  { answer: 'Rainforest', hint: 'Lungs of the planet', pieces: ['rain', 'forest'] },
  { answer: 'Fireplace', hint: 'Stockings hung here with care', pieces: ['fire', 'place'] },
  { answer: 'Stardust', hint: 'What Carl Sagan said we are made of', pieces: ['star', 'dust'] },
  { answer: 'Seafood', hint: 'A menu section, and an allergy', pieces: ['sea', 'food'] },
  { answer: 'Nightmare', hint: 'Wakes you at 3am', pieces: ['night', 'mare'] },
  { answer: 'Handbook', hint: 'Nobody read it', pieces: ['hand', 'book'] },
  { answer: 'Bowtie', hint: 'Formal, and favoured by one Doctor', pieces: ['bow', 'tie'] },
  { answer: 'Ladybug', hint: 'Spots, and good luck', pieces: ['lady', 'bug'] },
  { answer: 'Swordfish', hint: 'Comes with its own weapon', pieces: ['sword', 'fish'] },
  { answer: 'Footprint', hint: 'Neil Armstrong left one that is still there', pieces: ['foot', 'print'] },
  { answer: 'Sunburn', hint: 'The souvenir of a good holiday', pieces: ['sun', 'burn'] },
  { answer: 'Teacup', hint: 'A small storm happens in it', pieces: ['tea', 'cup'] },
  { answer: 'Lighthouse', hint: 'Lonely job, great view', pieces: ['light', 'house'] },
  { answer: 'Waterfall', hint: 'Niagara, Angel, Victoria', pieces: ['water', 'fall'] },
  { answer: 'Goldfish', hint: 'Three-second memory is a myth', pieces: ['gold', 'fish'] },
  { answer: 'Blackboard', hint: 'The squeak everyone hates', pieces: ['black', 'board'] },
  { answer: 'Greenhouse', hint: 'Warm, glass, and an effect', pieces: ['green', 'house'] },
  { answer: 'Seaweed', hint: 'Wraps your sushi', pieces: ['sea', 'weed'] },
  { answer: 'Icecream', hint: 'You scream, apparently', pieces: ['ice', 'cream'] },
  { answer: 'Earring', hint: 'Comes in pairs, lost one at a time', pieces: ['ear', 'ring'] },
  { answer: 'Toenail', hint: 'Clipped over a bin, ideally', pieces: ['toe', 'nail'] },
  { answer: 'Carpool', hint: 'James Corden made karaoke of it', pieces: ['car', 'pool'] },
  { answer: 'Bagpipe', hint: 'Banned as a weapon of war, supposedly', pieces: ['bag', 'pipe'] },
  { answer: 'Hotdog', hint: 'Is it a sandwich? Discuss', pieces: ['hot', 'dog'] },
  { answer: 'Notebook', hint: 'A Nicholas Sparks weepie', pieces: ['note', 'book'] },
  { answer: 'Lion King', hint: 'Hakuna matata', pieces: ['lion', 'crown'] },

  // --- Phonetic: the pieces SOUND like the answer ---
  { answer: 'Sherman', hint: 'Union general who marched to the sea', pieces: ['sure', 'man'], phonetic: true },
  { answer: 'Belief', hint: 'What you hold without proof', pieces: ['bee', 'leaf'], phonetic: true },
  { answer: 'Donkey', hint: 'Shrek travels with one', pieces: ['dough', 'key'], phonetic: true },
  { answer: 'Monkey', hint: 'Infinite ones, infinite typewriters', pieces: ['monk', 'key'], phonetic: true },
  { answer: 'Pirate', hint: 'Yarr', pieces: ['pie', 'rat'], phonetic: true },
  { answer: 'Carpet', hint: 'It really tied the room together', pieces: ['car', 'pet'], phonetic: true },
  { answer: 'Cartoon', hint: 'Saturday mornings', pieces: ['car', 'tune'], phonetic: true },
  { answer: 'Before', hint: 'The opposite of after', pieces: ['bee', 'four'], phonetic: true },
  { answer: 'Tulips', hint: 'A Dutch financial bubble in 1637', pieces: ['two', 'lips'], phonetic: true },
  { answer: 'Waterloo', hint: 'Napoleon lost here; ABBA won with it', pieces: ['water', 'loo'], phonetic: true },
  { answer: 'Carnation', hint: 'A frilly flower worn in a lapel', pieces: ['car', 'nation'], phonetic: true },
  { answer: 'Catalogue', hint: 'Argos was famous for its laminated one', pieces: ['cat', 'log'], phonetic: true },
  { answer: 'Milky Way', hint: 'You are currently inside it', pieces: ['milk', 'way'], phonetic: true },
];

// Resolves a puzzle's piece keys into renderable pieces. Throws on an unknown
// key rather than rendering a gap — a rebus missing a piece is unsolvable,
// and the tests call this over every puzzle so a bad key can't ship.
export function resolveRebus(puzzle) {
  return puzzle.pieces.map((key) => {
    const piece = REBUS_PIECES[key];
    if (!piece) throw new Error(`Unknown rebus piece: "${key}" (in "${puzzle.answer}")`);
    return { key, emoji: piece.emoji, reads: piece.reads };
  });
}

// Picks a puzzle nobody in this game has seen yet. `usedAnswers` is the
// game's own record, so a single game never repeats one; across games the
// bank recycles freely.
export function pickRebusPuzzle(usedAnswers = []) {
  const fresh = REBUS_PUZZLES.filter((p) => !usedAnswers.includes(p.answer));
  const pool = fresh.length > 0 ? fresh : REBUS_PUZZLES;
  return pool[Math.floor(Math.random() * pool.length)];
}
