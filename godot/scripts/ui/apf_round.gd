## ApfRound — the APF play screen, and the only screen the mechanic needs.
##
## THIS SCREEN IS THE GAME. With exploration gone there is no traversal, no
## budget and no phase gate; what is left is a casefile, a decision about it, and a
## board that makes the decision visible. docs/PLAYTEST_FLOW.md: "the casefile and
## the share are not part of the game — they are the game."
##
## WHY THE SHARE IS NOT ITS OWN SCREEN. It used to be (ShareSelection.tscn,
## still here and still wired to the gather loop). Under the rhythm the share
## belongs beside the board, because the board is what makes withholding legible
## without a word of explanation: a face stays lit that you could have darkened,
## and everyone can see you didn't. Moving the decision to a separate screen
## hides the one thing that gives it weight.
##
## THE CLIENT DERIVES NOTHING. The round, the requirement, the board and the
## pool all arrive from GET /apf/state. In particular the share minimum is the
## server's own answer — a second implementation of that rule has already cost
## this project a screen's worth of silently-refused legal moves, and
## scripts/test_share_rule.py exists to stop it coming back.
##
## Reached from the lobby once the host has assigned. Leaves for Accusation.tscn.

extends Control

# ---------------------------------------------------------------------------
# Node references (wire in ApfRound.tscn)
# ---------------------------------------------------------------------------
@onready var round_label: Label = $Margin/MainVBox/Header/RoundLabel
@onready var requirement_label: Label = $Margin/MainVBox/Header/RequirementLabel
@onready var round_bar: ProgressBar = $Margin/MainVBox/Progress/RoundBar
@onready var board_container: VBoxContainer = $Margin/MainVBox/Columns/BoardColumn/BoardScroll/BoardContainer
@onready var casefile_container: VBoxContainer = $Margin/MainVBox/Columns/CasefileColumn/CasefileScroll/CasefileContainer
@onready var table_label: Label = $Margin/MainVBox/TableLabel
@onready var status_label: Label = $Margin/MainVBox/StatusLabel
## The step pair (owner, Session 49): adjoining boxes, brass on hover. Next
## round and Close the case are the host's and are never both visible, so the
## pair is always two boxes for the host and Share alone for everyone else.
@onready var share_button: Button = $Margin/MainVBox/Actions/StepPair/ShareButton
@onready var next_round_button: Button = $Margin/MainVBox/Actions/StepPair/NextRoundButton
@onready var close_case_button: Button = $Margin/MainVBox/Actions/StepPair/CloseCaseButton
@onready var accuse_button: Button = $Margin/MainVBox/Actions/AccuseButton

## The SHARE half of each finding's SHARE / KEEP pair, for findings not yet
## shared, parallel to _selectable. pressed == chosen to share. Toggle-mode
## Buttons in a ButtonGroup with their KEEP half (Session 49, owner's markup):
## the theme draws the chosen half as a filled steel tile, so the decision
## reads from across the room, and naming BOTH options says that clicking
## changes it -- the old single toggle showed its state as its label and left
## the player to guess.
var _toggles: Array[Button] = []
## The finding dicts each checkbox stands for. Shared findings are NOT in here:
## sharing is monotone, so an already-shared finding has no decision left in it.
var _selectable: Array = []
var _busy: bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	share_button.pressed.connect(_on_share)
	next_round_button.pressed.connect(_on_next_round)
	close_case_button.pressed.connect(_on_close_case)
	accuse_button.pressed.connect(_on_accuse)

	## Other players' shares change the board and the pool, so the screen has to
	## react to them rather than only to its own actions. One refetch per event
	## is cheap: /apf/state is set arithmetic over a mystery already in memory.
	ApiClient.ws_event.connect(_on_ws_event)

	_render()
	_refresh()

func _on_ws_event(event_name: String, _data: Dictionary) -> void:
	if event_name in ["apf_state", "apf_opened", "apf_disclosed"]:
		_refresh()

# ---------------------------------------------------------------------------
# Server state
# ---------------------------------------------------------------------------
func _refresh() -> void:
	ApiClient.apf_state(GameState.game_id, GameState.player_id, _on_state)

