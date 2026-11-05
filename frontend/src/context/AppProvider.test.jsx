import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppProvider } from './AppProvider'
import { useApp } from './useApp'
import { ROUTES } from '../router/routes'
import { mockUser } from '../mocks'

function Probe() {
  const { route, user, navigate, setUser, logout } = useApp()
  return (
    <div>
      <span data-testid="route">{route}</span>
      <span data-testid="user">{user ? user.username : 'guest'}</span>
      <button onClick={() => navigate(ROUTES.GAME)}>go-game</button>
      <button onClick={() => navigate('bogus-route')}>go-bogus</button>
      <button onClick={() => setUser(mockUser())}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  )
}

describe('AppContext', () => {
  it('starts on the home route as a guest', () => {
    render(
      <AppProvider>
        <Probe />
      </AppProvider>,
    )
    expect(screen.getByTestId('route')).toHaveTextContent('home')
    expect(screen.getByTestId('user')).toHaveTextContent('guest')
  })

  it('navigates to a valid route', async () => {
    const user = userEvent.setup()
    render(
      <AppProvider>
        <Probe />
      </AppProvider>,
    )
    await user.click(screen.getByText('go-game'))
    expect(screen.getByTestId('route')).toHaveTextContent('game')
  })

  it('ignores navigation to an unknown route', async () => {
    const user = userEvent.setup()
    render(
      <AppProvider>
        <Probe />
      </AppProvider>,
    )
    await user.click(screen.getByText('go-bogus'))
    expect(screen.getByTestId('route')).toHaveTextContent('home')
  })

  it('sets and clears the user', async () => {
    const user = userEvent.setup()
    render(
      <AppProvider>
        <Probe />
      </AppProvider>,
    )
    await user.click(screen.getByText('login'))
    expect(screen.getByTestId('user')).toHaveTextContent('player1')
    await user.click(screen.getByText('logout'))
    expect(screen.getByTestId('user')).toHaveTextContent('guest')
  })

  it('accepts an initial state override', () => {
    render(
      <AppProvider initialState={{ route: ROUTES.STATS }}>
        <Probe />
      </AppProvider>,
    )
    expect(screen.getByTestId('route')).toHaveTextContent('stats')
  })

  it('useApp throws outside AppProvider', () => {
    // Suppress the expected error boundary noise from React.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Probe />)).toThrow(
      'useApp must be used within an AppProvider',
    )
    spy.mockRestore()
  })
})
