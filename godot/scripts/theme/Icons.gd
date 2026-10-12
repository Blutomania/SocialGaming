## Icons — which icon a thing gets, and why it means nothing.
##
## THE RULE (owner, Session 37): the icon sets decorate. They must never be
## read as a signal. Which of the four magnifiers sits beside a clue says
## nothing about that clue, and a player who starts believing the fingerprint
## one means something has been actively misled by the interface.
##
## THE OBVIOUS IMPLEMENTATION IS WRONG IN BOTH DIRECTIONS.
##
##   randi() % size, rolled at draw time, re-rolls on every redraw. The icon
##   beside a clue would change whenever the list rebuilds, which reads as a
##   bug and is genuinely distracting on a screen the player is studying.
##
##   hash(clue_id) % size, the fix people reach for next, is a FIXED MAPPING
##   wearing a costume. The same clue draws the same icon in every game
##   forever, so it is exactly the signal the rule forbids -- and worse, it is
##   a signal random-looking enough that nobody would think to check.
##
## SO: seeded, with the GAME in the seed. Stable for as long as anyone is
## looking at it, and reshuffled between games, which is what makes the
## randomness real rather than a lookup table nobody has noticed yet. Same
## technique background_field.py uses for the mark field, and for the same
## reason -- a reconnecting player should rejoin the screen they left.
##
## The two SETS do differ from one another, and that is intended: a magnifier
## and a speech bubble are different kinds of thing, and the shape carries that
## honestly. It is only the choice WITHIN a set that carries nothing.

class_name Icons
extends RefCounted

## Separates salt from key so ("ab", "c") and ("a", "bc") cannot seed the same
## draw. A space would not do it; this cannot appear in either value.
##
## \u0001 (SOH), written as an ESCAPE, not a literal control byte in the
## source -- a real NUL character sitting between the quotes parses as an
## UNTERMINATED STRING, not as a one-character string containing NUL.
## GDScript's lexer never got a chance to apply the "cannot appear in either
## value" reasoning above; it failed before that, on every load, which is why
## this was never caught by anything that reads source text rather than
## running it. First surfaced Session 42, on the first real F5 this file has
## been part of.
const _SEP: String = "\u0001"


## Pick a clue icon. `key` identifies the thing being decorated (a clue id, an
## evidence id); `salt` should be the game id, so the same key draws a
## different icon in a different game.
static func clue(key: String, salt: String = "") -> String:
	return _pick(IconSet.CLUE, key, salt)


## Pick a witness icon. Same contract as clue().
static func witness(key: String, salt: String = "") -> String:
	return _pick(IconSet.WITNESS, key, salt)


## Pick a suspect icon. Same key/salt contract as clue(), PLUS two optional
## trait filters that the clue/witness sets deliberately have no equivalent
## of: `pronouns` and `presentation`, straight from CharacterData (generation
## writes both -- see server/main.py's characters[] schema). Passing "" for
## either (an older mystery, a field generation omitted) falls back to the
## full unfiltered pool -- was inert until three PNGs landed in icons/suspect/
## and scripts/build_icons.py ran (playtest FindingsSept8); no code change was
## needed to activate it then, and none is needed to keep serving an
## unfiltered pick now, for the same reason: _pick()'s empty-set handling.
##
## THIS IS A DELIBERATE EXCEPTION TO "THE ICON MEANS NOTHING" AT THE TOP OF
## THIS FILE, NOT A VIOLATION OF IT. That rule is about NARRATIVE signal --
## an icon must never hint who did it. Matching a portrait's presented gender
## to a character's actual gender is accuracy, not a tell; it carries no more
## story information than getting a name's spelling right does. Keep that
## distinction if this file's top comment ever gets revised.
static func suspect(key: String, salt: String = "", pronouns: String = "", presentation: String = "") -> String:
	var candidates := _suspect_candidates(pronouns, presentation)
	return _pick(candidates, key, salt)


## she/her -> "feminine", he/him/his -> "masculine", anything else (they/them,
## an invented convention, empty) -> "neutral". Tokenized, not raw substring
## matching -- "he" IS a substring of "they" and "them", so a naive
## `.contains("he")` buckets "they/them" as masculine, which a test caught.
## Split on non-letters first so "they" and "he" are never the same token.
## Loose token matching rather than exact-string comparison for the same
## reason localization's name-map matching uses word-boundary regex: nothing
## enforces the prompt's exact casing or punctuation. "Neutral" is always a
## safe fallback -- an unrecognised pronoun string should degrade gracefully,
## not break icon assignment for a mystery that invented its own convention.
static func _gender_bucket(pronouns: String) -> String:
	var tokens := _words_only(pronouns.to_lower())
	if tokens.has("she") or tokens.has("her") or tokens.has("hers"):
		return "feminine"
	if tokens.has("he") or tokens.has("him") or tokens.has("his"):
		return "masculine"
	return "neutral"


## Split into lowercase letter-only tokens on every run of non-letter
## characters -- "she/her" -> ["she", "her"], "they/them" -> ["they", "them"].
static func _words_only(text: String) -> PackedStringArray:
	var regex := RegEx.new()
	regex.compile("[a-z]+")
	var out := PackedStringArray()
	for m in regex.search_all(text):
		out.append(m.get_string())
	return out


