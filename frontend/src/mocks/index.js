/**
 * Mock data factories for frontend development and tests.
 *
 * Each factory returns a fresh object every call so tests and components
 * can mutate results without leaking state between usages. Pass an
 * `overrides` object to customize any field, e.g. mockGame({ status: 'won' }).
 *
 * Shapes mirror the API contracts in docs/DESIGN_CONSOLIDATED.md.
 */

const FIXED_ID = '00000000-0000-4000-8000-000000000001'
const FIXED_DATE = '2026-01-01T00:00:00.000Z'

export function mockUser(overrides = {}) {
  return {
    user_id: FIXED_ID,
    email: 'player@example.com',
    username: 'player1',
    created_at: FIXED_DATE,
    ...overrides,
  }
}

export function mockGame(overrides = {}) {
  return {
    game_id: FIXED_ID,
    game_mode: 'custom',
    word_length: 5,
    max_turns: 6,
    status: 'in_progress',
    guesses: [],
    feedback: [],
    created_at: FIXED_DATE,
    ...overrides,
  }
}

export function mockStats(overrides = {}) {
  return {
    games_played: 10,
    games_won: 7,
    games_lost: 3,
    win_rate: 0.7,
    current_streak: 2,
    best_streak: 5,
    avg_guesses_to_win: 4.1,
    // { word_length: { guesses_used: wins } } per the API contract
    guess_distribution: { 5: { 3: 2, 4: 3, 5: 2 }, 6: { 4: 1, 5: 1 } },
    ...overrides,
  }
}

export function mockLeaderboardEntry(overrides = {}) {
  return {
    rank: 1,
    user_id: FIXED_ID,
    username: 'player1',
    win_rate: 0.7,
    games_played: 10,
    current_streak: 2,
    ...overrides,
  }
}

export function mockLeaderboard(overrides = {}) {
  return {
    leaderboard: [mockLeaderboardEntry()],
    current_user_rank: 1,
    ...overrides,
  }
}
