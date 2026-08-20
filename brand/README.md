# CYM brand assets

Source artwork for Choose Your Mystery's persistent screen elements. Parallel
to MYF's `mind-your-friends/public/brand/`.

Deliberately **not** inside `godot/` or `server/static/`: CYM has two clients
that both need these (the Godot host screen and the phone client at `/play`),
so the originals live here once and each client references or copies from here.
Putting the source in one client's folder is how the two end up with silently
different versions of the same mark.

## What goes here

Original artwork, at the size it was drawn — not export-optimised copies.
Prefer PNG with real transparency or SVG. Keep the filename descriptive.

## The one rule these assets must satisfy

**CYM's ground is slate `#2F4459`.** Anything drawn against white will lose its
dark half: near-black lands at ~1.9:1 on this ground and is effectively
invisible, which is exactly what happened to MYF's retired metallic title
treatment (see MYF `CLAUDE.md` item 48). Check a new mark's values against the
ground before assuming it reads — `background_field.py` documents the same
constraint for the background marks.
