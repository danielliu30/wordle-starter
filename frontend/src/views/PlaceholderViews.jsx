/**
 * Placeholder views — mount points for Phase 3 screens.
 *
 * Each view is intentionally minimal: it proves routing works and gives
 * the real screen a stable import location (`./views`) to land in.
 */

function PlaceholderView({ title }) {
  return (
    <section className="view">
      <h1>{title}</h1>
      <p>This screen is coming soon.</p>
    </section>
  )
}

export function HomeView() {
  return <PlaceholderView title="Wordle" />
}

export function GameView() {
  return <PlaceholderView title="Play" />
}

export function StatsView() {
  return <PlaceholderView title="Stats" />
}

export function LeaderboardView() {
  return <PlaceholderView title="Leaderboard" />
}

export function ProfileView() {
  return <PlaceholderView title="Profile" />
}

export function NotFoundView() {
  return <PlaceholderView title="Page not found" />
}
