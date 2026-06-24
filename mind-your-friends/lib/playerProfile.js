// Tentative — lightweight cross-game player memory.
// Not a user account. No login. Device-local or short-code based.
// See GAME_DESIGN.md → Player Memory for design rationale.

export function emptyProfile() {
  return {
    avatarSeed: null,
    preferredCategories: [],
    badgeCooldowns: {},
  };
}

const BADGE_COOLDOWN_GAMES = 4;

export function isBadgeOnCooldown(profile, archetype) {
  const lastSeen = profile.badgeCooldowns[archetype];
  if (lastSeen == null) return false;
  return lastSeen < BADGE_COOLDOWN_GAMES;
}

export function recordBadge(profile, archetype) {
  profile.badgeCooldowns[archetype] = 0;
  return profile;
}

export function tickCooldowns(profile) {
  for (const archetype of Object.keys(profile.badgeCooldowns)) {
    profile.badgeCooldowns[archetype] += 1;
  }
  return profile;
}
