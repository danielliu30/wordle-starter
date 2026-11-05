import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Spinner from './Spinner'

describe('Spinner', () => {
  it('exposes a status role for assistive tech', () => {
    render(<Spinner />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('announces the default label to screen readers', () => {
    render(<Spinner />)
    expect(screen.getByText('Loading')).toBeInTheDocument()
  })

  it('accepts a custom label', () => {
    render(<Spinner label="Loading game..." />)
    expect(screen.getByText('Loading game...')).toBeInTheDocument()
  })

  it('hides the decorative visual from assistive tech', () => {
    const { container } = render(<Spinner />)
    expect(container.querySelector('.spinner__visual')).toHaveAttribute(
      'aria-hidden',
      'true',
    )
  })
})
