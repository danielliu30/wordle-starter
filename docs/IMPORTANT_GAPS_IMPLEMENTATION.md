# Important Gaps - Detailed Implementation Plans

## Gap #7: Request/Response ID for Tracing

### Purpose
Enable distributed tracing across requests for debugging and monitoring

### Implementation

#### Backend

**Component**: Request ID Middleware

**Files**:
```
backend/
├── app/
│   ├── middleware/
│   │   ├── request_id.py
│   │   └── __init__.py
```

**Implementation**:
```python
# app/middleware/request_id.py
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Add to request state
        request.state.request_id = request_id

        # Process request
        response: Response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response
```

**Usage in main.py**:
```python
from app.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)
```

**Usage in endpoints**:
```python
@router.post("/api/games")
async def create_game(request: Request):
    request_id = request.state.request_id
    logger.info("Creating game", request_id=request_id)
    # ... implementation
```

**Usage in logging**:
```python
import structlog

logger = structlog.get_logger()
logger.info("User action", request_id=request.state.request_id, user_id=user_id)
```

#### Frontend

**Component**: Request ID Generator

**Files**:
```
frontend/
├── src/
│   ├── utils/
│   │   └── requestId.js
```

**Implementation**:
```javascript
// src/utils/requestId.js
export function generateRequestId() {
  return crypto.randomUUID ? crypto.randomUUID() : generateUUIDFallback();
}

function generateUUIDFallback() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
```

**Usage in API client**:
```javascript
import { generateRequestId } from '../utils/requestId';

async function createGame(gameMode, wordLength) {
  const requestId = generateRequestId();
  const response = await fetch(`${API_URL}/api/games`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Request-ID': requestId,
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ game_mode: gameMode, word_length: wordLength })
  });

  const returnedRequestId = response.headers.get('X-Request-ID');
  console.log('Request ID:', requestId, 'Response ID:', returnedRequestId);

  return response.json();
}
```

**Error display**:
```javascript
async function handleApiError(error) {
  const requestId = error.headers?.get('X-Request-ID');
  setError(`Something went wrong. Request ID: ${requestId}`);
}
```

### Testing

**Backend Tests**:
```python
def test_request_id_middleware():
    response = client.post("/api/games", headers={"X-Request-ID": "test-123"})
    assert response.headers["X-Request-ID"] == "test-123"

    response = client.post("/api/games")
    assert "X-Request-ID" in response.headers
    assert uuid.UUID(response.headers["X-Request-ID"])
```

### Impact
- Backend: +1 middleware file (~50 lines)
- Frontend: +1 utility file (~20 lines)
- Complexity: Low
- Benefit: High (debugging, monitoring)

---

## Gap #8: Pagination Strategy

### Purpose
Handle large datasets efficiently with pagination

### Implementation

#### Backend

**Approach**: Offset/Limit (simple, acceptable for assessment)

**Component**: Pagination utilities

**Files**:
```
backend/
├── app/
│   ├── utils/
│   │   ├── pagination.py
│   │   └── __init__.py
```

**Implementation**:
```python
# app/utils/pagination.py
from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool

class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

def paginate(items: List[T], total: int, params: PaginationParams) -> PaginatedResponse[T]:
    return PaginatedResponse(
        items=items,
        total=total,
        limit=params.limit,
        offset=params.offset,
        has_next=params.offset + params.limit < total,
        has_previous=params.offset > 0
    )
```

**Usage in repository**:
```python
from app.utils.pagination import PaginationParams, paginate

async def get_user_games(user_id: str, params: PaginationParams):
    query = select(Game).where(Game.user_id == user_id)
    total = await session.scalar(select(func.count()).where(Game.user_id == user_id))
    query = query.offset(params.offset).limit(params.limit)
    result = await session.execute(query)
    games = result.scalars().all()
    return paginate(games, total, params)
```

**Usage in endpoint**:
```python
@router.get("/api/users/me/games")
async def get_user_games(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    params = PaginationParams(limit=limit, offset=offset)
    return await game_repository.get_user_games(user_id, params)
```

#### Frontend

**Component**: Pagination hook

**Files**:
```
frontend/
├── src/
│   ├── hooks/
│   │   └── usePagination.js
```

**Implementation**:
```javascript
// src/hooks/usePagination.js
import { useState, useCallback } from 'react';

export function usePagination(initialLimit = 20) {
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(initialLimit);

  const offset = page * limit;

  const nextPage = useCallback(() => {
    setPage(p => p + 1);
  }, []);

  const previousPage = useCallback(() => {
    setPage(p => Math.max(0, p - 1));
  }, []);

  const goToPage = useCallback((pageNumber) => {
    setPage(Math.max(0, pageNumber));
  }, []);

  const resetPagination = useCallback(() => {
    setPage(0);
  }, []);

  return {
    page,
    limit,
    offset,
    setLimit,
    nextPage,
    previousPage,
    goToPage,
    resetPagination
  };
}
```