func _on_state(error: String, data: Dictionary) -> void:
	if error:
		status_label.text = "Could not reach the table: " + error
		status_label.add_theme_color_override("font_color", Palette.NEGATIVE)
		return
	status_label.remove_theme_color_override("font_color")
	GameState.record_apf_state(data)
	_render()

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
func _render() -> void:
	var state: Dictionary = GameState.apf_state
	if state.is_empty():
		round_label.text = "Opening the case…"
		return

	var current: int = int(state.get("round", 0))
	var total: int = int(state.get("rounds", 0))
	round_label.text = "Round %d of %d" % [current, total]
	var happened: String = _what_happened_this_round(current)
	if not happened.is_empty():
		round_label.text += ": " + happened

	_render_progress(state, current, total)
	_render_requirement(state)
	_render_board()
	_render_casefile(state)
	_render_table(state)
	_render_actions(state)

## How far the investigation has come (owner's markup, Session 47: the
## reference's confidence slider "reappropriated to show how far in the
## investigation"). APF announces its round count before play, so this is
## rounds, and it is exact rather than an estimate. The caption row under it
## (Cold trail / Warming up / ...) was removed on the owner's markup, Session
## 49: it said in words what the bar already shows.
func _render_progress(state: Dictionary, current: int, total: int) -> void:
	var disclosed: bool = bool(state.get("disclosed", false))
	round_bar.max_value = float(maxi(total, 1))
	round_bar.value = float(total if disclosed else current)

## What THIS player was handed this round, for the heading (owner, Session
## 49). Truthful by construction: it names the kind of finding actually
## assigned, never a kind the mystery does not contain -- every statement in
## a mystery today is a witness's, so "interviewed a suspect" would be a false
## clue (item 37 logs the real feature). Each player's heading differs,
## because each casefile does. One finding per round, so slot N-1 is round N's.
const _HAPPENED_BY_KIND: Dictionary = {
	"witness": "You Interviewed a Witness",
	"clue": "You Found a Clue",
	"lead": "You Followed a Lead",
}

func _what_happened_this_round(current: int) -> String:
	var casefile: Array = GameState.apf_casefile()
	if current < 1 or current > casefile.size():
		return ""
	var newest: Dictionary = casefile[current - 1]
	return str(_HAPPENED_BY_KIND.get(str(newest.get("kind", "")), ""))

## The requirement is stated as a TOTAL, because that is what it is. Saying
## "share 1 more" would hide the shape of the rule — the ladder is cumulative,
## and a player who gave two away in round 2 has already met round 4.
func _render_requirement(state: Dictionary) -> void:
	var required: int = int(state.get("share_required", 0))
	var held: int = int(state.get("held", 0))
	var owed: int = int(state.get("share_outstanding", 0))

	if bool(state.get("disclosed", false)):
		requirement_label.text = "The case is closed — everything is on the table."
		requirement_label.remove_theme_color_override("font_color")
		return
	if required <= 0:
		## Round 1. Holding a single finding forces a share whatever the difficulty, so
		## there is no decision here and the screen does not pretend otherwise.
		requirement_label.text = "Read your finding. Nothing is asked of you yet."
		requirement_label.remove_theme_color_override("font_color")
		return

	## "findings", not "clues" (owner's wording, one noun changed): what a
	## player holds can be a witness statement or a lead as well as a clue.
	requirement_label.text = "%d of your %d findings must be shared" % [required, held]
	if owed > 0:
		requirement_label.text += "  ·  %d still owed" % owed
		requirement_label.add_theme_color_override("font_color", Palette.CAUTION)
	else:
		requirement_label.add_theme_color_override("font_color", Palette.POSITIVE)

