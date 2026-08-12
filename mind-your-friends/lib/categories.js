// Tappable category suggestions for the lobby.
//
// Typing five categories was the most laborious moment in the whole game
// (playtest, Aug 12). The fix is two-part: three categories instead of five
// (CATEGORIES_PER_PLAYER), and a grid of these to tap so most players never
// type at all. "Enter your own" stays, because personal in-jokes are the
// point of category attribution — a question credited to "Bob's Divorce" is
// funnier than anything on this list, and attribution is a designed beat.
//
// Hardcoded on purpose: generating suggestions per lobby would cost a Claude
// call and re-introduce the very lobby wait we just removed. These names are
// also chosen to be ones the fact-bank prompt handles well — broad enough
// that ten real factoids exist, narrow enough that they aren't vague.
//
// Grouped only for display; the game treats every category identically.
export const CATEGORY_SUGGESTIONS = [
  {
    group: 'Screen',
    items: ['90s Movies', 'Horror Films', 'Animated Classics', 'Prestige TV', 'Reality TV', 'Superhero Movies'],
  },
  {
    group: 'Sound',
    items: ['Pop Music', '90s Hip Hop', 'Classic Rock', 'Musicals', 'One-Hit Wonders', 'Taylor Swift'],
  },
  {
    group: 'World',
    items: ['Geography', 'Ancient History', 'Space', 'Animals', 'Food & Drink', 'Famous Disasters'],
  },
  {
    group: 'Play',
    items: ['Video Games', 'Board Games', 'Football', 'The Olympics', 'Formula 1', 'Card Games'],
  },
  {
    group: 'Everything Else',
    items: ['Internet Culture', 'Fashion', 'Cars', 'True Crime', 'Science', 'Mythology'],
  },
];

// Flat list, for validation and tests.
export const ALL_SUGGESTED_CATEGORIES = CATEGORY_SUGGESTIONS.flatMap((g) => g.items);
