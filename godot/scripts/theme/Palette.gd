## scripts/build_palette.py from palette.py — DO NOT EDIT BY HAND
##
## The CYM palette, as Godot sees it. Regenerate with:
##     python3 scripts/build_palette.py
##
## Not an autoload and not a Theme. `class_name` makes every constant
## reachable as `Palette.GROUND` from any script with no load-order
## question to get wrong; the Theme that USES these is built in
## scripts/autoloads/Style.gd, which is hand-written and is not
## touched by regeneration.
##
## Every declaration states its type. Session 36 lost a whole screen to
## an inferred Variant, and `:=` on a constructor call is exactly the
## shape that went wrong.
class_name Palette
extends RefCounted


## Colours. Float components rather than Color("#RRGGBB") because a
## const initialiser has to be constant-foldable and a String is not.
const GROUND: Color = Color(0.047059, 0.066667, 0.094118, 1.0)  ## #0C1118
const SLATE: Color = Color(0.184314, 0.266667, 0.349020, 1.0)  ## #2F4459
const SURFACE: Color = Color(0.074510, 0.105882, 0.145098, 1.0)  ## #131B25
const SURFACE_DEEP: Color = Color(0.058824, 0.082353, 0.113725, 1.0)  ## #0F151D
const SURFACE_RAISED: Color = Color(0.117647, 0.168627, 0.227451, 1.0)  ## #1E2B3A
const LINE: Color = Color(0.337255, 0.470588, 0.611765, 1.0)  ## #56789C
const LINE_SOFT: Color = Color(0.231373, 0.313725, 0.407843, 1.0)  ## #3B5068
const INK: Color = Color(0.941176, 0.917647, 0.874510, 1.0)  ## #F0EADF
const INK_MUTED: Color = Color(0.662745, 0.713725, 0.764706, 1.0)  ## #A9B6C3
const INK_FAINT: Color = Color(0.490196, 0.545098, 0.600000, 1.0)  ## #7D8B99
const BRASS: Color = Color(0.788235, 0.635294, 0.152941, 1.0)  ## #C9A227
const BRASS_BRIGHT: Color = Color(0.890196, 0.737255, 0.258824, 1.0)  ## #E3BC42
const BRASS_DIM: Color = Color(0.541176, 0.435294, 0.105882, 1.0)  ## #8A6F1B
const STEEL: Color = Color(0.274510, 0.403922, 0.541176, 1.0)  ## #46678A
const STEEL_BRIGHT: Color = Color(0.458824, 0.607843, 0.784314, 1.0)  ## #759BC8
const POSITIVE: Color = Color(0.392157, 0.666667, 0.482353, 1.0)  ## #64AA7B
const NEGATIVE: Color = Color(0.835294, 0.525490, 0.537255, 1.0)  ## #D58689
const CAUTION: Color = Color(0.796078, 0.560784, 0.266667, 1.0)  ## #CB8F44


## Type sizes in pixels, for the 1280x720 host viewport. The phone
## client deliberately does NOT share these — see palette.py.
const TYPE_DISPLAY: int = 44
const TYPE_TITLE: int = 30
const TYPE_HEADING: int = 21
const TYPE_BODY: int = 18
const TYPE_LABEL: int = 13


## Spacing.
const SPACE_TIGHT: int = 4
const SPACE_SMALL: int = 8
const SPACE_BASE: int = 12
const SPACE_WIDE: int = 16
const SPACE_SECTION: int = 24
const SPACE_SCREEN: int = 32


## Corner radii.
const RADIUS_SMALL: int = 0
const RADIUS_BASE: int = 0
const RADIUS_CARD: int = 0

const BORDER_WIDTH: int = 2
const RULE_WIDTH: int = 1