## The suspect board. A row greys out when somebody SHARES a finding that clears
## that person, and the sharer's name goes on it. Nothing here greys a face on a
## narrowing (item 27): "man's size large" is a line the player draws, and a
## board that draws it for them deletes the deduction.
## A square image slot with no image in it yet (owner, playtest FindingsSept7:
## "we need more images in this game... images will come later when we use
## GenAI"). "FPO" -- production shorthand for "for position only" -- says the
## empty slot is deliberate. Deliberately NOT the PLAYTEST_FLOW.md video-slot
## approach (fill the gap with the best real content available, a map instead
## of an announcement) -- there IS no real-content stand-in for "what this
## person looks like" the way a map stands in for a scene, so naming the gap
## honestly is the only option that exists here, not a lesser copy of that one.
func _fpo_square(square_size: float) -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(square_size, square_size)

	var box := StyleBoxFlat.new()
	box.bg_color = Palette.SURFACE_DEEP
	box.border_color = Palette.LINE_SOFT
	box.set_border_width_all(Palette.BORDER_WIDTH)
	box.set_corner_radius_all(Palette.RADIUS_SMALL)
	panel.add_theme_stylebox_override("panel", box)

	var lbl := Label.new()
	lbl.text = "FPO"
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
	lbl.add_theme_color_override("font_color", Palette.INK_FAINT)
	panel.add_child(lbl)

	return panel

func _render_board() -> void:
	for child in board_container.get_children():
		child.queue_free()

	for entry in GameState.apf_board():
		var row: Dictionary = entry
		var wrapper := HBoxContainer.new()
		wrapper.add_theme_constant_override("separation", Palette.SPACE_SMALL)
		wrapper.add_child(_fpo_square(40.0))

		var box := VBoxContainer.new()
		box.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var name_label := Label.new()
		name_label.text = str(row.get("name", "?"))
		name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

		var cleared: bool = bool(row.get("cleared", false))
		if cleared:
			## Struck through and dimmed: the face is still on the board, because
			## knowing who is out is half the deduction. Dimming the WRAPPER, not
			## just the name, so the FPO square dims along with it.
			name_label.add_theme_color_override("font_color", Palette.INK_FAINT)
			wrapper.modulate = Color(1.0, 1.0, 1.0, 0.55)
		else:
			name_label.add_theme_color_override("font_color", Palette.INK)

		box.add_child(name_label)

		var by_label := Label.new()
		by_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		by_label.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
		if cleared:
			by_label.text = _cleared_by_text(row.get("cleared_by", []))
			by_label.add_theme_color_override("font_color", Palette.INK_MUTED)
		else:
			## NOT a verdict and not a nudge (owner, playtest FindingsSept7): this
			## reports only that no shared finding has cleared them yet -- the same
			## fact "cleared by X in round Y" reports in the other direction. The
			## MECHANIC is unchanged (item 27's board still greys a face only on a
			## shared exoneration); only the wording and visual weight of the
			## not-yet-cleared state changed, from a phrase that reads as a verdict
			## in an attention-grabbing accent (BRASS) to a neutral status in a
			## quiet one.
			by_label.text = "not yet cleared"
			by_label.add_theme_color_override("font_color", Palette.INK_FAINT)
		box.add_child(by_label)

		wrapper.add_child(box)
		board_container.add_child(wrapper)
		board_container.add_child(HSeparator.new())

## Attribution is the point, so the first name is spelled out rather than
## counted. "Ana cleared them in round 2" is a sentence about a person.
func _cleared_by_text(sources: Array) -> String:
	if sources.is_empty():
		return "cleared"
	var first: Dictionary = sources[0]
	var who: String = str(first.get("player_name", "someone"))
	var text: String = "cleared by %s in round %d" % [who, int(first.get("round", 0))]
	if bool(first.get("disclosure", false)):
		text += " (full disclosure)"
	if sources.size() > 1:
		text += " · and %d more" % (sources.size() - 1)
	return text

## The point at which a body cuts to its excerpt, when no sentence ending is
## found short enough to use as one. Chosen to be a couple of lines on this
## column's width, not a hard rule.
const _EXCERPT_FALLBACK_CHARS: int = 140

