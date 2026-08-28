@tool
extends EditorScript
## ApplyTheme — makes the design visible in the EDITOR, and checks every theme
## item name against the engine.
##
## Run it from the script editor: File → Run (Ctrl+Shift+X). It needs no
## arguments and spends nothing.
##
## WHY THIS EXISTS. Style.gd assigns the theme to get_tree().root, which only
## has a root at RUN time. Open a scene in the editor and you get engine grey:
## the design is real but invisible while it is being worked on. Godot's
## project-wide default theme (gui/theme/custom) IS honoured by the editor's
## canvas, but it has to be a Resource on disk, and Style.gd's header gives two
## good reasons not to hand-write one — it would be a fourth copy of the
## palette, and a .tres is the same text format that cost Session 36 five
## panels of Interrogation.tscn.
##
## Both objections are about hand-writing it. So this does not hand-write it:
## it calls Style.build_theme(), the same function the game uses, and lets
## ResourceSaver serialise the result. The .tres is a GENERATED PREVIEW of
## Style.gd, never a source. Style.gd stays the one implementation, palette.py
## stays the one place a colour is decided, and regenerating after any change
## to either is this one keystroke.
##
## Runtime is unaffected either way: a Control resolves its theme by walking
## ancestors first, so Style.gd's root assignment still wins at run time and the
## project default is only ever the editor's preview. A stale .tres can
## therefore mislead the editor, but it can never ship a wrong colour.
##
## WHAT THE CHECK IS FOR, AND WHY IT COULD NOT BE WRITTEN BEFORE. Setting a
## theme item Godot does not have is a SILENT no-op — no error, no warning, the
## control just keeps its engine default. Session 37 shipped ten control types
## whose item names nobody could verify, and recorded that "short of running
## Godot there cannot be" a guard. This is that guard: ThemeDB's default theme
## declares every item the engine really has, so every name Style.gd sets can be
## looked up in it. Anything printed under MISSES below is a name the engine
## does not know, i.e. a line of Style.gd that is doing nothing.

const THEME_DIR: String = "res://assets/theme"
const THEME_PATH: String = "res://assets/theme/cym_theme.tres"
const SETTING: String = "gui/theme/custom"


func _run() -> void:
	print("\n=== ApplyTheme ===")

	var theme: Theme = _build()
	if theme == null:
		push_error("ApplyTheme: Style.build_theme() returned nothing. Nothing was written.")
		return

	_report_fonts(theme)
	var misses: PackedStringArray = _validate(theme)
	_write(theme)
	_summarise(misses)


## Style.gd is an autoload, and autoloads are not instantiated in the editor, so
## the singleton is not reachable from here. build_theme() was deliberately
## written as a pure function for exactly this: it touches no tree and no state,
## so a bare instance can produce the theme and be freed again.
func _build() -> Theme:
	var script: GDScript = load("res://scripts/autoloads/Style.gd") as GDScript
	if script == null:
		push_error("ApplyTheme: could not load Style.gd.")
		return null
	var builder: Node = script.new() as Node
	if builder == null:
		push_error("ApplyTheme: Style.gd did not instantiate — it probably failed to parse.")
		return null
	var theme: Theme = builder.build_theme()
	builder.free()
	return theme


## The font canary, read off the built theme rather than off the Output panel.
## Style.gd keeps the engine default and warns if a face is missing, so a null
## default_font here means the three .ttf files have not been imported yet —
## usually just "the editor has not finished its first scan", not a real fault.
func _report_fonts(theme: Theme) -> void:
	if theme.default_font == null:
		print("  fonts   NOT loaded — every label will wear Godot's default face.")
		print("          If this is a fresh checkout, let the import finish and re-run.")
	else:
		print("  fonts   Nunito Sans loaded (default_font_size %d)." % theme.default_font_size)


## Every item Style.gd sets, looked up in the engine's own default theme.
## A type variation is checked against its BASE type, because that is what the
## engine resolves a variation's items against.
func _validate(theme: Theme) -> PackedStringArray:
	var engine: Theme = ThemeDB.get_default_theme()
	var misses: PackedStringArray = PackedStringArray()
	var checked: int = 0

	for type_name: String in theme.get_type_list():
		var base: String = String(theme.get_type_variation_base(type_name))
		var probe: String = base if base != "" else type_name

		for item: String in theme.get_color_list(type_name):
			checked += 1
			if not engine.has_color(item, probe):
				misses.append("color     %s/%s" % [type_name, item])
		for item: String in theme.get_font_list(type_name):
			checked += 1
			if not engine.has_font(item, probe):
				misses.append("font      %s/%s" % [type_name, item])
		for item: String in theme.get_font_size_list(type_name):
			checked += 1
			if not engine.has_font_size(item, probe):
				misses.append("font_size %s/%s" % [type_name, item])
		for item: String in theme.get_constant_list(type_name):
			checked += 1
			if not engine.has_constant(item, probe):
				misses.append("constant  %s/%s" % [type_name, item])
		for item: String in theme.get_stylebox_list(type_name):
			checked += 1
			if not engine.has_stylebox(item, probe):
				misses.append("stylebox  %s/%s" % [type_name, item])

	print("  items   %d checked across %d theme types." % [checked, theme.get_type_list().size()])
	return misses


func _write(theme: Theme) -> void:
	if not DirAccess.dir_exists_absolute(THEME_DIR):
		DirAccess.make_dir_recursive_absolute(THEME_DIR)

	var err: int = ResourceSaver.save(theme, THEME_PATH)
	if err != OK:
		push_error("ApplyTheme: could not write %s (error %d)." % [THEME_PATH, err])
		return
	print("  wrote   %s" % THEME_PATH)

	if String(ProjectSettings.get_setting(SETTING, "")) != THEME_PATH:
		ProjectSettings.set_setting(SETTING, THEME_PATH)
		var saved: int = ProjectSettings.save()
		if saved != OK:
			push_error("ApplyTheme: could not save project.godot (error %d)." % saved)
			return
		print("  set     %s = %s" % [SETTING, THEME_PATH])
	else:
		print("  set     %s was already pointed here." % SETTING)

	EditorInterface.get_resource_filesystem().scan()


func _summarise(misses: PackedStringArray) -> void:
	if misses.is_empty():
		print("\n  MISSES  none — every theme item name is one the engine has.")
	else:
		print("\n  MISSES  %d item(s) the engine does not have. Each is a line of" % misses.size())
		print("          Style.gd doing nothing, and would have gone unnoticed:")
		for miss: String in misses:
			print("            %s" % miss)

	print("\n  Reopen a scene to see the editor canvas pick the theme up.")
	print("  Commit both %s and project.godot.\n" % THEME_PATH)
