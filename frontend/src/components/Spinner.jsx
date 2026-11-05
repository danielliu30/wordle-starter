import './Spinner.css'

/**
 * Spinner — animated loading indicator.
 *
 * Accessibility: exposes role="status" with an sr-only label so screen
 * readers announce loading without reading decorative markup. Pass `label`
 * to customize the announced text (e.g. "Loading game...").
 */
function Spinner({ label = 'Loading' }) {
  return (
    <span className="spinner" role="status">
      <span className="spinner__visual" aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </span>
  )
}

export default Spinner