## Titles that end in a period without ending a sentence. Checked against the
## word immediately before a "." candidate -- found by running the excerpt
## against the accepted mystery's own real evidence text before trusting it:
## E2 opens "Written notes made by Dr. Voss within thirty minutes..." and a
## naive splitter cuts it to "Written notes made by Dr." -- a real defect in
## real content, not a hypothetical one, caught by testing against data
## instead of only against invented sentences.
const _TITLE_ABBREVIATIONS: Array[String] = [
	"mr", "mrs", "ms", "dr", "st", "capt", "rev", "prof", "jr", "sr", "mme", "mlle", "hon",
]

## A finding's excerpt: its OWN first sentence, verbatim -- never a generated
## summary (owner, playtest FindingsSept7; see the reply in this same turn on
## why that stays a deliberate, costed decision rather than a default). Falls
## back to a hard cut at the nearest word boundary when there is no sentence
## ending within a reasonable span, so one run-on paragraph cannot defeat the
## whole point of excerpting.
func _first_sentence(body: String) -> String:
	var search_from: int = 0
	while true:
		var idx: int = -1
		for mark in [". ", "! ", "? "]:
			var found: int = body.find(mark, search_from)
			if found != -1 and (idx == -1 or found < idx):
				idx = found
		if idx == -1:
			break
		if body[idx] == "." and _ends_in_title_abbreviation(body, idx):
			search_from = idx + 1
			continue
		return body.substr(0, idx + 1)

	if body.length() > 0 and body[body.length() - 1] in ".!?":
		return body
	if body.length() <= _EXCERPT_FALLBACK_CHARS:
		return body
	var cut: int = body.rfind(" ", _EXCERPT_FALLBACK_CHARS)
	if cut <= 0:
		cut = _EXCERPT_FALLBACK_CHARS
	return body.substr(0, cut) + "…"

## Whether the "." at `period_idx` closes a title abbreviation ("Dr.") rather
## than a sentence -- the word immediately before it, case-insensitively.
func _ends_in_title_abbreviation(body: String, period_idx: int) -> bool:
	var start: int = period_idx
	while start > 0 and body[start - 1] != " ":
		start -= 1
	var word: String = body.substr(start, period_idx - start).to_lower()
	return word in _TITLE_ABBREVIATIONS

## One finding's body, as a scannable bullet rather than a paragraph (owner,
## playtest FindingsSept7: "the findings are summarized so you can ingest them
## and begin to deduce from there"). "Full Finding", not "Full Testimony" --
## a finding can be a witness statement, a clue or a lead, and only the first
## of those is testimony. Skipped entirely when the excerpt already IS the
## whole body: a link with nothing left to reveal is a dead link, not a
## feature. Used for every row in What You Know -- yours and what was shared
## with you -- so a finding reads the same way whoever it came from.
##
## A STATEMENT is set in quotation marks instead of a bullet (owner, Session
## 49) -- they are someone's own words. Only statements: a clue or a lead is a
## description of a thing, and quoting it would put words in nobody's mouth.
func _body_block(body: String, statement: bool = false) -> Control:
	var wrap := VBoxContainer.new()

	var excerpt: String = _first_sentence(body)
	var bullet := Label.new()
	bullet.text = _quoted(excerpt) if statement else "•  " + excerpt
	bullet.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bullet.add_theme_color_override("font_color", Palette.INK_MUTED)
	wrap.add_child(bullet)

	if excerpt.strip_edges() == body.strip_edges():
		return wrap

	var full := Label.new()
	full.text = _quoted(body) if statement else body
	full.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	full.add_theme_color_override("font_color", Palette.INK_MUTED)
	full.visible = false
	wrap.add_child(full)

	var link := LinkButton.new()
	link.text = "Full Finding"
	link.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
	link.pressed.connect(func() -> void:
		full.visible = not full.visible
		bullet.visible = not full.visible
		link.text = "Show less" if full.visible else "Full Finding"
	)
	wrap.add_child(link)

	return wrap

## Curly quotes around a statement, after stripping any it already carries,
## so a generator that quotes its own testimony is not double-quoted.
func _quoted(text: String) -> String:
	var bare: String = text.strip_edges()
	for mark in ["\"", "“", "”"]:
		bare = bare.trim_prefix(mark).trim_suffix(mark)
	return "“" + bare + "”"

