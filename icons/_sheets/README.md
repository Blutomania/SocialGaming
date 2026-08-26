# Icon sheets — the originals, kept out of the build's way

The first upload of the icon artwork arrived as two files, each holding a whole
row of four, and each one a **PNG wrapped in an SVG**: one `<image>` element
carrying a base64 payload, and zero `<path>` elements.

`scripts/build_icons.py` refuses those, by design — it recolours by rewriting
paint attributes, so a bitmap would pass through in its original eight hues and
be the only multi-coloured thing in the product. They live here rather than in
`icons/clue/` and `icons/witness/` so the build does not trip over them; the
build only globs the two set folders, so nothing in here is ever read.

`scripts/split_icon_sheet.py` can turn one of these into individual flattened
PNGs if a raster stopgap is ever needed again — it finds the real gutters by
column occupancy rather than dividing the width by four, which matters because
the spacing in these two sheets is uneven (gutters of 80/77/68 and 61/75/70
pixels against an even division of 338 and 331).

**Prefer replacing them.** A bitmap cannot be re-cut, re-weighted, or scaled
past its own resolution, and CYM's host screen is a television.
