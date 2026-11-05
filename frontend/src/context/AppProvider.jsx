import { useReducer } from 'react'
import { AppContext, appReducer, initialAppState } from './app-context'

/**
 * AppProvider — supplies route/user state and navigation actions to the
 * tree below it. `initialState` is overridable for tests and stories.
 */
export function AppProvider({ children, initialState }) {
  const [state, dispatch] = useReducer(appReducer, {
    ...initialAppState,
    ...initialState,
  })

  const navigate = (route) => dispatch({ type: 'navigate', route })
  const setUser = (user) => dispatch({ type: 'setUser', user })
  const logout = () => dispatch({ type: 'logout' })

  return (
    <AppContext.Provider value={{ ...state, navigate, setUser, logout }}>
      {children}
    </AppContext.Provider>
  )
}