func _is_statement(finding: Dictionary) -> bool:
	return str(finding.get("kind", "")) == "witness"

## WHAT YOU KNOW (owner, Session 51): your casefile and everything shared with
## you, in ONE column -- before this they were two ("Your findings", "Shared
## information") and the owner found three columns too busy to digest. Newest
## round first; under each round, the finding you were handed and then what
## reached you from the table that round.
##
## Your own findings stay even once shared -- an investigator cannot be made to
## forget -- with a SHARED stamp and no toggle, because nothing is left to
## decide. What others shared carries SHARED WITH YOU and no name: who shared is
## on the table line below and in full disclosure at the end, and the owner
## judged the finding itself reads better without it. Your own shares are not
## repeated from the pool -- they are already here as your findings.
func _render_casefile(state: Dictionary) -> void:
	for child in casefile_container.get_children():
		child.queue_free()
	_toggles.clear()
	_selectable.clear()

	casefile_container.add_theme_constant_override("separation", Palette.SPACE_BASE)

	## What reached this player from others, by round. Disclosure entries (the
	## case closed, everything held went public) are kept apart: they were not
	## shared, they were revealed, and they head the list once the case closes.
	var received_by_round: Dictionary = {}
	var disclosed: Array = []
	for entry in state.get("shared_pool", []):
		var item: Dictionary = entry
		if str(item.get("shared_by_id", "")) == GameState.player_id:
			continue
		if bool(item.get("disclosure", false)):
			disclosed.append(item)
		else:
			var r: int = int(item.get("shared_round", 0))
			if not received_by_round.has(r):
				received_by_round[r] = []
			received_by_round[r].append(item)

	if not disclosed.is_empty():
		casefile_container.add_child(_round_tag("REVEALED WHEN THE CASE CLOSED"))
		for item in disclosed:
			casefile_container.add_child(_finding_row(item, "HELD BACK"))

	## One finding per round, so slot i arrived in round i + 1.
	var casefile: Array = GameState.apf_casefile()
	for i in range(casefile.size() - 1, -1, -1):
		var round_no: int = i + 1
		casefile_container.add_child(_round_tag("ROUND %d" % round_no))
		casefile_container.add_child(_finding_row(casefile[i]))
		for item in received_by_round.get(round_no, []):
			casefile_container.add_child(_finding_row(item, "SHARED WITH YOU"))

func _round_tag(text: String) -> Label:
	var tag := Label.new()
	tag.theme_type_variation = &"FaintLabel"
	tag.text = text
	return tag

## Night File's finding row (docs/STYLE_GUIDE.md): icon column | rule | the
## finding | its SHARE / KEEP pair. The whole row is the hit target, not just
## the pair -- a player reaching for "this one" points at the text, and a
## small button is a small thing to have to find from a sofa.
const _ICON_SIZE: float = 44.0

## What a finding IS, in the words the room uses. The ID column's picture and
## this label have to agree (owner, Session 49): a witness's portrait over
## WITNESS STATEMENT, a clue image over CLUE or LEAD.
const _KIND_LABELS: Dictionary = {
	"witness": "WITNESS STATEMENT",
	"clue": "CLUE",
	"lead": "LEAD",
}

