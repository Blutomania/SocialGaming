## MainMenu — entry point scene script.
## Buttons: New Game, Browse Saved Mysteries, Settings, Quit.
##
## SESSION ANNOTATION — Phase 2:
## The "Browse Saved" button calls ApiClient.list_mysteries() and shows a
## popup list. The actual browse UI can be a simple ItemList for now.
## Phase 3: Add "Multiplayer" button that opens LobbyCreate/LobbyJoin.

extends Control

# ---------------------------------------------------------------------------
# Node references (set these in the .tscn file)
# ---------------------------------------------------------------------------
@onready var new_game_button: Button = $VBox/NewGameButton
@onready var multiplayer_button: Button = $VBox/MultiplayerButton
@onready var browse_button: Button = $VBox/BrowseSavedButton
@onready var quit_button: Button = $VBox/QuitButton
@onready var status_label: Label = $StatusLabel
@onready var browse_popup: Window = $BrowsePopup          ## Created in scene
@onready var browse_list: ItemList = $BrowsePopup/VBox/ItemList

var _saved_mysteries: Array = []

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	GameState.reset()
	new_game_button.pressed.connect(_on_new_game)
	multiplayer_button.pressed.connect(_on_multiplayer)
	browse_button.pressed.connect(_on_browse)
	quit_button.pressed.connect(get_tree().quit)

	# Verify backend is reachable on startup
	status_label.text = "Checking backend…"
	ApiClient.health_check(_on_health_check)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_health_check(error: String, _data: Dictionary) -> void:
	if error:
		status_label.text = "Backend unreachable — start server at localhost:8000"
		status_label.modulate = Color.RED
	else:
		status_label.text = "Backend connected."
		status_label.modulate = Color.GREEN

func _on_new_game() -> void:
	GameState.is_multiplayer = false
	get_tree().change_scene_to_file("res://scenes/ui/MysteryGeneration.tscn")

func _on_multiplayer() -> void:
	GameState.is_multiplayer = true
	get_tree().change_scene_to_file("res://scenes/ui/MysteryGeneration.tscn")

func _on_browse() -> void:
	browse_button.disabled = true
	status_label.text = "Loading saved mysteries…"
	ApiClient.list_mysteries(_on_mysteries_listed)

func _on_mysteries_listed(error: String, data) -> void:
	browse_button.disabled = false
	if error:
		status_label.text = "Error: " + error
		return
	_saved_mysteries = data if data is Array else []
	browse_list.clear()
	for m in _saved_mysteries:
		var label := "%s [%s] %s" % [
			m.get("title", "?"),
			m.get("difficulty", "?"),
			"★%d" % m.get("viability_rating", 0) if m.get("viability_rating") else "",
		]
		browse_list.add_item(label)
	browse_popup.popup_centered(Vector2i(600, 400))

func _on_browse_item_selected(index: int) -> void:
	if index < 0 or index >= _saved_mysteries.size():
		return
	var slug: String = _saved_mysteries[index].get("slug", "")
	browse_popup.hide()
	status_label.text = "Loading mystery…"
	ApiClient.get_mystery(slug, _on_mystery_loaded)

func _on_mystery_loaded(error: String, data: Dictionary) -> void:
	if error:
		status_label.text = "Error: " + error
		return
	GameState.current_mystery = data
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
