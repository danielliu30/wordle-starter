import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from './ErrorBoundary'

function Bomb({ shouldThrow }) {
  if (shouldThrow) throw new Error('boom')
  return <p>all good</p>
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <Bomb shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('all good')).toBeInTheDocument()
  })

  it('renders the default fallback when a child throws', () => {
    render(
      <ErrorBoundary>
        <Bomb shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('boom')).toBeInTheDocument()
  })

  it('renders a custom fallback node', () => {
    render(
      <ErrorBoundary fallback={<p>custom failure UI</p>}>
        <Bomb shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('custom failure UI')).toBeInTheDocument()
  })

  it('supports a fallback render function receiving the error', () => {
    render(
      <ErrorBoundary fallback={(error) => <p>failed: {error.message}</p>}>
        <Bomb shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('failed: boom')).toBeInTheDocument()
  })

  it('calls onError with the error and error info', () => {
    const onError = vi.fn()
    render(
      <ErrorBoundary onError={onError}>
        <Bomb shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(onError).toHaveBeenCalledOnce()
    expect(onError.mock.calls[0][0].message).toBe('boom')
    expect(onError.mock.calls[0][1]).toHaveProperty('componentStack')
  })

  it('resets and retries when resetKeys change', () => {
    const { rerender } = render(
      <ErrorBoundary resetKeys={['route-a']}>
        <Bomb shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()

    // Same child still throws, but a new key gives it another chance —
    // simulate recovery by swapping to a non-throwing child too.
    rerender(
      <ErrorBoundary resetKeys={['route-b']}>
        <Bomb shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('all good')).toBeInTheDocument()
  })
})