## `received` names a finding that came from someone else -- SHARED WITH YOU,
## or HELD BACK once disclosure makes it public. It gets that stamp and no
## toggle: there is nothing for this player to decide about it.
func _finding_row(finding: Dictionary, received: String = "") -> Control:
	var shared: bool = bool(finding.get("shared", false))
	var row := PanelContainer.new()
	row.theme_type_variation = &"FindingRowShared" if shared or not received.is_empty() else &"FindingRow"

	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", Palette.SPACE_WIDE)
	row.add_child(line)

	line.add_child(_kind_icon(finding))
	line.add_child(VSeparator.new())

	var body := VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", Palette.SPACE_TIGHT)
	var title := Label.new()
	title.theme_type_variation = &"HeadingLabel"
	title.text = str(finding.get("title", "?"))
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_child(title)
	var kind_text: String = str(_KIND_LABELS.get(str(finding.get("kind", "")), ""))
	if not kind_text.is_empty():
		var kind := Label.new()
		kind.theme_type_variation = &"FaintLabel"
		kind.text = kind_text
		body.add_child(kind)
	body.add_child(_body_block(str(finding.get("body", "")), _is_statement(finding)))
	line.add_child(body)

	if shared or not received.is_empty():
		## One filled, locked box: a share cannot be taken back, so there is no
		## KEEP beside it to offer. A stamp, not a button -- nothing to press.
		var stamp := PanelContainer.new()
		stamp.theme_type_variation = &"StampPanel"
		stamp.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		var stamp_text := Label.new()
		stamp_text.theme_type_variation = &"StampTextLabel"
		stamp_text.text = received if not received.is_empty() else "SHARED"
		stamp_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		stamp.add_child(stamp_text)
		line.add_child(stamp)
		return row

	## SHARE | KEEP, adjoining. KEEP starts chosen, because keeping is what
	## happens if a player does nothing. Hover highlights whichever half is
	## under the cursor (the theme's Button hover).
	var group := ButtonGroup.new()
	var pair := HBoxContainer.new()
	pair.add_theme_constant_override("separation", 0)
	pair.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var share_half := _choice_half("SHARE", group)
	var keep_half := _choice_half("KEEP", group)
	keep_half.button_pressed = true
	pair.add_child(share_half)
	pair.add_child(keep_half)
	line.add_child(pair)

	share_half.toggled.connect(func(on: bool) -> void:
		row.theme_type_variation = &"FindingRowChosen" if on else &"FindingRow"
		_on_toggle(on)
	)
	_toggles.append(share_half)
	_selectable.append(finding)

	## A click anywhere on the row that nothing inside it took (the pair and
	## the Full Finding link both consume their own) flips the choice. Labels
	## ignore the mouse and containers pass it up, so text clicks arrive here.
	## Pressing the OTHER half rather than un-pressing this one: a ButtonGroup
	## owns the exclusivity, and un-pressing its pressed member is refused.
	row.gui_input.connect(func(event: InputEvent) -> void:
		var click: InputEventMouseButton = event as InputEventMouseButton
		if click and click.pressed and click.button_index == MOUSE_BUTTON_LEFT and not share_half.disabled:
			if share_half.button_pressed:
				keep_half.button_pressed = true
			else:
				share_half.button_pressed = true
	)
	return row

func _choice_half(text: String, group: ButtonGroup) -> Button:
	var half := Button.new()
	half.toggle_mode = true
	half.button_group = group
	half.text = text
	half.custom_minimum_size = Vector2(76, 40)
	return half

## The ID column's picture (owner, Session 49: "replace the single letter
## with an icon"). The SET says what kind of finding this is -- a portrait for
## a witness, an object for a clue or lead -- which the label beside it says
## anyway. Which picture within the set is random (Icons.gd's header): it
## must never say WHICH finding, or a glance at someone's screen would.
## The old letter / evidence code (W, E11) is gone: it was an internal id.
func _kind_icon(finding: Dictionary) -> Control:
	var key: String = str(finding.get("id", ""))
	var path: String = Icons.witness(key, GameState.game_id) if _is_statement(finding) \
		else Icons.clue(key, GameState.game_id)
	var icon := TextureRect.new()
	icon.texture = Icons.texture(path)
	icon.custom_minimum_size = Vector2(_ICON_SIZE, _ICON_SIZE)
	## IGNORE_SIZE, or the imported SVG's pixel size becomes the minimum and
	## the column overflows (the CaseDisplay bug, Session 48).
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	icon.modulate = Icons.tint()
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return icon

## Who has paid and who has not. Public on purpose: the pattern across rounds is
## the thing the mechanic exists to produce.
func _render_table(state: Dictionary) -> void:
	var parts: PackedStringArray = []
	for entry in state.get("players", []):
		var p: Dictionary = entry
		var line: String = "%s: %d shared" % [str(p.get("name", "?")), int(p.get("shared", 0))]
		if int(p.get("outstanding", 0)) > 0:
			line += " (owes %d)" % int(p.get("outstanding", 0))
		parts.append(line)
	table_label.text = "  ·  ".join(parts)