**Usage in component**:
```javascript
import { usePagination } from '../hooks/usePagination';

function GameHistory() {
  const { page, limit, offset, nextPage, previousPage } = usePagination(20);

  const { games, total, has_next, has_previous } = useFetchGames(offset, limit);

  return (
    <div>
      <GameList games={games} />
      <PaginationControls
        hasPrevious={has_previous}
        hasNext={has_next}
        onPrevious={previousPage}
        onNext={nextPage}
        currentPage={page}
        totalPages={Math.ceil(total / limit)}
      />
    </div>
  );
}
```

**Pagination UI Component**:
```javascript
function PaginationControls({ hasPrevious, hasNext, onPrevious, onNext, currentPage, totalPages }) {
  return (
    <div className="pagination">
      <button
        onClick={onPrevious}
        disabled={!hasPrevious}
      >
        Previous
      </button>
      <span>Page {currentPage + 1} of {totalPages}</span>
      <button
        onClick={onNext}
        disabled={!hasNext}
      >
        Next
      </button>
    </div>
  );
}
```

### Testing

**Backend Tests**:
```python
def test_pagination():
    params = PaginationParams(limit=10, offset=0)
    response = await get_user_games(user_id, params)
    assert response.limit == 10
    assert response.offset == 0
    assert len(response.items) <= 10
    assert response.has_previous == False
```

### Future Enhancement
For production, consider cursor-based pagination for better performance with large offsets.

### Impact
- Backend: +1 utility file (~50 lines)
- Frontend: +1 hook file (~40 lines), +1 component (~30 lines)
- Complexity: Low
- Benefit: High (handles large datasets)

---

## Gap #9: Rate Limiting Implementation

### Purpose
Prevent abuse and protect API resources

### Implementation

#### Backend

**Approach**: Redis-based sliding window rate limiting

**Component**: Rate limiting middleware

**Files**:
```
backend/
├── app/
│   ├── middleware/
│   │   ├── rate_limit.py
│   │   └── __init__.py
```

**Implementation**:
```python
# app/middleware/rate_limit.py
import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis.asyncio as redis

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, redis_client: redis.Redis, default_limit: int = 100):
        super().__init__()
        self.redis = redis_client
        self.default_limit = default_limit

    async def dispatch(self, request: Request, call_next):
        # Get client identifier (user ID or IP)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            identifier = f"user:{user_id}"
        else:
            identifier = f"ip:{request.client.host}"

        # Check rate limit
        key = f"rate_limit:{identifier}:{request.url.path}"
        current = await self.redis.incr(key)

        if current == 1:
            await self.redis.expire(key, 60)  # 1 minute window

        if current > self.default_limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.default_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                    "Retry-After": "60"
                }
            )

        # Process request
        response: Response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(self.default_limit - current)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        return response
```

**Usage in main.py**:
```python
from app.middleware.rate_limit import RateLimitMiddleware

redis_client = redis.from_url(REDIS_URL)
app.add_middleware(RateLimitMiddleware, redis_client=redis_client, default_limit=100)
```

**Endpoint-specific limits**:
```python
from fastapi import Depends

def get_rate_limit(limit: int):
    async def rate_limit_middleware(request: Request, call_next):
        # Custom rate limit for this endpoint
        # ... implementation
        return await call_next(request)
    return rate_limit_middleware

@router.post("/api/auth/login")
@rate_limit(limit=5)  # Stricter limit for login
async def login():
    # ... implementation
```

#### Frontend

**Component**: Rate limit error handling

**Implementation**:
```javascript
async function handleRateLimitError(error) {
  if (error.status === 429) {
    const retryAfter = error.headers.get('Retry-After');
    const limit = error.headers.get('X-RateLimit-Limit');
    setError(`Rate limit exceeded (${limit} requests/minute). Retry after ${retryAfter} seconds.`);
  }
}
```

### Testing

**Backend Tests**:
```python
async def test_rate_limit():
    # Make 101 requests
    for i in range(101):
        response = client.get("/api/games")
        if i < 100:
            assert response.status_code == 200
        else:
            assert response.status_code == 429
```

### Impact
- Backend: +1 middleware file (~60 lines)
- Frontend: +error handling (~10 lines)
- Complexity: Medium
- Benefit: High (prevents abuse)

---

## Gap #10: Frontend Routing Strategy

### Purpose
Navigate between different views (game, profile, leaderboard)

### Implementation

#### Approach: Conditional Rendering (Simple for Assessment)

**Component**: View Manager

