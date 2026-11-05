import { useApp } from '../context/useApp'
import { ROUTES } from '../router/routes'
import {
  HomeView,
  GameView,
  StatsView,
  LeaderboardView,
  ProfileView,
  NotFoundView,
} from '../views/PlaceholderViews'

/**
 * AppRouter — conditional-rendering router (per design: state-based view
 * switching, no React Router yet).
 *
 * The active route lives in AppContext; this component only maps route →
 * view. Unknown routes render NotFoundView as a safety net.
 */
const ROUTE_VIEWS = {
  [ROUTES.HOME]: HomeView,
  [ROUTES.GAME]: GameView,
  [ROUTES.STATS]: StatsView,
  [ROUTES.LEADERBOARD]: LeaderboardView,
  [ROUTES.PROFILE]: ProfileView,
}

function AppRouter() {
  const { route } = useApp()
  const View = ROUTE_VIEWS[route] ?? NotFoundView
  return <View />
}

export default AppRouter
