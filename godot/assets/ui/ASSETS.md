# UI Asset Slots

Drop images here and they appear automatically — no code changes needed.

| Filename | Used by | Recommended size | Notes |
|---|---|---|---|
| `main_menu_bg.png` | MainMenu background | 1280×720 | Full-bleed atmospheric image (dark, moody) |
| `logo.png` | MainMenu title logo | ~600×180 | Game title treatment, transparent BG preferred |
| `case_bg.png` | CaseDisplay background | 1280×720 | Crime scene / evidence board feel |
| `interrogation_bg.png` | Interrogation background | 1280×720 | Dark room, single light source feel |
| `accusation_bg.png` | Accusation background | 1280×720 | Tense/dramatic |
| `result_bg.png` | ResultScreen background | 1280×720 | Reveal moment |
| `icon.png` | Window/taskbar icon | 256×256 | Required by Godot — any square image works |

All images are loaded as `TextureRect` nodes set to `EXPAND` + `KEEP_ASPECT_COVERED`
so they fill the screen regardless of the source dimensions.