**Files**:
```
frontend/
├── src/
│   ├── App.jsx
```

**Implementation**:
```javascript
// src/App.jsx
import { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import GameBoard from './components/GameBoard/GameBoard';
import ProfileView from './components/ProfileView/ProfileView';
import LeaderboardDisplay from './components/LeaderboardDisplay/LeaderboardDisplay';
import LoginForm from './components/Auth/LoginForm';
import GameModeSelector from './components/GameModeSelector/GameModeSelector';

function AppContent() {
  const { isAuthenticated, isGuest } = useAuth();
  const [currentView, setCurrentView] = useState('game'); // 'game' | 'profile' | 'leaderboard'

  if (!isAuthenticated) {
    return <LoginForm />;
  }

  return (
    <div className="app">
      <nav>
        <button onClick={() => setCurrentView('game')}>Game</button>
        <button onClick={() => setCurrentView('profile')}>Profile</button>
        <button onClick={() => setCurrentView('leaderboard')}>Leaderboard</button>
      </nav>

      {currentView === 'game' && <GameModeSelector />}
      {currentView === 'profile' && <ProfileView />}
      {currentView === 'leaderboard' && <LeaderboardDisplay />}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
```

#### Future Enhancement: React Router

**For production, upgrade to React Router**:
```bash
npm install react-router-dom
```

```javascript
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/game">Game</Link>
        <Link to="/profile">Profile</Link>
        <Link to="/leaderboard">Leaderboard</Link>
      </nav>
      <Routes>
        <Route path="/game" element={<GameModeSelector />} />
        <Route path="/profile" element={<ProfileView />} />
        <Route path="/leaderboard" element={<LeaderboardDisplay />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### Impact
- Frontend: Modified App.jsx (~50 lines)
- Complexity: Low
- Benefit: High (navigation between views)

---

## Gap #11: Frontend State Management Strategy

### Purpose
Manage global state without prop drilling

### Implementation

#### Approach: React Context (Simple for Assessment)

**Component**: Game State Context (already in design)

**Files**:
```
frontend/
├── src/
│   ├── context/
│   │   ├── GameStateContext.jsx
│   │   └── AuthContext.jsx
```

**Implementation** (already in design, just documenting strategy):

```javascript
// src/context/GameStateContext.jsx
import { createContext, useContext, useState, useCallback } from 'react';

const GameStateContext = createContext(null);

export function GameStateProvider({ children }) {
  const [currentGame, setCurrentGame] = useState(null);
  const [guesses, setGuesses] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [gameStatus, setGameStatus] = useState('idle'); // 'idle' | 'playing' | 'won' | 'lost'

  const createGame = useCallback(async (gameMode, wordLength) => {
    const game = await apiClient.createGame(gameMode, wordLength);
    setCurrentGame(game);
    setGuesses([]);
    setFeedback([]);
    setGameStatus('playing');
  }, []);

  const submitGuess = useCallback(async (guess) => {
    const result = await apiClient.submitGuess(currentGame.game_id, guess);
    setGuesses(prev => [...prev, guess]);
    setFeedback(prev => [...prev, result.feedback]);
    setGameStatus(result.status);
  }, [currentGame]);

  const resetGame = useCallback(() => {
    setCurrentGame(null);
    setGuesses([]);
    setFeedback([]);
    setGameStatus('idle');
  }, []);

  return (
    <GameStateContext.Provider value={{
      currentGame,
      guesses,
      feedback,
      gameStatus,
      createGame,
      submitGuess,
      resetGame
    }}>
      {children}
    </GameStateContext.Provider>
  );
}

export function useGameState() {
  const context = useContext(GameStateContext);
  if (!context) {
    throw new Error('useGameState must be used within GameStateProvider');
  }
  return context;
}
```

**Usage in components**:
```javascript
import { useGameState } from '../context/GameStateContext';

function GameBoard() {
  const { currentGame, guesses, feedback, submitGuess } = useGameState();
  // ... implementation
}
```

#### Future Enhancement: Zustand

**For production, upgrade to Zustand**:
```bash
npm install zustand
```

```javascript
import { create } from 'zustand';

const useGameStore = create((set) => ({
  currentGame: null,
  guesses: [],
  feedback: [],
  gameStatus: 'idle',

  createGame: (game) => set({ currentGame: game, guesses: [], feedback: [], gameStatus: 'playing' }),
  submitGuess: (guess, feedback) => set((state) => ({
    guesses: [...state.guesses, guess],
    feedback: [...state.feedback, feedback]
  })),
  resetGame: () => set({ currentGame: null, guesses: [], feedback: [], gameStatus: 'idle' })
}));
```

### Impact
- Frontend: Already in design, just documenting strategy
- Complexity: Low
- Benefit: High (avoid prop drilling)

---

## Gap #12: Loading States Strategy

### Purpose
Show loading indicators during async operations

### Implementation

#### Component: Loading Spinner

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── LoadingSpinner/
│   │   │   ├── LoadingSpinner.jsx
│   │   │   └── LoadingSpinner.css
```

