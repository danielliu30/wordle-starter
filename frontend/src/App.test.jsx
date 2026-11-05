import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a loading state while fetching', () => {
    fetch.mockReturnValue(new Promise(() => {}))
    render(<App />)
    expect(screen.getByText(/Loading\.\.\./)).toBeInTheDocument()
  })

  it('renders the API response on success', async () => {
    fetch.mockResolvedValue({
      json: () => Promise.resolve({ message: 'Hello World' }),
    })
    render(<App />)
    await waitFor(() =>
      expect(screen.getByText(/Hello World/)).toBeInTheDocument(),
    )
  })

  it('renders an error message when the fetch fails', async () => {
    fetch.mockRejectedValue(new Error('network down'))
    render(<App />)
    await waitFor(() =>
      expect(
        screen.getByText(/Failed to connect to API/),
      ).toBeInTheDocument(),
    )
  })
})
