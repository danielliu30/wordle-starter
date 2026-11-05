import { useApp } from '../context/useApp'
import { ROUTES } from '../router/routes'

/**
 * Nav — top-level navigation rendered as buttons (not links) because
 * routing is state-based, not URL-based. `aria-current` marks the
 * active route for assistive tech.
 */
const NAV_ITEMS = [
  { route: ROUTES.HOME, label: 'Home' },
  { route: ROUTES.GAME, label: 'Play' },
  { route: ROUTES.STATS, label: 'Stats' },
  { route: ROUTES.LEADERBOARD, label: 'Leaderboard' },
  { route: ROUTES.PROFILE, label: 'Profile' },
]

function Nav() {
  const { route, navigate } = useApp()

  return (
    <nav className="nav" aria-label="Main">
      <ul className="nav__list">
        {NAV_ITEMS.map(({ route: itemRoute, label }) => (
          <li key={itemRoute}>
            <button
              type="button"
              className="nav__link"
              aria-current={route === itemRoute ? 'page' : undefined}
              onClick={() => navigate(itemRoute)}
            >
              {label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}

export default Nav