**Implementation**:
```javascript
// src/components/LoadingSpinner/LoadingSpinner.jsx
import './LoadingSpinner.css';

function LoadingSpinner({ size = 'medium' }) {
  return (
    <div className={`loading-spinner loading-spinner--${size}`}>
      <div className="spinner"></div>
    </div>
  );
}

export default LoadingSpinner;
```

```css
/* src/components/LoadingSpinner/LoadingSpinner.css */
.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-left-color: #3b82f6;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
}

.loading-spinner--small .spinner {
  width: 20px;
  height: 20px;
  border-width: 2px;
}

.loading-spinner--large .spinner {
  width: 60px;
  height: 60px;
  border-width: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

#### Component: Skeleton Screen

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── Skeleton/
│   │   │   ├── Skeleton.jsx
│   │   │   └── Skeleton.css
```

**Implementation**:
```javascript
// src/components/Skeleton/Skeleton.jsx
import './Skeleton.css';

function Skeleton({ width, height, className = '' }) {
  const style = {
    width: width || '100%',
    height: height || '20px'
  };

  return (
    <div
      className={`skeleton ${className}`}
      style={style}
    />
  );
}

export default Skeleton;
```

```css
/* src/components/Skeleton/Skeleton.css */
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

#### Usage in components

**API client with loading state**:
```javascript
function useApiCall() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const call = useCallback(async (apiFunction) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFunction();
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, call };
}
```

**Component with loading state**:
```javascript
function GameHistory() {
  const { loading, error, call } = useApiCall();
  const [games, setGames] = useState([]);

  useEffect(() => {
    call(apiClient.getUserGames)
      .then(data => setGames(data.games));
  }, [call]);

  if (loading) {
    return (
      <div>
        <Skeleton height={60} />
        <Skeleton height={60} />
        <Skeleton height={60} />
      </div>
    );
  }

  if (error) {
    return <ErrorMessage error={error} />;
  }

  return <GameList games={games} />;
}
```

**Button with loading state**:
```javascript
function Button({ loading, children, ...props }) {
  return (
    <button disabled={loading} {...props}>
      {loading ? <LoadingSpinner size="small" /> : children}
    </button>
  );
}
```

### Impact
- Frontend: +2 components (~80 lines total)
- Complexity: Low
- Benefit: High (better UX)

---

## Gap #13: Error Boundaries

### Purpose
Catch and handle React component errors gracefully

### Implementation

#### Component: Error Boundary

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── ErrorBoundary/
│   │   │   ├── ErrorBoundary.jsx
│   │   │   └── ErrorBoundary.css
```

**Implementation**:
```javascript
// src/components/ErrorBoundary/ErrorBoundary.jsx
import { Component } from 'react';
import './ErrorBoundary.css';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Log error to service
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <details style={{ whiteSpace: 'pre-wrap' }}>
            {this.state.error && this.state.error.toString()}
            <br />
            {this.state.errorInfo.componentStack}
          </details>
          <button onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

```css
/* src/components/ErrorBoundary/ErrorBoundary.css */
.error-boundary {
  padding: 20px;
  background-color: #fee2e2;
  border: 1px solid #ef4444;
  border-radius: 8px;
  margin: 20px;
}

.error-boundary h2 {
  color: #dc2626;
  margin-top: 0;
}

