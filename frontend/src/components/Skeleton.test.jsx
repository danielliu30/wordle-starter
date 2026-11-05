import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import Skeleton from './Skeleton'

describe('Skeleton', () => {
  it('renders a decorative placeholder hidden from assistive tech', () => {
    const { container } = render(<Skeleton />)
    const el = container.firstChild
    expect(el).toHaveClass('skeleton')
    expect(el).toHaveAttribute('aria-hidden', 'true')
  })

  it('applies numeric dimensions as pixels', () => {
    const { container } = render(<Skeleton width={200} height={24} />)
    expect(container.firstChild).toHaveStyle({ width: '200px', height: '24px' })
  })

  it('accepts CSS string dimensions', () => {
    const { container } = render(<Skeleton width="100%" height="2rem" />)
    // Assert on the inline style: jsdom normalizes rem to px in computed styles.
    expect(container.firstChild.style.width).toBe('100%')
    expect(container.firstChild.style.height).toBe('2rem')
  })

  it('merges extra class names', () => {
    const { container } = render(<Skeleton className="skeleton--line" />)
    expect(container.firstChild).toHaveClass('skeleton', 'skeleton--line')
  })
})
