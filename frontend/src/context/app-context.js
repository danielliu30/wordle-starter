import { createContext } from 'react'
import { ROUTES } from '../router/routes'

/**
 * App state store — context object, reducer, and initial state.
 *
 * Kept separate from AppProvider.jsx so each file exports a single kind
 * of thing (components vs. non-components), which keeps fast refresh and
 * tree-shaking happy.
 *
 * Per the design doc, state management uses React Context (a future
 * upgrade path is Zustand). It holds cross-cutting UI state only:
 * the active route and the current user (null for guests). Feature
 * state (game, stats, etc.) gets its own contexts later.
 */

export const AppContext = createContext(null)

export const initialAppState = {
  route: ROUTES.HOME,
  user: null,
}

export function appReducer(state, action) {
  switch (action.type) {
    case 'navigate':
      // Ignore unknown routes so a bad navigate() call can't wedge the UI.
      if (!Object.values(ROUTES).includes(action.route)) return state
      return { ...state, route: action.route }
    case 'setUser':
      return { ...state, user: action.user }
    case 'logout':
      return { ...state, user: null }
    default:
      return state
  }
}
