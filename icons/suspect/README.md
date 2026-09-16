# icons/suspect/ — provenance

## The 15 SVGs (added playtest InterrogationSept8/ResultSept8)

Source: SVG Repo (svgrepo.com), pulled by the owner and handed over as a zip —
this sandbox's network policy blocks svgrepo.com directly, so these were never
fetched or license-checked from inside a session. SVG Repo's own claim is CC0
(public domain) per upload, checked at the page for each icon at the time it
was pulled.

**[CONFIRMED, Sept 16] Cleared by legal for the demo.** The owner had legal
independently verify this license claim; it holds for these 15 files, for the
demo. That clearance is scoped to the demo specifically, not asserted here as
a permanent, ships-on-Steam-forever clearance — if that broader question ever
comes up, it's a fresh check, not an inference from this one.

- businessman-person-2-svgrepo-com.svg
- detective-face-svgrepo-com.svg
- detective-svgrepo-com.svg
- dictator-svgrepo-com.svg
- evil-combatant-svgrepo-com.svg
- gentleman-person-svgrepo-com.svg
- m-i-b-svgrepo-com.svg
- male-person-2-svgrepo-com.svg
- male-student-1-svgrepo-com.svg
- masquerade-gentleman-svgrepo-com.svg
- mug-shot-svgrepo-com.svg
- person-silhouette-svgrepo-com.svg
- policeman-svgrepo-com.svg
- thief-svgrepo-com.svg
- woman-silhouette-svgrepo-com.svg

## What the owner's batch also contained, and was NOT added

The owner's zip held 22 SVG Repo files total. Seven were left out:

- **`stalin-svgrepo-com.svg`** — a caricature of a specific real historical
  figure (named as such in the filename itself). Excluded outright: these are
  meant to be anonymous, generic "suspect" placeholders, and a real person's
  likeness — especially this one — has no place standing in for a fictional
  murder suspect, independent of any copyright question.
- `female-toilet-svgrepo-com.svg` — a restroom pictogram, unrelated to this set.
- `high-school-girl-who-cut-her-bangs-too-short-5-svgrepo-com.svg`,
  `icon-for-people-who-love-money-dollar-edition-svgrepo-com.svg` — off-theme
  novelty icons, not generic figures.
- `female-lawyer-upper-body-svgrepo-com.svg`,
  `female-programmer-upper-body-svgrepo-com.svg`,
  `female-worker-upper-body-svgrepo-com.svg` — detailed 5-color illustrations,
  not flat silhouettes. Stylistically inconsistent with the rest of this set
  and everything else `Icons.gd` tints (a single `modulate` multiply only
  reads right on flat single-tone art), and closer to a specific portrait than
  an anonymous placeholder. Worth reconsidering as a *different* asset class
  later (real per-suspect portraits) rather than folded into this one.

**Worth flagging on its own:** excluding those three leaves this set skewed
toward masculine-presenting archetypes (businessman, gentleman, policeman,
thief, detective, ...) against one explicitly feminine-presenting silhouette
(`woman-silhouette`) and a few gender-neutral entries (`person-silhouette`,
`mug-shot`, `dictator`, `evil-combatant`). `Icons.gd`'s own picking rule never
correlates a specific icon to a specific suspect's identity — assignment is
seeded on name + game id, not on any trait of the character — but the set's
*composition* is still worth a second pass if a more balanced cast look
matters before this goes further than FPO.

## The gender-skew follow-up batch (18 files, not added except one)

The owner sent a second SVG Repo zip aimed at the skew flagged above. Of 18 files, only one was
added: `woman-svgrepo-com.svg`. `woman-silhouette-svgrepo-com.svg` in this batch is
**byte-identical** to the file already in this folder — not a new asset, skipped.

**[CORRECTED, Sept 16] `woman-svgrepo-com.svg` was described here as "a flat single-fill
silhouette in the same visual language as the existing set." That was wrong, and the mistake is
worth naming precisely: it was checked for color complexity with a regex that only matches
`fill="#..."` attribute syntax, and this file paints entirely via `style="fill:#...;"` — a
different syntax the check silently missed.** Rendered, it's a 9-distinct-color illustration:
blonde hair, light/tan skin tone, white shirt, red tie, tan blazer — stylistically identical to
the "detailed, upper-body, closer to a portrait than a placeholder" shape that got the
female-lawyer/programmer/worker trio excluded above, on the same grounds. See "Quantified skew
review" below for what this means for the set as a whole, and the recommendation.

**The other 16 were not added, on both the style ground this folder already applies and a license
ground this session's re-check turned up:**

