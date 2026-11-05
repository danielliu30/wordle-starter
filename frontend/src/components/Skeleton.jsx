import './Skeleton.css'

/**
 * Skeleton — pulsing placeholder shown while content loads.
 *
 * Mirrors the shape of the content it replaces so layout doesn't jump
 * when real data arrives. Decorative only: hidden from assistive tech
 * because the surrounding loading state (e.g. Spinner) conveys status.
 *
 * Props:
 * - width / height: CSS length strings or numbers (numbers → px)
 * - className: extra classes for variant styling (e.g. "skeleton--line")
 */
function Skeleton({ width, height, className = '' }) {
  const style = {
    ...(width !== undefined && {
      width: typeof width === 'number' ? `${width}px` : width,
    }),
    ...(height !== undefined && {
      height: typeof height === 'number' ? `${height}px` : height,
    }),
  }

  return (
    <div
      className={`skeleton ${className}`.trim()}
      style={style}
      aria-hidden="true"
    />
  )
}

export default Skeleton
