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

**CYM's ground is Night `#0C1118`.** It was slate `#2F4459` until Session 47,
and slate is still MYF's ground, so a mark shared by both titles has to read on
both. On Night it is a mark's dark half that disappears: anything below about
mid-grey sinks into the ground. On slate, near-black lands at ~1.9:1 and is
effectively invisible, which is exactly what happened to MYF's retired metallic
title treatment (see MYF `CLAUDE.md` item 48). Measure a new mark before
assuming it reads: `scripts/check_brand_contrast.py` grades against Night, and
`--myf` grades against slate.
