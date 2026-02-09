# CLAUDE.md

## Project Overview

This repository stores design documents and pitch decks for **Choose Your Mystery** — an AI-powered multiplayer party game where players collaboratively investigate crimes while competing to solve them first. Think of it as "Clue, expanded in every way imaginable" with AI-generated scenarios, characters, and dialogue.

The repository also contains a companion concept document for an AI-powered trivia/knowledge game with roguelike gameplay card mechanics.

## Repository Contents

This is a **document-only repository** — no source code, build tools, or dependencies.

| File | Description |
|------|-------------|
| `Choose Your Mystery - Concept Overview.pdf` | Core game design document: mechanics, game flow, information-sharing system, tech strategy, and success metrics |
| `Choose Your Mystery.pdf` | Investor/stakeholder pitch deck: market positioning, features, team background, competitive landscape, and pricing |
| `knowledge_ai.pdf` | Design document for a multiplayer AI trivia game with custom avatars, category selection, and gameplay cards |

## Key Game Concepts

### Choose Your Mystery
- **Genre:** AI-generated social mystery / party game
- **Players:** 2+ (single player, PvP, and co-op modes)
- **Core mechanic:** Players investigate a mystery, then must share 75% of discovered information with the group while keeping 25% private for competitive advantage
- **Game flow:** User Prompt → AI Generation → Crime Scene → Chase Leads → Crime Board Assembly → Information Sharing → Name the Culprit
- **Target price:** $19.99
- **Anticipated release:** 2026

### Knowledge AI (Trivia Game)
- **Genre:** AI-powered multiplayer trivia with roguelike card mechanics
- **Core mechanic:** Category-based trivia with strategic "gameplay cards" (e.g., Redirect, Hint Me Up, Bear/Bull Market for point values)
- **Inspirations:** You Don't Know Jack / Jackbox, Jeopardy

## Technical Direction (from design docs)

The concept overview outlines the following MVP development path:
1. Text-based interface with 2-3 players
2. Pre-written scenarios to test mechanics before full AI integration
3. Focus on perfecting the information-sharing system first
4. Web-based platform (HTML/CSS/JavaScript)
5. Gradual AI generation integration

Suggested tools: AI-assisted coding (Cursor), web technologies, no-code platforms (Construct 3, GameMaker Studio).

## Working with This Repository

### Structure
```
PDFs/
├── CLAUDE.md                                    # This file
├── Choose Your Mystery - Concept Overview.pdf   # Game design document
├── Choose Your Mystery.pdf                      # Pitch deck
└── knowledge_ai.pdf                             # Trivia game design document
```

### Conventions
- No source code exists yet; this repo is for version-controlling design documents
- PDF files are binary — they cannot be diffed meaningfully in Git
- No `.gitignore`, CI/CD, linting, testing, or build configuration exists
- There is no `README.md` — this CLAUDE.md serves as the primary documentation

### For AI Assistants
- When asked about the game design, extract text from the PDFs using `pdftotext` (requires `poppler-utils`)
- There are no code tasks to perform unless the user begins building the game prototype
- If development begins, follow the MVP path outlined in the Concept Overview: start with a web-based text interface, mock AI with pre-written scenarios, and focus on the 75/25 information-sharing mechanic first
- The creator (Blutomania / Ezra Greene) has a background in entertainment product marketing (505 Games, Warner Bros, MTV) — context for business-oriented questions

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update 'tasks/lessons.md' with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -> then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management
1. **Plan First**: Write plan to 'tasks/todo.md' with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review to 'tasks/todo.md'
6. **Capture Lessons**: Update 'tasks/lessons.md' after corrections

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
