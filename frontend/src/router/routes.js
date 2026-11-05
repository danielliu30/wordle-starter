/**
 * Route definitions for the app's conditional-rendering router.
 *
 * The design calls for state-based view switching in App.jsx rather than
 * React Router; if a route is ever deep-linkable or needs params, this
 * is the seam where React Router would slot in.
 */
export const ROUTES = {
  HOME: 'home',
  GAME: 'game',
  STATS: 'stats',
  LEADERBOARD: 'leaderboard',
  PROFILE: 'profile',
}
