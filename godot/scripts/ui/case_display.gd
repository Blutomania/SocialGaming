## CaseDisplay — shows the generated mystery:
## title, setting, crime, victim, suspects, coherence badge, evidence.
## Two action buttons: "Interrogate Suspects" and "Make Accusation".
##
## SESSION ANNOTATION — Phase 2:
## The viability rating widget lives on this screen (bottom).
## Phase 3: Add a "Shared Clues" panel on the right side for clues
## received from other players via the 75% mechanic.

extends Control

# ---------------------------------------------------------------------------
# Node references
# ---------------------------------------------------------------------------
@onready var bg_texture: TextureRect = $BgTexture
@onready var title_label: Label = $ScrollContainer/MainVBox/TitleLabel
@onready var setting_label: RichTextLabel = $ScrollContainer/MainVBox/SettingLabel
@onready var crime_label: RichTextLabel = $ScrollContainer/MainVBox/CrimeLabel
@onready var cast_container: VBoxContainer = $ScrollContainer/MainVBox/CastContainer
@onready var coherence_label: Label = $ScrollContainer/MainVBox/CoherenceBadge
@onready var evidence_container: VBoxContainer = $ScrollContainer/MainVBox/EvidenceContainer
@onready var gameplay_label: Label = $ScrollContainer/MainVBox/GameplayLabel
@onready var interrogate_button: Button = $ScrollContainer/MainVBox/Buttons/InterrogateButton
@onready var accuse_button: Button = $ScrollContainer/MainVBox/Buttons/AccuseButton
@onready var main_menu_button: Button = $ScrollContainer/MainVBox/Buttons/MainMenuButton
@onready var viability_hbox: HBoxContainer = $ScrollContainer/MainVBox/ViabilityRow
@onready var viability_label: Label = $ScrollContainer/MainVBox/ViabilityRow/ViabilityLabel

var _mystery: MysteryData
var _current_rating: int = 0

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	if ResourceLoader.exists("res://assets/ui/case_bg.png"):
		bg_texture.texture = load("res://assets/ui/case_bg.png")
	elif ResourceLoader.exists("res://assets/ui/main_menu_bg.png"):
		bg_texture.texture = load("res://assets/ui/main_menu_bg.png")
	_mystery = MysteryData.from_dict(GameState.current_mystery)
	_populate()
	interrogate_button.pressed.connect(_go_interrogate)
	accuse_button.pressed.connect(_go_accuse)
	main_menu_button.pressed.connect(func(): get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn"))

func _populate() -> void:
	title_label.text = _mystery.title

	setting_label.text = (
		"[b]%s[/b] — [i]%s[/i]\n%s" % [
			_mystery.location,
			_mystery.time_period,
			_mystery.setting_description,
		]
	)

	crime_label.text = (
		"[b]The Crime[/b]\n%s\n[i]When: %s[/i]\n[i]Discovered: %s[/i]" % [
			_mystery.what_happened,
			_mystery.when_occurred,
			_mystery.initial_discovery,
		]
	)

	# --- Cast ---
	# Clear any placeholder children
	for child in cast_container.get_children():
		child.queue_free()

	var victim := _mystery.get_victim()
	if victim.name:
		_add_cast_row("VICTIM", victim.name, victim.occupation, Color.INDIAN_RED)

	for suspect in _mystery.get_suspects():
		_add_cast_row("SUSPECT", suspect.name, suspect.occupation, Color.ORANGE)

	var witnesses := _mystery.characters.filter(func(c): return c.role == "witness")
	for w in witnesses:
		_add_cast_row("WITNESS", w.name, w.occupation, Color.SKY_BLUE)

	# --- Coherence badge ---
	if _mystery.coherence_passed:
		coherence_label.text = "Coherence: PASS (%d warnings)" % _mystery.coherence_warnings
		coherence_label.modulate = Color.GREEN
	else:
		coherence_label.text = (
			"Coherence: FAIL — %d blocking, %d warnings" % [
				_mystery.coherence_blocking,
				_mystery.coherence_warnings,
			]
		)
		coherence_label.modulate = Color.RED

	# --- Evidence ---
	for child in evidence_container.get_children():
		child.queue_free()
	for ev in _mystery.evidence:
		_add_evidence_row(ev)

	# --- Gameplay notes ---
	var twists_text := " · ".join(_mystery.key_twists) if _mystery.key_twists else "none"
	gameplay_label.text = (
		"Difficulty: %s  ·  Playtime: %s\nKey twists: %s" % [
			_mystery.difficulty,
			_mystery.estimated_playtime,
			twists_text,
		]
	)

	# --- Viability rating buttons ---
	_build_viability_buttons()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
func _add_cast_row(role_tag: String, name: String, occupation: String, color: Color) -> void:
	var lbl := Label.new()
	lbl.text = "[%s] %s — %s" % [role_tag, name, occupation]
	lbl.modulate = color
	cast_container.add_child(lbl)

func _add_evidence_row(ev: MysteryData.EvidenceData) -> void:
	var relevance_icon: String = ({"critical": "★", "red_herring": "✗", "supporting": "·"} as Dictionary).get(ev.relevance, "·")
	var panel := PanelContainer.new()
	var vbox := VBoxContainer.new()

	var header := Label.new()
	header.text = "%s [%s] %s  (%s)" % [relevance_icon, ev.id, ev.name, ev.type]
	header.modulate = Color.LIGHT_GRAY

	var desc := Label.new()
	desc.text = ev.description
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.add_theme_color_override("font_color", Color(0.85, 0.85, 0.85))

	vbox.add_child(header)
	vbox.add_child(desc)
	panel.add_child(vbox)
	evidence_container.add_child(panel)

func _build_viability_buttons() -> void:
	# Only free dynamically-added buttons — never free the label (it's a scene node)
	for child in viability_hbox.get_children():
		if child != viability_label:
			child.queue_free()
	viability_label.text = "Rate this mystery: "
	for i in range(1, 11):
		var btn := Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(36, 36)
		btn.pressed.connect(_on_rate.bind(i))
		viability_hbox.add_child(btn)

func _on_rate(rating: int) -> void:
	_current_rating = rating
	var slug: String = GameState.current_mystery.get("_slug", "")
	if slug.is_empty():
		return
	ApiClient.rate_mystery(slug, rating, func(err, _d):
		if err:
			push_warning("Rating save failed: " + err)
	)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _go_interrogate() -> void:
	GameState.game_phase = GameState.Phase.INTERROGATION
	get_tree().change_scene_to_file("res://scenes/ui/Interrogation.tscn")

func _go_accuse() -> void:
	GameState.game_phase = GameState.Phase.ACCUSATION
	get_tree().change_scene_to_file("res://scenes/ui/Accusation.tscn")
