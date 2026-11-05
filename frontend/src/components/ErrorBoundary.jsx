import { Component } from 'react'

/**
 * ErrorBoundary catches JavaScript errors anywhere in its child component
 * tree, logs them, and renders a fallback UI instead of crashing the app.
 *
 * Props:
 * - fallback: React node, or a function `(error) => node` for custom UI.
 *   Defaults to a generic "something went wrong" message.
 * - onError: optional callback `(error, errorInfo) => void` for reporting
 *   (e.g. to an error monitoring service). Errors are always logged to
 *   console.error regardless.
 * - resetKeys: optional array of values; when any changes, the boundary
 *   clears its error state and retries rendering children. Useful for
 *   recovering when the route or relevant data changes.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  componentDidUpdate(prevProps) {
    // Auto-reset when resetKeys change so a transient failure doesn't
    // wedge the UI until a full page reload.
    if (
      this.state.error &&
      this.props.resetKeys &&
      !shallowArrayEqual(prevProps.resetKeys, this.props.resetKeys)
    ) {
      this.setState({ error: null })
    }
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    const { fallback } = this.props
    if (typeof fallback === 'function') return fallback(error)
    if (fallback) return fallback

    return (
      <div role="alert" className="error-boundary">
        <h2>Something went wrong</h2>
        <p>{error.message}</p>
      </div>
    )
  }
}

function shallowArrayEqual(a = [], b = []) {
  return a.length === b.length && a.every((v, i) => Object.is(v, b[i]))
}

export default ErrorBoundary
