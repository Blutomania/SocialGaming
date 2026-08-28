@tool
extends EditorScript
## VerifyScenes — LOADS every screen through the engine and says what actually
## came out. Run from the script editor: File → Run (Ctrl+Shift+X). Costs
## nothing and touches nothing on disk.
##
## WHY THIS EXISTS. scripts/check_godot_wiring.py reads the scene files with a
## regex. Session 36's lasting finding was that reading a scene is not the same
## as loading one: Interrogation.tscn declared 21 nodes, the checker saw all 21
## and confirmed every $NodePath against them, and five panels were still null
## at run time because a `#` line made the scene parser drop the node declared
## after it. The checker passed a screen that was broken.
##
## This closes that gap from the only place it can be closed — inside the
## engine. It parses the .tscn for the nodes it DECLARES, then instantiates the
## scene and asks the resulting tree which of them really exist. A node that is
## declared but missing is the Session 36 defect, and it is reported by name.
##
## It also reports a scene whose root lost its script, which is what a GDScript
## parse error looks like from the outside: no exception, no missing node, just
## a screen where nothing responds. Session 36 lost the whole result screen that
## way, to an implicit string concatenation GDScript does not have.
##
## instantiate() is safe to call here. _ready() and @onready both wait for the
## node to enter a tree, and nothing is added to one — so no scene fetches, no
## API calls, and no state is touched by running this.

const SCENES: Array[String] = [
	"res://scenes/ui/MainMenu.tscn",
	"res://scenes/ui/MysteryGeneration.tscn",
	"res://scenes/ui/Lobby.tscn",
	"res://scenes/ui/CaseDisplay.tscn",
	"res://scenes/ui/Interrogation.tscn",
	"res://scenes/ui/ShareSelection.tscn",
	"res://scenes/ui/Accusation.tscn",
	"res://scenes/ui/ResultScreen.tscn",
]


func _run() -> void:
	print("\n=== VerifyScenes ===")
	var failed: int = 0
	for path: String in SCENES:
		if not _check(path):
			failed += 1

	print("")
	if failed == 0:
		print("  All %d screens load with every declared node present." % SCENES.size())
		print("  This is the check check_godot_wiring.py cannot make.")
	else:
		print("  %d of %d screens did not survive loading — see above." % [failed, SCENES.size()])
	print("")


func _check(path: String) -> bool:
	var declared: PackedStringArray = _declared_paths(path)

	var packed: PackedScene = load(path) as PackedScene
	if packed == null:
		print("  FAIL  %s — did not load at all." % path)
		return false

	var root: Node = packed.instantiate()
	if root == null:
		print("  FAIL  %s — loaded but would not instantiate." % path)
		return false

	var missing: PackedStringArray = PackedStringArray()
	var wrong_type: PackedStringArray = PackedStringArray()
	for entry: String in declared:
		var parts: PackedStringArray = entry.split("\t")
		var node_path: String = parts[0]
		var node_type: String = parts[1] if parts.size() > 1 else ""
		if not root.has_node(node_path):
			missing.append(node_path)
		elif node_type != "" and not root.get_node(node_path).is_class(node_type):
			wrong_type.append("%s (declared %s, is %s)"
				% [node_path, node_type, root.get_node(node_path).get_class()])

	var lost_script: bool = _declares_root_script(path) and root.get_script() == null
	root.free()

	if missing.is_empty() and wrong_type.is_empty() and not lost_script:
		print("  ok    %s — %d nodes, all present." % [path, declared.size()])
		return true

	print("  FAIL  %s" % path)
	if lost_script:
		print("          root has NO script, though the scene declares one.")
		print("          That is what a GDScript parse error looks like from here —")
		print("          check the Output panel above for the parse message.")
	for name: String in missing:
		print("          missing node: %s" % name)
	for name: String in wrong_type:
		print("          wrong type:   %s" % name)
	return false


## The nodes the FILE says exist. Each entry is "path\ttype"; the root itself is
## skipped, since has_node("") is not a meaningful question.
func _declared_paths(path: String) -> PackedStringArray:
	var out: PackedStringArray = PackedStringArray()

	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		return out

	var node_re: RegEx = RegEx.new()
	node_re.compile("^\\[node name=\"([^\"]*)\"(.*)\\]")
	var type_re: RegEx = RegEx.new()
	type_re.compile("type=\"([^\"]*)\"")
	var parent_re: RegEx = RegEx.new()
	parent_re.compile("parent=\"([^\"]*)\"")

	while not file.eof_reached():
		var line: String = file.get_line()
		var m: RegExMatch = node_re.search(line)
		if m == null:
			continue

		var node_name: String = m.get_string(1)
		var rest: String = m.get_string(2)

		var parent_m: RegExMatch = parent_re.search(rest)
		if parent_m == null:
			continue  # the root node — nothing to resolve it against

		var parent: String = parent_m.get_string(1)
		var node_path: String = node_name if parent == "." else parent + "/" + node_name

		var type_m: RegExMatch = type_re.search(rest)
		var node_type: String = type_m.get_string(1) if type_m != null else ""

		out.append(node_path + "\t" + node_type)

	file.close()
	return out


func _declares_root_script(path: String) -> bool:
	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		return false
	var text: String = file.get_as_text()
	file.close()
	# The root's script is the one assigned before any [node ... parent=...] line.
	var head: String = text
	var first_child: int = text.find("parent=\"")
	if first_child != -1:
		head = text.substr(0, first_child)
	return head.contains("script = ExtResource")
