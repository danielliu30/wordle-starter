import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AppRouter from './AppRouter'
import { AppProvider } from '../context/AppProvider'
import { ROUTES } from '../router/routes'

function renderAt(route) {
  return render(
    <AppProvider initialState={{ route }}>
      <AppRouter />
    </AppProvider>,
  )
}

describe('AppRouter', () => {
  it.each([
    [ROUTES.HOME, 'Wordle'],
    [ROUTES.GAME, 'Play'],
    [ROUTES.STATS, 'Stats'],
    [ROUTES.LEADERBOARD, 'Leaderboard'],
    [ROUTES.PROFILE, 'Profile'],
  ])('renders the %s view', (route, heading) => {
    renderAt(route)
    expect(
      screen.getByRole('heading', { name: heading }),
    ).toBeInTheDocument()
  })

  it('renders NotFoundView for an unknown route', () => {
    renderAt('not-a-route')
    expect(
      screen.getByRole('heading', { name: 'Page not found' }),
    ).toBeInTheDocument()
  })
})