- **Style:** each one carries `class="iconify iconify--twemoji"` and 4–12 distinct `fill="#..."`
  values — the same "detailed, multi-colour, closer to a portrait than an anonymous placeholder"
  shape that got the female-lawyer/programmer/worker trio excluded above, not the flat single-tone
  silhouette the rest of this set (and `Icons.gd`'s tint-by-modulate mechanism) is built around.
- **License (new finding, this is the re-check item 2 of the Sept-9 to-do asked for):** that
  `iconify--twemoji` class name is not cosmetic — these are Twemoji, Twitter/X's emoji artwork,
  which is licensed **CC-BY 4.0, not CC0**. CC-BY requires attribution; this whole set was pulled
  on the assumption (SVG Repo's own per-page tag) that everything here is CC0 and needs none. SVG
  Repo re-hosting a CC-BY work under its own CC0 badge does not change the original artist's
  actual terms. None of the 15 files in the first batch showed this marker — this is specific to
  the new batch. **Do not add any `iconify--twemoji`-tagged SVG Repo file to this set without
  either attributing Twemoji explicitly or getting a license the game can ship under.**

Excluded files (all Twemoji, all `-skin-tone` variants of the same handful of archetypes —
detective, astronaut, elf, fairy, farmer, mage, vampire, one wearing a turban, one in a veil, one a
zombie — plus one ungendered non-Twemoji `woman-dark-skin-tone` that turned out to carry the same
marker):

- woman-astronaut-light-skin-tone-svgrepo-com.svg
- woman-dark-skin-tone-svgrepo-com.svg
- woman-detective-light-skin-tone-svgrepo-com.svg
- woman-detective-medium-light-skin-tone-svgrepo-com.svg
- woman-detective-medium-skin-tone-svgrepo-com.svg
- woman-elf-medium-dark-skin-tone-svgrepo-com.svg
- woman-elf-medium-light-skin-tone-svgrepo-com.svg
- woman-fairy-light-skin-tone-svgrepo-com.svg
- woman-fairy-medium-light-skin-tone-svgrepo-com.svg
- woman-farmer-medium-skin-tone-svgrepo-com.svg
- woman-mage-medium-light-skin-tone-svgrepo-com.svg
- woman-mage-svgrepo-com.svg
- woman-svgrepo-com-2.svg
- woman-vampire-medium-light-skin-tone-svgrepo-com.svg
- woman-wearing-turban-light-skin-tone-svgrepo-com.svg
- woman-with-veil-svgrepo-com.svg
- woman-zombie-svgrepo-com.svg

**Net effect on the skew:** one more flat feminine-presenting silhouette (2 of 19 now), not the
larger rebalance the batch was hoping for. The skew this folder flagged is still real. Closing it
properly likely means sourcing flat, CC0-or-clearly-permissive, non-costumed body/portrait
silhouettes specifically — the same brief as the original set, filtered by gender presentation —
rather than an emoji character pack, which is a different asset class (see the "upper-body"
exclusions above) independent of its license.

## Quantified skew review (Sept 16) — all 19 current entries, actually rendered and looked at

Not inferred from filenames. Every SVG was rasterized and viewed alongside the three existing
PNGs. `Icons.gd` picks by hash of name + game id, uncorrelated with any trait of the character —
so every axis below is about the *pool's composition*, not about any single generated mystery.

| Axis | Breakdown |
|---|---|
| **Gender presentation** | 13 of 19 (68%) masculine-coded (`businessman-person-2`, `detective-face`, `detective`, `dictator`, `gentleman-person`, `m-i-b`, `male-person-2`, `male-student-1`, `masquerade-gentleman`, `policeman`, `Suspect2`, `suspect1`, `suspect3`) · 2 of 19 (11%) feminine-coded (`woman-silhouette`, `woman`) · 4 of 19 (21%) gender-neutral by construction — masked or featureless (`evil-combatant`, `mug-shot`, `person-silhouette`, `thief`) |
| **Apparent age** | 18 of 19 read as adults. 1 (`male-student-1`, a collared-shirt schoolboy look) reads distinctly younger — worth its own flag below, separate from gender. |
| **Race / skin tone** | 18 of 19 carry **no** race or skin-tone signal at all — flat black silhouettes or line art, race-neutral by construction, which is arguably the right property for an anonymous placeholder set. Exactly 1 (`woman`, the file added this batch) shows an explicit light/tan skin tone and blonde hair. That is the *only* racially-specific entry in the whole pool, and it lands on the one slot meant to broaden feminine representation — so the fix for one axis quietly created a problem on another: a feminine-presenting suspect has a real chance of always reading as a specific (light-skinned) ethnicity, where a masculine-presenting one never does. |
| **Disability / visible ability signals** | 0 of 19. No representation either way — an absence, not a skew, but worth naming since it was asked for. |
| **Religious / cultural dress** | 0 of 19 in the live set. The Sept batch's turban and veil variants existed in the source zip but were excluded for the Twemoji/CC-BY reason above, not for their content — so this axis is untested by choice, not by design. |

**What this means for actual play:** generation assigns each suspect a name and a described
gender/identity independent of which icon they draw. With the pool at 68% masculine / 11%
feminine / 21% neutral, a female character in the cast has roughly a 7-in-8 chance of being drawn
with a masculine-coded or neutral icon — a visible mismatch — and on the ~1-in-19 draw where the
pool's only feminine *portrait* (not silhouette) comes up, it also silently assigns a specific
race the character's own text may not describe at all.

**Recommendation:** pull `woman-svgrepo-com.svg` back out. It fails this set's own style rule
(flat, single-tone, race-neutral) on the same grounds three other files were already excluded for,
and it's the one file actively making the race axis worse, not better. That reverts the pool to
18 (69% masc / 5% fem / 26% neutral) — a smaller, less misleading number, not a fixed one. Actually
closing the skew still needs new sourcing: flat, race-neutral, non-costumed feminine-presenting
silhouettes, specifically — not filtered from a general-purpose icon pack, which is what produced
both failed attempts so far.