.error-boundary button {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
```

#### Usage in App

```javascript
import ErrorBoundary from './components/ErrorBoundary/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <GameStateProvider>
          <AppContent />
        </GameStateProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
```

#### Specific Error Boundaries

**For game components**:
```javascript
function GameWrapper() {
  return (
    <ErrorBoundary fallback={<GameErrorFallback />}>
      <GameBoard />
      <Keyboard />
    </ErrorBoundary>
  );
}

function GameErrorFallback() {
  return (
    <div className="game-error">
      <p>Game encountered an error</p>
      <button onClick={() => window.location.reload()}>Restart Game</button>
    </div>
  );
}
```

### Impact
- Frontend: +1 component (~50 lines)
- Complexity: Low
- Benefit: High (better error handling)

---

## Gap #14: Mobile Responsiveness

### Purpose
Ensure app works well on mobile devices

### Implementation

#### CSS Strategy: Responsive Design with Media Queries

**Global CSS**:
```css
/* src/index.css */
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

/* Mobile-first approach */
@media (min-width: 768px) {
  .container {
    padding: 40px;
  }
}
```

**Game Board Responsive**:
```css
/* src/components/GameBoard/GameBoard.css */
.game-board {
  display: grid;
  gap: 5px;
  margin: 20px auto;
  max-width: 350px;
}

.game-cell {
  width: 50px;
  height: 50px;
  border: 2px solid #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  text-transform: uppercase;
}

/* Mobile adjustments */
@media (max-width: 480px) {
  .game-board {
    max-width: 300px;
    gap: 3px;
  }

  .game-cell {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }
}

/* Large screens */
@media (min-width: 768px) {
  .game-board {
    max-width: 400px;
  }

  .game-cell {
    width: 60px;
    height: 60px;
    font-size: 28px;
  }
}
```

**Keyboard Responsive**:
```css
/* src/components/Keyboard/Keyboard.css */
.keyboard {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 5px;
  margin: 20px auto;
  max-width: 500px;
}

.key {
  padding: 15px 5px;
  font-size: 16px;
  border: 1px solid #3b82f6;
  border-radius: 4px;
  cursor: pointer;
  text-align: center;
}

/* Mobile adjustments */
@media (max-width: 480px) {
  .keyboard {
    max-width: 350px;
    gap: 3px;
  }

  .key {
    padding: 10px 3px;
    font-size: 14px;
  }
}

/* Touch-friendly on mobile */
@media (hover: none) {
  .key {
    min-height: 50px;
    min-width: 30px;
  }
}
```

**Viewport Meta Tag**:
```html
<!-- index.html -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
```

#### Touch Event Handling

**Keyboard with touch support**:
```javascript
function Keyboard({ onKeyPress }) {
  const handleTouch = (letter) => {
    // Provide haptic feedback on mobile
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
    onKeyPress(letter);
  };

  return (
    <div className="keyboard">
      {keys.map(key => (
        <button
          key={key}
          onTouchEnd={() => handleTouch(key)}
          onClick={() => onKeyPress(key)}
        >
          {key}
        </button>
      ))}
    </div>
  );
}
```

### Testing

**Test on different screen sizes**:
- Use Chrome DevTools device emulation
- Test on actual mobile devices if possible
- Test touch interactions

### Impact
- Frontend: CSS updates (~200 lines across components)
- Complexity: Low
- Benefit: High (mobile users can use app)

---

## Gap #15: Logging Strategy

### Purpose
Structured logging for debugging and monitoring

### Implementation

#### Backend

**Library**: structlog

**Add to requirements.txt**:
```txt
structlog>=23.0.0
```

**Configuration**:
```python
# app/logging_config.py
import structlog
import logging
import sys

def configure_logging():
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Get logger
logger = structlog.get_logger()
```

**Usage in main.py**:
```python
from app.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger()
logger.info("Application starting")
```

**Usage in components**:
```python
logger = structlog.get_logger()

@router.post("/api/games")
async def create_game(request: Request):
    request_id = request.state.request_id
    user_id = request.state.user_id

    logger.info(
        "Creating game",
        request_id=request_id,
        user_id=user_id,
        game_mode=game_mode,
        word_length=word_length
    )

    # ... implementation

    logger.info(
        "Game created",
        request_id=request_id,
        game_id=game_id
    )
```

**Log format (JSON)**:
```json
{
  "event": "Creating game",
  "request_id": "uuid",
  "user_id": "uuid",
  "game_mode": "custom",
  "word_length": 5,
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "info"
}
```

**PII Redaction**:
```python
def redact_pii(data):
    """Redact personally identifiable information"""
    if 'email' in data:
        data['email'] = '***@***.***'
    if 'password' in data:
        data['password'] = '***'
    return data

logger.info("User login", user_id=user_id, **redact_pii({"email": email}))
```

### Impact
- Backend: +1 config file (~30 lines), logging updates (~50 lines)
- Complexity: Low
- Benefit: High (structured logs for debugging)

---

## Gap #16: Monitoring and Alerting

### Purpose
Monitor application health and performance

### Implementation

#### Approach: Basic metrics logging (can be enhanced later)

**Component**: Metrics collector

**Files**:
```
backend/
├── app/
│   ├── monitoring/
│   │   ├── metrics.py
│   │   └── __init__.py
```

**Implementation**:
```python
# app/monitoring/metrics.py
import time
from contextlib import contextmanager
from functools import wraps
import structlog

logger = structlog.get_logger()

@contextmanager
def track_request_duration(endpoint: str):
    """Track request duration"""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        logger.info(
            "request_duration",
            endpoint=endpoint,
            duration_ms=duration * 1000
        )

def track_metric(metric_name: str, value: float, tags: dict = None):
    """Log a metric"""
    logger.info(
        "metric",
        metric=metric_name,
        value=value,
        tags=tags or {}
    )

# Decorator for endpoint tracking
def track_endpoint(endpoint_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with track_request_duration(endpoint_name):
                try:
                    result = await func(*args, **kwargs)
                    track_metric(f"{endpoint_name}_success", 1)
                    return result
                except Exception as e:
                    track_metric(f"{endpoint_name}_error", 1)
                    raise
        return wrapper
    return decorator
```

**Usage in endpoints**:
```python
from app.monitoring.metrics import track_endpoint

@router.post("/api/games")
@track_endpoint("create_game")
async def create_game():
    # ... implementation
```

**Health check with metrics**:
```python
@router.get("/health")
async def health_check():
    # Check database
    db_start = time.time()
    await database.execute("SELECT 1")
    db_latency = (time.time() - db_start) * 1000

    # Check Redis
    redis_start = time.time()
    await redis.ping()
    redis_latency = (time.time() - redis_start) * 1000

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "database_latency_ms": db_latency,
            "redis_latency_ms": redis_latency
        }
    }
