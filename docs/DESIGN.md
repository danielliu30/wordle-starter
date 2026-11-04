# Wordle Full Stack Application - Consolidated Design Document

## Document Summary

This document consolidates the complete design including:
- Original system architecture and components
- 15 critical fixes from design review
- 14 important gaps with implementation details
- Outbox pattern for reliable event processing
- Configuration management and secrets
- Database migrations strategy
- API error response standards
- Test environment setup

**Total Components**: 40 backend, 21 frontend
**Total Lines of Code Estimate**: ~10,000 lines
**Timeline Estimate**: 3-4 weeks for full implementation

---

## Table of Contents

1. [Overview & Requirements](#overview--requirements)
2. [Critical Fixes Applied](#critical-fixes-applied)
3. [Important Gaps Addressed](#important-gaps-addressed)
4. [Outbox Pattern](#outbox-pattern)
5. [System Architecture](#system-architecture)
6. [Backend Components](#backend-components)
7. [Frontend Components](#frontend-components)
8. [Database Schema](#database-schema)
9. [API Design](#api-design)
10. [Configuration Management](#configuration-management)
11. [Testing Strategy](#testing-strategy)
12. [Implementation Phases](#implementation-phases)

---

## Overview & Requirements

### Core Features

1. **User Authentication**
   - Sign up / Sign in with email/password
   - Guest mode with 6-hour refresh tokens
   - Session management with JWT tokens
   - Access token in sessionStorage (persists across refresh)
   - Refresh token in httpOnly cookie
   - Password reset: **OUT OF SCOPE** for assessment

2. **Game Modes**
   - **Word of the Day**: Daily challenge, UTC-based, always 5 letters, one attempt per UTC day
   - **Custom Games**: Random words, configurable length (5-8), unlimited plays
   - **Practice Mode**: Persisted with `game_mode='practice'` flag, excluded from stats

3. **User Profiles & Stats**
   - Win/loss ratio
   - Current streak, best streak
   - Average guesses to win
   - **Per-word-length guess distribution** (5, 6, 7, 8)
   - Total games played
   - Historical attempts viewable

4. **Leaderboards**
   - Global leaderboard (by win rate, streaks)
   - Daily leaderboard (word of the day rankings)
   - **Event-driven invalidation** + 5-minute periodic fallback

5. **Persistence Strategy**
   - **Game state**: Write-through caching (sync DB write for critical data)
   - **Stats/leaderboards**: Async write with outbox pattern
   - In-memory cache (Redis) for hot data
   - PostgreSQL for long-term storage
   - SQLite for local development, PostgreSQL for production

6. **Idempotency**
   - Hierarchical scope: `{user_id}:{operation}:{resource_id}`
   - All user actions idempotent via unique request IDs
   - Safe retry on network failures

7. **Validation Strategy**
   - Frontend validation (optimistic UI)
   - Backend validation (source of truth)
   - **sessionStorage** for access tokens (persists across refresh, cleared on tab close)
   - **Server-wins** for offline sync conflicts

---

## Critical Fixes Applied

### Fix 1: Practice Mode Persistence
- **Solution**: Persist practice games with `game_mode='practice'` flag
- **Implementation**: Stats queries filter out practice games
- **Files**: GameRepository, StatsService

### Fix 2: Word of the Day Timezone
- **Solution**: UTC-based, word changes at 00:00 UTC
- **Implementation**: Use `datetime.utcnow().date()` for word selection
- **Display**: Show countdown to next word in user's local time

### Fix 3: Access Token Storage
- **Solution**: sessionStorage (NOT memory or localStorage)
- **Reason**: Persists across refreshes, more secure than localStorage, cleared on tab close
- **Implementation**: `sessionStorage.setItem('access_token', token)`

### Fix 4: Game State Async Write
- **Solution**: Write-through caching for game state (sync DB write)
- **Implementation**: Write to Redis sync, write to PostgreSQL sync before returning
- **Stats/leaderboards**: Can use async writes (non-critical)

### Fix 5: Guest Mode Refresh Token
- **Solution**: 6-hour refresh tokens for guests
- **Reason**: 15-min access token too short for 24-hour session
- **Implementation**: Guest sessions in user_sessions table with role='guest'

### Fix 6: Idempotency Key Scope
- **Solution**: Hierarchical scope `{user_id}:{operation}:{resource_id}`
- **Example**: `user_123:submit_guess:game_456`
- **Implementation**: Generate scoped keys in API client

### Fix 7: Logout Cookie Clearing
- **Solution**: Server-side Set-Cookie with expired cookie
- **Implementation**: `response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="strict")`

---

## Important Gaps Addressed

### Gap 7: Request/Response ID
- **Implementation**: Request ID middleware, generate UUID per request
- **Headers**: `X-Request-ID` in request and response
- **Logging**: Include request_id in all logs

### Gap 8: Pagination
- **Approach**: Offset/Limit (simple for assessment)
- **Implementation**: PaginatedResponse with limit/offset/total/has_next/has_previous
- **Max limit**: 100 items per page

### Gap 9: Rate Limiting
- **Approach**: Redis-based sliding window
- **Limits**: 100 req/min per user, 10 req/min per IP, 5 req/min for auth endpoints
- **Headers**: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

### Gap 10: Frontend Routing
- **Approach**: Conditional rendering (simple for assessment)
- **Future**: React Router for production
- **Implementation**: State-based view switching in App.jsx

### Gap 11: Frontend State Management
- **Approach**: React Context (simple for assessment)
- **Future**: Zustand for production
- **Contexts**: AuthContext, GameStateContext

### Gap 12: Loading States
- **Components**: LoadingSpinner, Skeleton screens
- **Implementation**: useApiCall hook with loading state
- **UI**: Spinners during async operations, skeletons for data loading

### Gap 13: Error Boundaries
- **Implementation**: React Error Boundary component
- **Fallback**: Error display with reload button
- **Usage**: Wrap entire app, specific boundaries for game components

### Gap 14: Mobile Responsiveness
- **Approach**: Responsive CSS with media queries
- **Breakpoints**: Mobile (<480px), Tablet (480-768px), Desktop (>768px)
- **Touch**: Touch event handling, haptic feedback

### Gap 15: Logging Strategy
- **Library**: structlog with JSON format
- **Format**: JSON with timestamp, level, event, request_id
- **PII**: Redact emails, passwords in logs

### Gap 16: Monitoring
- **Approach**: Basic metrics logging (can add Prometheus later)
- **Metrics**: Request duration, error counts, queue depth
- **Health check**: Database/Redis latency checks

### Gap 17: Health Check Details
- **Endpoints**: /health, /health/ready, /health/live
- **Checks**: Database connectivity, Redis connectivity, Celery queue depth
- **Response**: Status, timestamp, detailed checks with latency

### Gap 18: Graceful Shutdown
- **Implementation**: FastAPI lifespan manager
- **Handlers**: SIGTERM, SIGINT
- **Process**: Stop accepting requests, wait 5s for in-flight, close connections

### Gap 19: Request Timeouts
- **Configuration**: DB query 10s, Redis 5s, API request 30s
- **Implementation**: asyncio.wait_for with timeout
- **Frontend**: fetch with AbortController, 30s timeout

### Gap 20: Test Data Strategy
- **Backend**: pytest-factoryboy for test data generation
- **Frontend**: Mock data utilities
- **Cleanup**: Auto-rollback after each test

---

## Outbox Pattern

### Purpose
Ensure reliable, atomic event publishing for leaderboard updates and UI notifications.

### Architecture
```
Game Completion
    ↓
1. Update Game Status (Transaction Start)
    ↓
2. Write Outbox Event (Same Transaction)
    ↓
3. Commit Transaction
    ↓
[Outbox Event Persisted]
    ↓
Background Poller (every 5s)
    ↓
4. Read Unprocessed Events
    ↓
5. Process Event (Update Leaderboard, Stats)
    ↓
6. Mark Event as Completed
    ↓
[UI Notified via SSE]
```

### Database Schema
```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX idx_outbox_status_created ON outbox_events(status, created_at);
CREATE INDEX idx_outbox_aggregate ON outbox_events(aggregate_type, aggregate_id);
```

### Event Types
- `game_completed`: Update stats, leaderboards, invalidate cache
- `user_stats_updated`: Invalidate cache, notify UI
- `leaderboard_updated`: Invalidate cache, notify UI

### Components
- OutboxRepository: Database operations
- OutboxPublisher: Write events in transaction
- Event Handlers: Process events (stats, leaderboards)
- OutboxPoller: Background poller (5s interval)
- SSE Endpoint: Real-time updates to frontend

### Impact
- Backend: ~470 lines (5 components, 1 table)
- Frontend: ~120 lines (SSE hook, endpoint)
- Timeline: +2 days

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  GameBoard   │  │   Keyboard   │  │ GameControls │  │ Auth     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  │ Provider │ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┘  └──────────┘ │
│  │  WordLength  │  │ GameState    │  ┌──────────────┐               │
│  │  Selector    │  │  Display     │  │ Leaderboard  │               │
│  └──────────────┘  └──────────────┘  │  Display     │               │
│  ┌──────────────┐  ┌──────────────┘  └──────────────┘               │
│  │ Profile      │  │ Stats Display    │                                 │
│  │  View        │  └──────────────────┘                                 │
│  └──────────────┘  ┌──────────────┐                                    │
│                    │ Loading      │                                    │
│                    │ Spinner      │                                    │
│                    └──────────────┘                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Error        │  │ Skeleton     │  │ Pagination  │               │
│  │ Boundary     │  │ Screens      │  │ Controls    │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                 Client-Side Validation Layer                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │Word      │ │Guess     │ │Input     │ │Optimistic│        │  │
│  │  │Validator │ │Validator │ │Sanitizer │ │UI Update │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ HTTP/REST API (JWT Auth)
                               │ X-Request-ID header
                               │
┌──────────────────────────────┴────────────────────────────────────────┐
│                    Backend (FastAPI)                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                   API Layer (with Auth Middleware)              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Game      │ │Auth      │ │User      │ │Leaderboard│     │  │
│  │  │Router    │ │Router    │ │Router    │ │Router    │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │  │
│  │  │Health    │ │Error     │ │SSE       │                    │  │
│  │  │Router    │ │Handler   │ │Router    │                    │  │
│  │  └──────────┘  └──────────┘  └──────────┘                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  Middleware Layer                             │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Request   │ │Rate      │ │Auth      │ │Error     │     │  │
│  │  │ID        │ │Limit     │ │Middleware│ │Handler   │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  Service Layer                                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Game      │ │User      │ │Stats     │ │Leaderboard│     │  │
│  │  │Service   │ │Service   │ │Service   │ │Service   │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │  │
│  │  │Auth      │ │WordOfDay │ │Outbox    │                    │  │
│  │  │Service   │ │Service   │ │Publisher │                    │  │
│  │  └──────────┘  └──────────┘  └──────────┘                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                Business Logic Layer                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Feedback  │ │Game      │ │Word      │ │Stats     │     │  │
│  │  │Engine    │ │State     │ │Selector  │ │Calculator │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  Cache Layer (Redis)                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Game      │ │WordOfDay │ │User      │ │Idempotency│     │  │
│  │  │Cache     │ │Cache     │ │Session   │ │Keys      │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  Data Layer                                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Game      │ │User      │ │Word      │ │Outbox    │     │  │
│  │  │Repository│ │Repository│ │Dictionary│ │Repository│     │  │
│  │  │(DB)      │ │(DB)      │ │(File)    │ │(DB)      │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  Persistence Layer (PostgreSQL)               │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Games     │ │Users     │ │Game      │ │User      │     │  │
│  │  │Table     │ │Table     │ │Attempts  │ │Stats     │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │  ┌──────────┐  ┌──────────┐                                    │  │
│  │  │Outbox    │ │User      │                                    │  │
│  │  │Events    │ │Sessions  │                                    │  │
│  │  └──────────┘  └──────────┘                                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Backend Components (40 total)

### Core Components (18)

1. **Authentication** - JWT tokens, bcrypt, session management
2. **User Repository** - User CRUD operations
3. **Word Dictionary** - Embedded word list, filtered by length
4. **Word Selector** - Random/deterministic word selection
5. **Word of the Day** - UTC-based daily challenge
6. **Feedback Engine** - Multi-pass algorithm for duplicate letters
7. **Game State** - In-memory game state management
8. **Game Repository** - PostgreSQL + Redis caching
9. **Word Validator** - Dictionary validation
10. **Idempotency** - Hierarchical scoped keys
11. **Async Write Queue** - Background task processing
12. **Stats Calculator** - Per-word-length distribution
13. **Stats Service** - Cache invalidation, updates
14. **Leaderboard Service** - Event-driven + periodic
15. **Game Service** - Orchestration with outbox publishing
16. **API Layer** - Routers, middleware, error handling
17. **Models** - Pydantic schemas
18. **Database** - SQLAlchemy models, Alembic migrations

### Cross-Cutting Components (12)

19. **Configuration** - Settings with pydantic-settings
20. **Logging** - Structlog with JSON format
21. **Monitoring** - Basic metrics collection
22. **Health Check** - Detailed health checks
23. **Lifecycle** - Graceful shutdown
24. **Request ID Middleware** - Distributed tracing
25. **Rate Limiting** - Redis-based sliding window
26. **Error Handler** - Standardized error responses
27. **Outbox Repository** - Event persistence
28. **Outbox Publisher** - Event publishing in transaction
29. **Outbox Poller** - Background event processing
30. **Event Handlers** - Game completed, stats updated, leaderboard updated

### Test Support (10)

31. **Test Factories** - pytest-factoryboy
32. **Test Fixtures** - Test database/Redis setup
33. **Test Utilities** - Mock data
34. **Unit Tests** - Component isolation
35. **Integration Tests** - Real dependencies
36. **E2E Tests** - Full request lifecycle
37. **API Tests** - Request/response validation
38. **Performance Tests** - Load testing
39. **Security Tests** - Vulnerability scanning
40. **Migration Tests** - Schema validation

---

## Frontend Components (21 total)

### Core Components (11)

1. **API Client** - HTTP communication, retry logic, idempotency
2. **Auth Context** - Authentication state, sessionStorage
3. **Game State Context** - Game state management
4. **Offline Sync Manager** - Offline queue, server-wins sync
5. **Client Validation** - Word, guess, input validation
6. **Game Mode Selector** - Mode selection UI
7. **Word Length Selector** - Length selection (5-8)
8. **Game Board** - Grid display with feedback
9. **Keyboard** - On-screen keyboard
10. **Game Controls** - New game, reset
11. **Feedback Display** - Win/loss messages

### UI Components (5)

12. **Stats Display** - User statistics visualization
13. **Leaderboard Display** - Leaderboard with SSE updates
14. **Profile View** - User profile and history
15. **Auth UI** - Login, register forms
16. **App** - Main orchestrator with conditional routing

### Cross-Cutting Components (5)

17. **Loading Spinner** - Loading indicators
18. **Skeleton Screens** - Data loading placeholders
19. **Error Boundary** - React error boundary
20. **Pagination Controls** - Page navigation
21. **SSE Hook** - Server-sent events client

---

## Database Schema

### Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
```

#### user_sessions
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'user' or 'guest'
    device_info JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(refresh_token_hash);
```

#### games
```sql
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    game_mode VARCHAR(50) NOT NULL, -- 'word_of_day', 'custom', 'practice'
    word_length INTEGER NOT NULL CHECK (word_length BETWEEN 5 AND 8),
    target_word VARCHAR(8) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'in_progress', 'won', 'lost'
    max_turns INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_games_user_created ON games(user_id, created_at DESC);
```

#### game_attempts
```sql
CREATE TABLE game_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    guess VARCHAR(8) NOT NULL,
    feedback JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, attempt_number)
);

CREATE INDEX idx_attempts_game ON game_attempts(game_id, attempt_number);
```

#### user_stats
```sql
CREATE TABLE user_stats (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    games_lost INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    avg_guesses_to_win DECIMAL(3, 2),
    guess_distribution JSONB DEFAULT '{}', -- {5: {1: count, ...}, 6: {...}, ...}
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stats_user ON user_stats(user_id);
```

#### word_of_day_attempts
```sql
CREATE TABLE word_of_day_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    attempt_date DATE NOT NULL,
    game_id UUID REFERENCES games(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, attempt_date)
);

CREATE INDEX idx_wod_user_date ON word_of_day_attempts(user_id, attempt_date);
```

#### outbox_events
```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    CONSTRAINT check_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_outbox_status_created ON outbox_events(status, created_at);
CREATE INDEX idx_outbox_aggregate ON outbox_events(aggregate_type, aggregate_id);
```

---

## API Design

### Authentication Endpoints

#### POST /api/auth/register
- Request: `{ email, password, username }`
- Response: `{ user_id, email, username, access_token, refresh_token }`

#### POST /api/auth/login
- Request: `{ email, password }`
- Response: `{ user_id, email, username, access_token, refresh_token }`

#### POST /api/auth/guest
- Request: (empty)
- Response: `{ guest_id, access_token, refresh_token }` (6-hour TTL)

#### POST /api/auth/refresh
- Request: `{ refresh_token }` (or httpOnly cookie)
- Response: `{ access_token }`

#### POST /api/auth/logout
- Headers: `Authorization: Bearer {token}`
- Response: `{ message: "Logged out" }`
- Sets: `refresh_token` cookie deletion

### Game Endpoints

#### POST /api/games
- Headers: `Authorization: Bearer {token}`, `X-Request-ID: {uuid}`
- Request: `{ game_mode: "custom"|"word_of_day"|"practice", word_length: 5 }`
- Response: `{ game_id, game_mode, word_length, max_turns, status, guesses: [], feedback: [], created_at }`

#### POST /api/games/{game_id}/guesses
- Headers: `Authorization: Bearer {token}`, `X-Request-ID: {uuid}`, `Idempotency-Key: {uuid}`
- Request: `{ guess: "APPLE" }`
- Response: `{ game_id, status, guesses, feedback, remaining_turns }`

#### GET /api/games/{game_id}
- Headers: `Authorization: Bearer {token}`, `X-Request-ID: {uuid}`
- Response: Full game state

#### GET /api/games
- Headers: `Authorization: Bearer {token}`, `X-Request-ID: {uuid}`
- Query: `?limit=20&offset=0&game_mode=custom`
- Response: `{ games: [...], total, limit, offset }`

### User Endpoints

#### GET /api/users/me
- Headers: `Authorization: Bearer {token}`, `X-Request-ID: {uuid}`
- Response: `{ user_id, email, username, created_at }`

#### GET /api/users/me/stats
- Headers: `Authorization: Bearer {token}`, `X-Request-ID: {uuid}`
- Response: `{ games_played, games_won, games_lost, win_rate, current_streak, best_streak, avg_guesses_to_win, guess_distribution }`

#### GET /api/users/me/games
- Headers: `Authorization: Bearer {token}`, `X-Request-ID: {uuid}`
- Query: `?limit=20&offset=0`
- Response: `{ games: [...], total, limit, offset }`

### Leaderboard Endpoints

#### GET /api/leaderboards/global
- Headers: `Authorization: Bearer {token}` (optional for guests), `X-Request-ID: {uuid}`
- Query: `?limit=10&sort_by=win_rate`
- Response: `{ leaderboard: [...], current_user_rank }`

#### GET /api/leaderboards/daily
- Headers: `Authorization: Bearer {token}` (optional for guests), `X-Request-ID: {uuid}`
- Query: `?date=2024-01-01&limit=10`
- Response: `{ date, leaderboard: [...], current_user_rank }`

### SSE Endpoint

#### GET /api/events
- Headers: `Authorization: Bearer {token}`
- Response: Server-sent events stream
- Events: `game_completed`, `user_stats_updated`, `leaderboard_updated`

### Health Endpoints

#### GET /health
- Response: `{ status, timestamp, checks: { database: {status, latency_ms}, redis: {status, latency_ms}, celery: {status, queue_depth} } }`

#### GET /health/ready
- Response: Same as /health, returns 503 if not ready

#### GET /health/live
- Response: `{ status: "alive", timestamp }`

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_GUESS",
    "message": "Word not in dictionary",
    "details": {
      "field": "guess",
      "value": "ABCDE"
    },
    "request_id": "uuid",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

---

## Configuration Management

### Environment Variables

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_QUERY_TIMEOUT: int = 10

    # Redis
    REDIS_URL: str
    REDIS_TIMEOUT: int = 5

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL: int = 900  # 15 minutes
    REFRESH_TOKEN_TTL: int = 604800  # 7 days (user), 21600  # 6 hours (guest)

    # Word of the Day
    WORD_OF_DAY_TIMEZONE: str = "UTC"
    WORD_OF_DAY_WORD_LENGTH: int = 5

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_MINUTE_IP: int = 10
    RATE_LIMIT_AUTH_ENDPOINTS: int = 5

    # Timeouts
    API_REQUEST_TIMEOUT: int = 30

    # Outbox
    OUTBOX_POLL_INTERVAL: int = 5
    OUTBOX_BATCH_SIZE: int = 100
    OUTBOX_RETENTION_DAYS: int = 7

    class Config:
        env_file = ".env"

settings = Settings()
```

### .env.example

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/wordle
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key-here
WORD_OF_DAY_TIMEZONE=UTC
```

---

## Testing Strategy

### Backend Tests

**Unit Tests**: pytest with pytest-asyncio
- Component isolation with mocks
- ~90% code coverage target

**Integration Tests**: Real dependencies
- Test database (SQLite)
- Test Redis (in-memory)
- ~70% coverage

**E2E Tests**: Full request lifecycle
- TestClient for FastAPI
- Real database transactions
- ~50% coverage

### Frontend Tests

**Unit Tests**: Vitest + React Testing Library
- Component testing
- Hook testing
- ~80% coverage

**E2E Tests**: Playwright
- Full user flows
- Cross-browser testing
- ~40% coverage

### Test Data

**Backend**: pytest-factoryboy
- UserFactory, GameFactory, GameAttemptFactory
- Auto-cleanup between tests

**Frontend**: Mock utilities
- mockGame, mockUser, mockStats, mockLeaderboard

---

## Implementation Phases

### Phase 0: Foundation (Must Do Before Coding) - 3-4 days

**Backend**:
1. Configuration Management (Settings class)
2. Database Migrations (Alembic setup)
3. Test Environment Setup (test DB/Redis)
4. API Error Response Standards
5. Health Check Details
6. Logging Strategy (structlog)
7. Request ID Middleware
8. Graceful Shutdown
9. Request Timeout Handling

**Frontend**:
10. Frontend Routing (conditional rendering)
11. Frontend State Management (React Context)
12. Loading States (spinner, skeleton)
13. Error Boundary
14. Mobile Responsiveness (CSS)
15. Test Data Strategy (mocks)

### Phase 1: Backend Core (5-7 days)

16. Database Schema
17. Word Dictionary
18. Word Selector
19. Feedback Engine (multi-pass algorithm)
20. Game State
21. Game Repository (PostgreSQL + Redis)
22. Word Validator
23. Authentication (JWT, bcrypt, sessions)
24. User Repository
25. Word of the Day (UTC-based)
26. Idempotency (hierarchical scope)
27. Game Service (orchestration)
28. Models (Pydantic schemas)

### Phase 2: Backend Advanced (4-5 days)

29. Outbox Pattern (repository, publisher, poller, handlers)
30. Stats Calculator (per-word-length distribution)
31. Stats Service (cache invalidation)
32. Leaderboard Service (event-driven + periodic)
33. Async Write Queue (background tasks)
34. Rate Limiting (Redis-based)
35. API Layer (routers, middleware)
36. Monitoring (basic metrics)

### Phase 3: Frontend Core (4-5 days)

37. API Client (with retry, idempotency, request ID)
38. Auth Context (sessionStorage)
39. Game State Context
40. Client-Side Validation
41. Game Mode Selector
42. Word Length Selector
43. Game Board
44. Keyboard
45. Game Controls
46. Feedback Display

### Phase 4: Frontend Advanced (3-4 days)

47. Stats Display
48. Leaderboard Display (with SSE)
49. Profile View
50. Auth UI (login, register)
51. Offline Sync Manager (server-wins)
52. Pagination Controls
53. SSE Hook

### Phase 5: Integration & Polish (3-4 days)

54. App Component (orchestration)
55. E2E Tests
56. Performance Optimization
57. Security Audit
58. Documentation
59. Deployment Preparation

---

## Total Timeline Estimate

- **Phase 0**: 3-4 days
- **Phase 1**: 5-7 days
- **Phase 2**: 4-5 days
- **Phase 3**: 4-5 days
- **Phase 4**: 3-4 days
- **Phase 5**: 3-4 days

**Total**: 22-29 days (4-6 weeks)

**Risk Buffer**: +1 week for unexpected issues

**Final Estimate**: 5-7 weeks for full implementation

---

## Dependencies

### Backend
```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.0
asyncpg>=0.29.0
redis>=5.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
structlog>=23.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-factoryboy>=3.3.0
faker>=20.0.0
httpx>=0.25.0
```

### Frontend
```json
{
  "dependencies": {
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  },
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.1.0",
    "@testing-library/user-event": "^14.5.0",
    "@vitejs/plugin-react": "^5.1.1",
    "vitest": "^1.0.0",
    "jsdom": "^23.0.0",
    "playwright": "^1.40.0",
    "eslint": "^9.39.1",
    "eslint-plugin-react-hooks": "^7.0.1",
    "eslint-plugin-react-refresh": "^0.4.24"
  }
}
```

---

## Deployment Considerations

### Backend
- Docker containerization
- Environment variables for configuration
- Health check endpoints for load balancers
- Graceful shutdown handling
- Database connection pooling
- Redis connection pooling
- Structured logging (JSON format)
- SQLite for local dev, PostgreSQL for production

### Frontend
- Static file generation (Vite build)
- Responsive design (mobile-first)
- Service worker for offline support (optional)
- CDN deployment for static assets (optional)

### Infrastructure
- PostgreSQL database (managed or self-hosted)
- Redis cache (managed or self-hosted)
- Load balancer for API servers
- Horizontal scaling for API workers
- Background task processing (outbox poller)
- Monitoring and alerting (basic metrics, can add Prometheus later)
- Backup strategy (daily backups, 30-day retention)

---

## Future Enhancements (Out of Scope)

- Real-time multiplayer mode
- Friend system and social features
- Custom word lists (user-created)
- Tournament mode
- Achievements and badges
- Dark mode
- Mobile app (React Native)
- Analytics and A/B testing
- Machine learning for word suggestions
- Voice input for guesses
- Accessibility improvements (screen readers)
- Password reset flow (email service)
- Redis pub/sub for outbox (instead of polling)
- Message queue (RabbitMQ, Kafka)
- Full event sourcing
- React Router (upgrade from conditional rendering)
- Zustand (upgrade from React Context)
- Cursor-based pagination (upgrade from offset/limit)
- Prometheus metrics (upgrade from basic logging)
- CI/CD pipeline
- Security testing
- Compliance documents

---

## Conclusion

This consolidated design provides a production-ready blueprint for the Wordle full-stack application with:

- **40 backend components** (18 core + 12 cross-cutting + 10 test)
- **21 frontend components** (11 core + 5 UI + 5 cross-cutting)
- **~10,000 lines of code** estimated
- **5-7 weeks timeline** with risk buffer
- **Production-grade features**: Outbox pattern, distributed tracing, rate limiting, health checks, graceful shutdown
- **Assessment-appropriate simplifications**: Conditional routing, React Context, offset/limit pagination, basic monitoring

The design balances production readiness with assessment feasibility, using simpler approaches for assessment (conditional rendering, React Context) while documenting production upgrades (React Router, Zustand, cursor-based pagination).
