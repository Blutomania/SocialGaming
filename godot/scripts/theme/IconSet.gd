## scripts/build_icons.py from icons/ — DO NOT EDIT BY HAND
##
## The icon sets, as resource paths. Regenerate with:
##     python3 scripts/build_icons.py
##
## Data only. The PICKING lives in scripts/theme/Icons.gd and is
## hand-written, because which icon a clue gets is a design rule with
## a reason behind it, not a list -- see that file.
class_name IconSet
extends RefCounted


const CLUE: Array[String] = [
	"res://assets/icons/clue/clue_01.svg",
	"res://assets/icons/clue/clue_02.svg",
	"res://assets/icons/clue/clue_03.svg",
	"res://assets/icons/clue/clue_04.svg",
]

const WITNESS: Array[String] = [
	"res://assets/icons/witness/witness_01.svg",
	"res://assets/icons/witness/witness_02.svg",
	"res://assets/icons/witness/witness_03.svg",
	"res://assets/icons/witness/witness_04.svg",
]

const SUSPECT: Array[String] = [
	"res://assets/icons/suspect/Suspect2.png",
	"res://assets/icons/suspect/business-woman-with-tie-icon.svg",
	"res://assets/icons/suspect/business-women-silhouette-icon.svg",
	"res://assets/icons/suspect/businessman-person-2-svgrepo-com.svg",
	"res://assets/icons/suspect/businesswoman-icon.svg",
	"res://assets/icons/suspect/detective-face-svgrepo-com.svg",
	"res://assets/icons/suspect/detective-svgrepo-com.svg",
	"res://assets/icons/suspect/dictator-svgrepo-com.svg",
	"res://assets/icons/suspect/evil-combatant-svgrepo-com.svg",
	"res://assets/icons/suspect/gentleman-person-svgrepo-com.svg",
	"res://assets/icons/suspect/m-i-b-svgrepo-com.svg",
	"res://assets/icons/suspect/male-person-2-svgrepo-com.svg",
	"res://assets/icons/suspect/male-student-1-svgrepo-com.svg",
	"res://assets/icons/suspect/masquerade-gentleman-svgrepo-com.svg",
	"res://assets/icons/suspect/mug-shot-svgrepo-com.svg",
	"res://assets/icons/suspect/person-silhouette-svgrepo-com.svg",
	"res://assets/icons/suspect/policeman-svgrepo-com.svg",
	"res://assets/icons/suspect/suspect1.png",
	"res://assets/icons/suspect/suspect3.png",
	"res://assets/icons/suspect/thief-svgrepo-com.svg",
	"res://assets/icons/suspect/woman-female-icon.svg",
	"res://assets/icons/suspect/woman-silhouette-svgrepo-com.svg",
	"res://assets/icons/suspect/woman-volunteer-icon.svg",
]

## path -> tags, from icons/suspect/tags.json. Every SUSPECT path has an
## entry -- build_icons.py refuses to build otherwise (see load_suspect_tags).
## Filtering by tag is Icons.gd's job, not data held here.
const SUSPECT_TAGS: Dictionary = {
	"res://assets/icons/suspect/Suspect2.png": ["masculine", "human"],
	"res://assets/icons/suspect/business-woman-with-tie-icon.svg": ["feminine", "human"],
	"res://assets/icons/suspect/business-women-silhouette-icon.svg": ["feminine", "human"],
	"res://assets/icons/suspect/businessman-person-2-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/businesswoman-icon.svg": ["feminine", "human"],
	"res://assets/icons/suspect/detective-face-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/detective-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/dictator-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/evil-combatant-svgrepo-com.svg": ["neutral", "human"],
	"res://assets/icons/suspect/gentleman-person-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/m-i-b-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/male-person-2-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/male-student-1-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/masquerade-gentleman-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/mug-shot-svgrepo-com.svg": ["neutral", "human"],
	"res://assets/icons/suspect/person-silhouette-svgrepo-com.svg": ["neutral", "human"],
	"res://assets/icons/suspect/policeman-svgrepo-com.svg": ["masculine", "human"],
	"res://assets/icons/suspect/suspect1.png": ["masculine", "human"],
	"res://assets/icons/suspect/suspect3.png": ["masculine", "human"],
	"res://assets/icons/suspect/thief-svgrepo-com.svg": ["neutral", "human"],
	"res://assets/icons/suspect/woman-female-icon.svg": ["feminine", "human"],
	"res://assets/icons/suspect/woman-silhouette-svgrepo-com.svg": ["feminine", "human"],
	"res://assets/icons/suspect/woman-volunteer-icon.svg": ["feminine", "human"],
}