```

#### Future Enhancement: Prometheus

**For production, add Prometheus**:
```python
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

@router.post("/api/games")
async def create_game():
    with request_duration.time():
        request_count.labels(method='POST', endpoint='/api/games').inc()
        # ... implementation
```

**Metrics endpoint**:
```python
@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Impact
- Backend: +1 monitoring file (~60 lines)
- Complexity: Low
- Benefit: Medium (basic monitoring)

---

## Gap #17: Health Check Details

### Purpose
Detailed health check for load balancers and monitoring

### Implementation

#### Component: Health check service

**Files**:
```
backend/
├── app/
│   ├── monitoring/
│   │   ├── health.py
│   │   └── __init__.py
```

**Implementation**:
```python
# app/monitoring/health.py
from datetime import datetime
from fastapi import HTTPException
import time

class HealthChecker:
    def __init__(self, database, redis):
        self.database = database
        self.redis = redis

    async def check_database(self) -> dict:
        """Check database connectivity"""
        start = time.time()
        try:
            await self.database.execute("SELECT 1")
            latency = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_redis(self) -> dict:
        """Check Redis connectivity"""
        start = time.time()
        try:
            await self.redis.ping()
            latency = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_celery(self) -> dict:
        """Check Celery worker health"""
        try:
            # Check if Celery workers are responding
            from app.async_write.queue import get_queue_depth
            queue_depth = await get_queue_depth()
            return {
                "status": "healthy",
                "queue_depth": queue_depth
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_health_status(self) -> dict:
        """Get overall health status"""
        checks = {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "celery": await self.check_celery()
        }

        overall_status = "healthy" if all(
            check["status"] == "healthy" for check in checks.values()
        ) else "unhealthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
```

**Usage in health router**:
```python
from app.monitoring.health import HealthChecker

health_checker = HealthChecker(database, redis)

@router.get("/health")
async def health_check():
    return await health_checker.get_health_status()

@router.get("/health/ready")
async def readiness_check():
    """Readiness check - can app accept traffic?"""
    status = await health_checker.get_health_status()
    if status["status"] != "healthy":
        raise HTTPException(status_code=503, detail="Service not ready")
    return status

@router.get("/health/live")
async def liveness_check():
    """Liveness check - is app running?"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
```

**Response format**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.23
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 2.15
    },
    "celery": {
      "status": "healthy",
      "queue_depth": 0
    }
  }
}
```

### Impact
- Backend: +1 health checker file (~80 lines)
- Complexity: Low
- Benefit: High (load balancer health checks)

---

## Gap #18: Graceful Shutdown

### Purpose
Handle shutdown signals to prevent data loss

### Implementation

#### Component: Shutdown handler

**Files**:
```
backend/
├── app/
│   ├── lifecycle.py
```

**Implementation**:
```python
# app/lifecycle.py
import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Application starting up")
    # Initialize connections, etc.
    yield
    # Shutdown
    logger.info("Application shutting down")
    await shutdown_gracefully()

async def shutdown_gracefully():
    """Gracefully shutdown connections"""
    logger.info("Starting graceful shutdown")

    # Stop accepting new requests
    # (handled by uvicorn automatically)

    # Wait for in-flight requests to complete
    logger.info("Waiting for in-flight requests to complete")
    await asyncio.sleep(5)  # Wait for requests to finish

    # Close database connections
    logger.info("Closing database connections")
    # await database.close()

    # Close Redis connections
    logger.info("Closing Redis connections")
    # await redis.close()

    # Stop background tasks
    logger.info("Stopping background tasks")
    # cancel background tasks

    logger.info("Graceful shutdown complete")
```

**Usage in main.py**:
```python
from app.lifecycle import lifespan

