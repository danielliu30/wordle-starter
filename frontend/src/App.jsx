import { AppProvider } from './context/AppProvider'
import ErrorBoundary from './components/ErrorBoundary'
import Nav from './components/Nav'
import AppRouter from './components/AppRouter'
import './App.css'

/**
 * App — top-level orchestrator.
 *
 * Composition order matters: ErrorBoundary catches render failures in
 * everything below it; AppProvider supplies route/user state to Nav and
 * the routed view.
 */
function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <div className="app">
          <header className="app__header">
            <span className="app__brand">Wordle</span>
            <Nav />
          </header>
          <main className="app__main">
            <AppRouter />
          </main>
        </div>
      </AppProvider>
    </ErrorBoundary>
  )
}

export default App