func _render_actions(state: Dictionary) -> void:
	var disclosed: bool = bool(state.get("disclosed", false))
	var current: int = int(state.get("round", 0))
	var total: int = int(state.get("rounds", 0))
	var final_round: bool = current >= total

	## Only the host assigns and closes; everyone else would get a 403.
	next_round_button.visible = GameState.is_host and not disclosed and not final_round
	close_case_button.visible = GameState.is_host and not disclosed and final_round

	next_round_button.disabled = _busy or not bool(state.get("checkpoint_met", false))
	close_case_button.disabled = _busy or not bool(state.get("checkpoint_met", false))
	share_button.visible = not disclosed
	accuse_button.disabled = _busy

	_update_share_button()

func _update_share_button() -> void:
	var owed: int = GameState.apf_outstanding()
	var chosen: int = _selected_ids().size()
	share_button.disabled = _busy or chosen == 0
	if owed > 0 and chosen < owed:
		share_button.text = "Share selected (%d of %d owed)" % [chosen, owed]
	elif chosen > 0:
		share_button.text = "Share %d" % chosen
	else:
		share_button.text = "Share selected"

func _on_toggle(_pressed: bool) -> void:
	_update_share_button()

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
func _selected_ids() -> Array:
	var ids: Array = []
	for i in range(_toggles.size()):
		if _toggles[i].button_pressed:
			ids.append(str(_selectable[i].get("id", "")))
	return ids

## Sharing MORE than the minimum is legal and deliberately not blocked: the
## requirement is a floor, not a cap, and giving something away early is a real
## move. The server is the only thing that refuses a share, and it refuses only
## a finding the player was never assigned.
func _on_share() -> void:
	var ids: Array = _selected_ids()
	if ids.is_empty():
		return
	_set_busy(true)
	status_label.text = "Putting %d on the table…" % ids.size()
	ApiClient.apf_share(GameState.game_id, GameState.player_id, ids, _on_share_result)

func _on_share_result(error: String, data: Dictionary) -> void:
	_set_busy(false)
	if error:
		status_label.text = "The table did not accept that: " + error
		status_label.add_theme_color_override("font_color", Palette.NEGATIVE)
		return
	status_label.remove_theme_color_override("font_color")
	var owed: int = int(data.get("outstanding", 0))
	if owed > 0:
		status_label.text = "Shared. You still owe %d." % owed
	else:
		status_label.text = "Shared. The table is waiting on the others."
	_refresh()

func _on_next_round() -> void:
	_set_busy(true)
	status_label.text = "Opening the next round…"
	ApiClient.apf_next_round(GameState.game_id, GameState.player_id, _on_round_result)

func _on_round_result(error: String, _data: Dictionary) -> void:
	_set_busy(false)
	if error:
		status_label.text = "Could not open the next round: " + error
		status_label.add_theme_color_override("font_color", Palette.CAUTION)
		return
	status_label.remove_theme_color_override("font_color")
	status_label.text = ""
	_refresh()

## Full disclosure. Not a tie-breaker and not a rescue — it is the reward for
## having chosen this mystery, and it is what puts a name against every finding
## somebody sat on.
func _on_close_case() -> void:
	_set_busy(true)
	status_label.text = "Closing the case…"
	ApiClient.apf_disclose(GameState.game_id, GameState.player_id, _on_disclose_result)

func _on_disclose_result(error: String, _data: Dictionary) -> void:
	_set_busy(false)
	if error:
		status_label.text = "Could not close the case: " + error
		status_label.add_theme_color_override("font_color", Palette.NEGATIVE)
		return
	status_label.remove_theme_color_override("font_color")
	status_label.text = "Everything is on the table. Make your accusation."
	_refresh()

func _on_accuse() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/Accusation.tscn")

func _set_busy(busy: bool) -> void:
	_busy = busy
	share_button.disabled = busy
	next_round_button.disabled = busy
	close_case_button.disabled = busy
	accuse_button.disabled = busy