app = FastAPI(lifespan=lifespan)
```

**Signal handling (if needed outside FastAPI)**:
```python
def setup_signal_handlers():
    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown")
        # Trigger graceful shutdown
        asyncio.create_task(shutdown_gracefully())

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
```

### Impact
- Backend: +1 lifecycle file (~40 lines)
- Complexity: Low
- Benefit: High (prevents data loss during deployment)

---

## Gap #19: Request Timeout Handling

### Purpose
Prevent resource exhaustion from long-running requests

### Implementation

#### Backend

**Component**: Timeout configuration

**Files**:
```
backend/
├── app/
│   ├── config.py
```

**Implementation**:
```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database timeout
    DATABASE_QUERY_TIMEOUT: int = 10  # seconds

    # Redis timeout
    REDIS_TIMEOUT: int = 5  # seconds

    # API request timeout
    API_REQUEST_TIMEOUT: int = 30  # seconds

    # External API timeout (if any)
    EXTERNAL_API_TIMEOUT: int = 10  # seconds

    class Config:
        env_file = ".env"

settings = Settings()
```

**Usage in database queries**:
```python
from sqlalchemy import text

async def execute_with_timeout(query, timeout=settings.DATABASE_QUERY_TIMEOUT):
    """Execute query with timeout"""
    try:
        result = await asyncio.wait_for(
            database.execute(query),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Database query timeout", query=str(query))
        raise HTTPException(status_code=504, detail="Database timeout")
```

**Usage in Redis operations**:
```python
async def redis_get_with_timeout(key, timeout=settings.REDIS_TIMEOUT):
    """Get from Redis with timeout"""
    try:
        return await asyncio.wait_for(
            redis.get(key),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("Redis timeout", key=key)
        raise HTTPException(status_code=504, detail="Cache timeout")
```

**Usage in HTTP client (if calling external APIs)**:
```python
import httpx

async def external_api_call(url, timeout=settings.EXTERNAL_API_TIMEOUT):
    """Call external API with timeout"""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url)
            return response.json()
        except httpx.TimeoutException:
            logger.error("External API timeout", url=url)
            raise HTTPException(status_code=504, detail="External service timeout")
```

#### Frontend

**Component**: Request timeout handling

**Implementation**:
```javascript
// API client with timeout
async function fetchWithTimeout(url, options = {}, timeout = 30000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}

// Usage
async function createGame(gameMode, wordLength) {
  try {
    const response = await fetchWithTimeout(
      `${API_URL}/api/games`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_mode: gameMode, word_length: wordLength })
      },
      30000  // 30 second timeout
    );
    return response.json();
  } catch (error) {
    if (error.message === 'Request timeout') {
      setError('Request timed out. Please try again.');
    }
    throw error;
  }
}
```

### Impact
- Backend: +1 config file (~20 lines), timeout wrappers (~50 lines)
- Frontend: +timeout handling (~30 lines)
- Complexity: Low
- Benefit: High (prevents resource exhaustion)

---

## Gap #20: Test Data Strategy

### Purpose
Reliable test data generation and cleanup

### Implementation

#### Backend

**Library**: pytest-factoryboy

**Add to requirements.txt**:
```txt
pytest-factoryboy>=3.3.0
faker>=20.0.0
```

**Component**: Test factories

**Files**:
```
backend/
├── tests/
│   ├── factories.py
```

**Implementation**:
```python
# tests/factories.py
import factory
from faker import Faker
from app.database.models import User, Game, GameAttempt

fake = Faker()

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: fake.email())
    password_hash = factory.LazyAttribute(lambda obj: fake.sha256())
    username = factory.LazyAttribute(lambda obj: fake.user_name())
    created_at = factory.LazyAttribute(lambda obj: fake.date_time_this_year())

class GameFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Game
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: f"game_{n}")
    user_id = factory.SubFactory(UserFactory)
    game_mode = factory.Iterator(["custom", "word_of_day", "practice"])
    word_length = factory.Iterator([5, 6, 7, 8])
    target_word = factory.LazyAttribute(lambda obj: fake.word())
    status = factory.Iterator(["in_progress", "won", "lost"])
    max_turns = factory.LazyAttribute(lambda obj: obj.word_length + 1)
    created_at = factory.LazyAttribute(lambda obj: fake.date_time_this_year())

class GameAttemptFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = GameAttempt
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: f"attempt_{n}")
    game_id = factory.SubFactory(GameFactory)
    attempt_number = factory.Sequence(lambda n: n)
    guess = factory.LazyAttribute(lambda obj: fake.word())
    feedback = factory.LazyAttribute(lambda obj: [
        {"letter": fake.random_letter(), "color": fake.random_element(["green", "yellow", "gray"])}
        for _ in range(5)
    ])
