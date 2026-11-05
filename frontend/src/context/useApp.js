import { useContext } from 'react'
import { AppContext } from './app-context'

/**
 * Access app state and actions. Throws if used outside AppProvider so
 * missing-provider bugs fail loudly in dev instead of silently.
 */
export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}