## The candidate pool for suspect(), before _pick() hashes into it.
##
## FALLBACK CHAIN, most to least specific -- each step is allowed to come up
## empty and falls through to the next rather than erroring, which is the
## whole point: a species with no dedicated art yet still resolves to
## SOMETHING today, and automatically gets more precise the day someone tags
## an SVG for it. No code change either way. Same "degrade gracefully, extend
## by content not code" shape as craft_grounding.get_craft_guidance()'s
## confidence-tier filtering -- deliberately, not by coincidence.
##
##   1. presentation != "human": try that exact species tag (e.g. "martian").
##   2. still nothing: try the generic "non-human" tag.
##   3. (human, or no non-human art exists yet): try [gender_bucket, "human"].
##   4. still nothing: the full, unfiltered SUSPECT pool -- always non-empty
##      once any suspect icon exists, so this step is the true floor.
static func _suspect_candidates(pronouns: String, presentation: String) -> Array[String]:
	var pres := presentation.to_lower().strip_edges()

	if not pres.is_empty() and pres != "human":
		var species_specific := _suspect_by_tags([pres])
		if not species_specific.is_empty():
			return species_specific
		var generic_nonhuman := _suspect_by_tags(["non-human"])
		if not generic_nonhuman.is_empty():
			return generic_nonhuman
		# No non-human art tagged yet at all -- fall through to the human
		# pool below rather than return empty. A wrong-but-present icon beats
		# a blank slot; see texture()'s own reasoning for the same trade-off
		# made the other direction (empty set -> draw nothing, not a fault).

	var bucket := _gender_bucket(pronouns)
	var gender_matched := _suspect_by_tags([bucket, "human"])
	if not gender_matched.is_empty():
		return gender_matched

	return IconSet.SUSPECT


## Every SUSPECT path whose IconSet.SUSPECT_TAGS entry contains every tag in
## `required` (AND-match -- two tags per icon today, gender + presentation).
static func _suspect_by_tags(required: Array[String]) -> Array[String]:
	var out: Array[String] = []
	for path in IconSet.SUSPECT_TAGS.keys():
		var tags: Array = IconSet.SUSPECT_TAGS[path]
		var has_all := true
		for t in required:
			if not tags.has(t):
				has_all = false
				break
		if has_all:
			out.append(path)
	return out


## Load a picked icon as a texture, or null when there is nothing to load.
##
## Returns null rather than a placeholder on purpose: an empty set is a
## legitimate state (the sets ship empty until artwork lands in icons/), and a
## screen that draws nothing is correct there, whereas a "missing icon" box
## would be reporting a fault that does not exist.
static func texture(icon_path: String) -> Texture2D:
	if icon_path.is_empty():
		return null
	if not ResourceLoader.exists(icon_path):
		push_warning("Icons: %s is listed in IconSet but is not on disk. " % icon_path
			+ "Run: python3 scripts/build_icons.py")
		return null
	return load(icon_path) as Texture2D


## The generated icons are pure white so that this multiplies cleanly to any
## palette colour -- see scripts/build_icons.py for why Godot recolours by
## modulate while the phone uses currentColor.
static func tint() -> Color:
	return Palette.INK_MUTED


## An empty String when the set has no icons in it yet.
static func _pick(set_paths: Array[String], key: String, salt: String) -> String:
	if set_paths.is_empty():
		return ""
	var seed_text: String = salt + _SEP + key
	var index: int = _mix32(seed_text.hash()) % set_paths.size()
	return set_paths[index]


## Avalanche the hash before taking a modulus of it.
##
## THIS IS NOT DEFENSIVE POLISH -- without it the feature is broken, and a test
## caught it. String.hash() is djb2 (h * 33 + byte), so keys that differ only in
## their last character produce hashes that differ by almost exactly that
## character's value. Taking `% 4` of that reads the low bits, which had barely
## been mixed at all, and the result was:
##
##     clue_0 .. clue_15  ->  1 2 3 0 1 2 3 0 1 2 2 3 0 1 2 3
##
## The icons would have cycled through the set IN ORDER down every list. That
## is the most legible pattern the set could possibly have had -- the exact
## thing the rule at the top of this file forbids, arrived at by accident.
##
## The same flaw hid in the game salt. A different game shifted every key by one
## constant offset, so the whole assignment ROTATED rather than reshuffling: 400
## of 400 keys changed icon, which looks like a pass until you notice they all
## moved together and the mapping is just as fixed as before.
##
## This is the murmur3 32-bit finalizer. Each step is masked back to 32 bits
## because GDScript ints are 64-bit signed and would otherwise carry high bits
## the constants were never chosen for.
static func _mix32(value: int) -> int:
	var h: int = value & 0xFFFFFFFF
	h = ((h ^ (h >> 16)) * 0x7FEB352D) & 0xFFFFFFFF
	h = ((h ^ (h >> 15)) * 0x846CA68B) & 0xFFFFFFFF
	h = (h ^ (h >> 16)) & 0xFFFFFFFF
	return h