```

**Test fixtures**:
```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from tests.factories import UserFactory, GameFactory, GameAttemptFactory
from app.database.models import Base

@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session() as session:
        UserFactory._meta.sqlalchemy_session = session
        GameFactory._meta.sqlalchemy_session = session
        GameAttemptFactory._meta.sqlalchemy_session = session
        yield session
        await session.rollback()

@pytest.fixture
def user_factory(test_session):
    return UserFactory

@pytest.fixture
def game_factory(test_session):
    return GameFactory
```

**Usage in tests**:
```python
async def test_get_user_games(user_factory, game_factory):
    # Create test user
    user = user_factory.create()

    # Create test games
    game_factory.create(user_id=user.id, status="won")
    game_factory.create(user_id=user.id, status="lost")
    game_factory.create(user_id=user.id, status="in_progress")

    # Test
    games = await game_repository.get_user_games(user.id)
    assert len(games) == 3
```

**Test cleanup**:
```python
@pytest.fixture(autouse=True)
async def cleanup_database(test_session):
    """Auto-cleanup after each test"""
    yield
    await test_session.rollback()
```

#### Frontend

**Component**: Test data utilities

**Files**:
```
frontend/
├── src/
│   ├── tests/
│   │   ├── utils.js
```

**Implementation**:
```javascript
// src/tests/utils.js
export const mockGame = {
  game_id: 'game-123',
  game_mode: 'custom',
  word_length: 5,
  max_turns: 6,
  status: 'in_progress',
  guesses: [],
  feedback: [],
  remaining_turns: 6,
  created_at: '2024-01-01T00:00:00Z'
};

export const mockUser = {
  user_id: 'user-123',
  email: 'test@example.com',
  username: 'testuser',
  created_at: '2024-01-01T00:00:00Z'
};

export const mockStats = {
  games_played: 100,
  games_won: 70,
  games_lost: 30,
  win_rate: 0.7,
  current_streak: 5,
  best_streak: 15,
  avg_guesses_to_win: 4.2,
  guess_distribution: {
    '5': {1: 5, 2: 10, 3: 20, 4: 25, 5: 8, 6: 2}
  }
};

export const mockLeaderboard = {
  leaderboard: [
    {
      rank: 1,
      user_id: 'user-456',
      username: 'player1',
      win_rate: 0.95,
      games_played: 200,
      best_streak: 25
    }
  ],
  current_user_rank: 50
};
```

**Usage in tests**:
```javascript
import { render, screen } from '@testing-library/react';
import { mockGame, mockUser } from '../tests/utils';

test('GameBoard displays game state', () => {
  render(<GameBoard game={mockGame} />);
  expect(screen.getByText('6 turns remaining')).toBeInTheDocument();
});
```

### Impact
- Backend: +1 factories file (~80 lines), +1 conftest.py (~50 lines)
- Frontend: +1 test utils file (~50 lines)
- Complexity: Low
- Benefit: High (reliable tests)

---

## Summary

### Total Implementation Effort

**Backend**:
- 7 new files (~370 lines)
- 6 modified files (~150 lines)
- Total: ~520 lines

**Frontend**:
- 6 new files (~320 lines)
- 3 modified files (~100 lines)
- Total: ~420 lines

**Total**: ~940 lines of code

### Timeline Impact
- **Implementation time**: 2-3 days
- **Testing time**: 1 day
- **Total**: 3-4 days

### Priority Ordering

**Must Implement (Core functionality)**:
1. Request/Response ID (Gap #7)
2. Pagination (Gap #8)
3. Health Check Details (Gap #17)
4. Graceful Shutdown (Gap #18)
5. Request Timeout Handling (Gap #19)
6. Test Data Strategy (Gap #20)

**Should Implement (UX improvements)**:
7. Frontend Routing (Gap #10)
8. Frontend State Management (Gap #11)
9. Loading States (Gap #12)
10. Error Boundaries (Gap #13)
11. Mobile Responsiveness (Gap #14)

**Nice to Have (Observability)**:
12. Rate Limiting (Gap #9)
13. Logging Strategy (Gap #15)
14. Monitoring and Alerting (Gap #16)

### Risk Assessment

**Without these gaps**:
- Risk: MEDIUM
- Impact: Poor UX, hard to debug, potential resource exhaustion
- Deployment: Possible but not production-ready

**With these gaps**:
- Risk: LOW
- Impact: Good UX, debuggable, resource-protected
- Deployment: Production-ready for assessment scope

### Recommendation

Implement all 14 gaps in **Phase 0** (before core implementation):
- These are foundational pieces
- Hard to add later
- Relatively low effort
- High benefit

Then proceed with **Phase 1** (core components from DESIGN.md).
