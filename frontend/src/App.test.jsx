import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

describe('App', () => {
  it('renders the header and home view by default', () => {
    render(<App />)
    // Brand text and the home view heading both read "Wordle".
    expect(screen.getAllByText('Wordle').length).toBeGreaterThan(0)
    expect(
      screen.getByRole('heading', { name: 'Wordle' }),
    ).toBeInTheDocument()
  })

  it('navigates between views via the nav', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Stats' }))
    expect(
      screen.getByRole('heading', { name: 'Stats' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Play' }))
    expect(
      screen.getByRole('heading', { name: 'Play' }),
    ).toBeInTheDocument()
  })

  it('marks the active nav item with aria-current', async () => {
    const user = userEvent.setup()
    render(<App />)

    const statsButton = screen.getByRole('button', { name: 'Stats' })
    expect(statsButton).not.toHaveAttribute('aria-current')

    await user.click(statsButton)
    expect(statsButton).toHaveAttribute('aria-current', 'page')
  })
})
