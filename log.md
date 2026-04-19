# Writing-Room Log

> Chronological record of all vault actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, deduplicate, restructure

## [2026-04-19] restructure | Initial wiki architecture
- Created `SCHEMA.md` with domain conventions, status taxonomy, genre tags, content types
- Created `index.md` with full project catalog and thematic summaries
- Created `log.md` (this file)

## [2026-04-19] restructure | Editor notes preserved
- Moved Lyra's editorial files (`README.md`, `STYLE_RUBRIC.md`, `GENRE_GUIDE.md`) to `_editor-notes/`
- Created `_editor-notes/ABOUT.md` with voice profile and key concepts
- Root `README.md` replaced with new writing-room index

## [2026-04-19] archive | aCoT drafts consolidated
- Moved `aCoT/draft2.md` and `aCoT/opening_scene.md` to `A Cage Of Thorns/_archive/`
- Removed `aCoT/` directory (early drafts superseded by main project)

## [2026-04-19] deduplicate | Cafe Confections ghost loop broken
- **Before:** 104 files across 3 variants (SliceOfLife, Gritty, Original) with recursive Gritty→Gritty→Gritty nesting
- **Finding:** All character files (5) and lore files (4) were byte-identical across all variants. All root files (README, Story Hook, Story Pitch, LOREBOOK, Draft 0) were also identical.
- **Action:** Removed all recursive nested Gritty folders (60 duplicate files). Consolidated remaining 3 variant copies to single canonical version. Archived Gritty and Original variants to `_archive/`.
- **After:** 14 canonical files + 30 archived variant files = 44 total (down from 104)
- **Net reduction:** 60 files removed (recursive duplicates eliminated)

## [2026-04-19] scan | Full vault audit
- Total projects: 6 active + 1 seed (EmberAndIron)
- Active files: 113 | Archived files: 32
- Previous total: ~204 files | Reduction: ~59 files (duplicates + drafts)
- Identified projects by status: 2 active (A Cage Of Thorns, The Loomworks), 1 active (Monster Girl Sanctuary), 3 dormant (Cafe Confections, battlemaster, dungeon-lore), 1 seed (EmberAndIron)
