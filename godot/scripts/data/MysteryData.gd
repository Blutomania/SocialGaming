## MysteryData — typed wrapper around the mystery JSON dict.
## Use MysteryData.from_dict(d) to convert the server response.
## Then access strongly-typed fields instead of raw Dictionary lookups.
##
## SESSION ANNOTATION — Phase 2:
## Add fields as needed. The server returns richer JSON than what's modelled
## here; access extras via mystery_data.raw["some_field"].

class_name MysteryData

# ---------------------------------------------------------------------------
# Inner classes
# ---------------------------------------------------------------------------

class CharacterData:
	var name: String = ""
	var role: String = ""       # victim | suspect | detective | witness
	var occupation: String = ""
	var motive: String = ""
	var alibi: String = ""
	var secret: String = ""

	static func from_dict(d: Dictionary) -> CharacterData:
		var c := CharacterData.new()
		c.name = d.get("name", "")
		c.role = d.get("role", "")
		c.occupation = d.get("occupation", "")
		c.motive = d.get("motive", "")
		c.alibi = d.get("alibi", "")
		c.secret = d.get("secret", "")
		return c

	func is_interrogatable() -> bool:
		return role in ["suspect", "witness"]


class EvidenceData:
	var id: String = ""
	var name: String = ""
	var description: String = ""
	var type: String = ""       # physical | testimonial | circumstantial | documentary
	var relevance: String = ""  # critical | supporting | red_herring

	static func from_dict(d: Dictionary) -> EvidenceData:
		var e := EvidenceData.new()
		e.id = d.get("id", "")
		e.name = d.get("name", "")
		e.description = d.get("description", "")
		e.type = d.get("type", "")
		e.relevance = d.get("relevance", "")
		return e


class SolutionData:
	var culprit: String = ""
	var method: String = ""
	var motive: String = ""
	var key_evidence: Array = []
	var how_to_deduce: String = ""

	static func from_dict(d: Dictionary) -> SolutionData:
		var s := SolutionData.new()
		s.culprit = d.get("culprit", "")
		s.method = d.get("method", "")
		s.motive = d.get("motive", "")
		s.key_evidence = d.get("key_evidence", [])
		s.how_to_deduce = d.get("how_to_deduce", "")
		return s

# ---------------------------------------------------------------------------
# MysteryData fields
# ---------------------------------------------------------------------------

var title: String = ""
var slug: String = ""

## Setting
var location: String = ""
var time_period: String = ""
var environment: String = ""
var setting_description: String = ""

## Crime
var crime_type: String = ""
var what_happened: String = ""
var when_occurred: String = ""
var initial_discovery: String = ""

## Cast
var characters: Array[CharacterData] = []

## Evidence
var evidence: Array[EvidenceData] = []

## Solution (hidden from players until accusation)
var solution: SolutionData = SolutionData.new()

## Gameplay metadata
var difficulty: String = ""
var estimated_playtime: String = ""
var key_twists: Array = []

## Backend metadata
var coherence_passed: bool = false
var coherence_blocking: int = 0
var coherence_warnings: int = 0

## The full raw dict — for fields not yet modelled above
var raw: Dictionary = {}

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

static func from_dict(d: Dictionary) -> MysteryData:
	var m := MysteryData.new()
	m.raw = d
	m.title = d.get("title", "Untitled Mystery")
	m.slug = d.get("_slug", "")

	var s: Dictionary = d.get("setting", {})
	m.location = s.get("location", "")
	m.time_period = s.get("time_period", "")
	m.environment = s.get("environment", "")
	m.setting_description = s.get("description", "")

	var c: Dictionary = d.get("crime", {})
	m.crime_type = c.get("type", "")
	m.what_happened = c.get("what_happened", "")
	m.when_occurred = c.get("when", "")
	m.initial_discovery = c.get("initial_discovery", "")

	for char_dict in d.get("characters", []):
		m.characters.append(CharacterData.from_dict(char_dict))

	for ev_dict in d.get("evidence", []):
		m.evidence.append(EvidenceData.from_dict(ev_dict))

	m.solution = SolutionData.from_dict(d.get("solution", {}))

	var notes: Dictionary = d.get("gameplay_notes", {})
	m.difficulty = notes.get("difficulty", "")
	m.estimated_playtime = notes.get("estimated_playtime", "")
	m.key_twists = notes.get("key_twists", [])

	var coherence: Dictionary = d.get("_coherence", {})
	m.coherence_passed = coherence.get("passed", false)
	m.coherence_blocking = coherence.get("blocking", 0)
	m.coherence_warnings = coherence.get("warnings", 0)

	return m

# ---------------------------------------------------------------------------
# Convenience queries
# ---------------------------------------------------------------------------

func get_victim() -> CharacterData:
	for ch in characters:
		if ch.role == "victim":
			return ch
	return CharacterData.new()

func get_suspects() -> Array:
	return characters.filter(func(c): return c.role == "suspect")

func get_interrogatable() -> Array:
	return characters.filter(func(c): return c.is_interrogatable())

func suspect_names() -> Array:
	return get_suspects().map(func(c): return c.name)

func character_by_name(char_name: String) -> CharacterData:
	for ch in characters:
		if ch.name == char_name:
			return ch
	return CharacterData.new()
