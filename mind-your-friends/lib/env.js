// Loads .env.local (and friends) into process.env.
//
// Next.js loads these automatically for its own runtime, but NOT for a custom
// server — server.js is a plain Node process that happens to embed Next, so
// nothing has read the env files by the time our modules initialise. Without
// this, `cp .env.local.example .env.local && npm run dev` starts a server whose
// ANTHROPIC_API_KEY is undefined, and the first Claude call fails.
//
// This MUST be imported before any module that reads process.env at module
// scope — claudeClient.js builds its client on import, and constants.js reads
// the game-length overrides on import. ESM evaluates every import (in
// declaration order) before running the importing file's body, so calling
// loadEnvConfig() inside server.js would run too late. Keeping it in its own
// module, imported first, is what makes the ordering work.
//
// @next/env ships as a dependency of next — no new package needed.

// Default import, not a named one: @next/env is CommonJS, so `import
// { loadEnvConfig }` throws at parse time in this ESM project.
import nextEnv from '@next/env';

nextEnv.loadEnvConfig(process.cwd());
