# Wordle Full Stack Application - Design Document

## Overview

This document outlines the production-level design for a full-stack Wordle application with a FastAPI backend and React frontend. The design follows a component-based architecture with smallest possible logical components, each with infra, implementation, and test layers.

## Expanded Requirements

### Core Features
1. **User Authentication**
   - Sign up / Sign in with email/password
   - Guest mode (anonymous play without account)
   - Session management with JWT tokens
   - Password reset flow

2. **Game Modes**
   - **Word of the Day**: Daily challenge, same word for all users, one attempt per day
   - **Custom Games**: Random words, configurable length (5-8), unlimited plays
   - **Practice Mode**: No persistence, purely for learning

3. **User Profiles & Stats**
   - Win/loss ratio
   - Current streak
   - Best streak
   - Average guesses to win
   - Distribution of guesses (won in 1, 2, 3, 4, 5, 6 turns)
   - Total games played
   - Historical attempts viewable

4. **Leaderboards**
   - Global leaderboard (by win rate, streaks)
   - Daily leaderboard (word of the day rankings)
   - Friends leaderboard (optional)

5. **Persistence Strategy**
   - Write-through cache with async persistence
   - In-memory cache for hot data (current game state, word of the day)
   - Persistent database for long-term storage
   - Handle disconnection/crash scenarios

6. **Idempotency**
   - All user actions idempotent via unique request IDs
   - Deduplication of duplicate submissions
   - Safe retry on network failures

7. **Validation Strategy**
   - Frontend validation for immediate feedback (optimistic UI)
   - Backend validation as source of truth
   - Async persistence with conflict resolution
   - Handle sync on reconnection

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
│                    │ Offline      │                                    │
│                    │ Sync Manager │                                    │
│                    └──────────────┘                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                 Client-Side Validation Layer                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │Word      │ │Guess     │ │Input     │ │Optimistic│        │  │
│  │  │Validator │ │Validator │ │Sanitizer │ │UI Update │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ HTTP/REST API (JWT Auth)
                               │
┌──────────────────────────────┴────────────────────────────────────────┐
│                    Backend (FastAPI)                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                   API Layer (with Auth Middleware)              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Game      │ │Auth      │ │User      │ │Leaderboard│     │  │
│  │  │Router    │ │Router    │ │Router    │ │Router    │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │  ┌──────────┐  ┌──────────┐                                    │  │
│  │  │Health    │ │Error     │                                    │  │
│  │  │Router    │ │Handler   │                                    │  │
│  │  └──────────┘  └──────────┘                                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  Service Layer                                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Game      │ │User      │ │Stats     │ │Leaderboard│     │  │
│  │  │Service   │ │Service   │ │Service   │ │Service   │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │  │
│  │  │Auth      │ │WordOfDay │ │Idempotency│                    │  │
│  │  │Service   │ │Service   │ │Service    │                    │  │
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
│  │  │Game      │ │User      │ │Word      │ │Async     │     │  │
│  │  │Repository│ │Repository│ │Dictionary│ │Write     │     │  │
│  │  │(DB)      │ │(DB)      │ │(File)    │ │Queue     │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                  Persistence Layer (PostgreSQL)               │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Games     │ │Users     │ │Game      │ │User      │     │  │
│  │  │Table     │ │Table     │ │Attempts  │ │Stats     │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

### Write Path (Async Persistence)
```
User Action
    ↓
Frontend Validation (Optimistic UI Update)
    ↓
API Request (with idempotency key)
    ↓
Backend Validation
    ↓
Write to Cache (Redis) - Immediate
    ↓
Enqueue Async Write Task
    ↓
Write to Database (PostgreSQL) - Background
    ↓
Sync Status to Client
```

### Read Path (Cache-Aside)
```
Client Request
    ↓
Check Cache (Redis)
    ↓
Cache Hit? → Return Data
    ↓ No
Query Database (PostgreSQL)
    ↓
Write to Cache
    ↓
Return Data
```

### Reconnection/Sync Flow
```
Client Reconnects
    ↓
Request Sync (last known state timestamp)
    ↓
Backend Returns Deltas (missed writes)
    ↓
Client Merges State
    ↓
Client Resubmits Pending Actions (with idempotency keys)
```

## Backend Component Breakdown

### 1. Authentication Component
**Purpose**: Handle user authentication and authorization

**Sub-components**:
- `AuthRepository` (Infra - No Op)
  - Interface for user authentication operations
- `PostgresAuthRepository` (Implementation)
  - Store/retrieve user credentials (hashed passwords)
  - JWT token generation and validation
  - Session management
- `AuthService` (Implementation)
  - Register new users
  - Authenticate users
  - Validate JWT tokens
  - Password reset flow
- `AuthTests` (Tests)
  - Unit: Test auth logic with mocked repository
  - Integ: Test auth with real PostgreSQL
  - E2E: Test full auth flow

**Files**:
```
backend/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── auth_repository.py  # Interface
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   ├── postgres_auth_repository.py
│   │   │   └── auth_service.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_auth.py
│   │       ├── test_integ_auth.py
│   │       └── test_e2e_auth.py
```

### 2. User Repository Component
**Purpose**: Manage user data and profiles

**Sub-components**:
- `UserRepository` (Infra - No Op)
  - Interface for user CRUD operations
- `PostgresUserRepository` (Implementation)
  - Create/read/update user profiles
  - Store user settings and preferences
- `UserTests` (Tests)
  - Unit: Test user operations with mocks
  - Integ: Test with PostgreSQL
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── user/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── user_repository.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── postgres_user_repository.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_user.py
│   │       └── test_integ_user.py
```

### 3. Word Dictionary Component
**Purpose**: Manage word list for validation and target word selection

**Sub-components**:
- `WordDictionaryRepository` (Infra - No Op)
  - Interface for loading and querying words
- `FileWordDictionary` (Implementation)
  - Loads words from embedded JSON file
  - Filters by length (5-8 letters)
  - Excludes plural words
  - Cached in memory after load
- `WordDictionaryTests` (Tests)
  - Unit: Test word loading, filtering, length validation
  - Integ: Test word dictionary initialization
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── word_dictionary/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── word_dictionary_repository.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── file_word_dictionary.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_word_dictionary.py
│   │       └── test_integ_word_dictionary.py
```

### 4. Word Selector Component
**Purpose**: Select random target words of specified length

**Sub-components**:
- `WordSelector` (Infra - No Op)
  - Interface for selecting target words
- `RandomWordSelector` (Implementation)
  - Selects random word from dictionary of specified length
  - For Word of the Day: deterministic based on date
  - For Custom Games: random selection
- `WordSelectorTests` (Tests)
  - Unit: Test random selection, length filtering, date-based selection
  - Integ: Test integration with word dictionary
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── word_selector/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── word_selector.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── random_word_selector.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_word_selector.py
│   │       └── test_integ_word_selector.py
```

### 5. Word of the Day Component
**Purpose**: Manage daily challenge word

**Sub-components**:
- `WordOfDayService` (Implementation)
  - Determine word of the day based on date
  - Cache word of the day in Redis (24h TTL)
  - Validate one attempt per day per user
- `WordOfDayTests` (Tests)
  - Unit: Test date-based word selection
  - Integ: Test with Redis cache
  - E2E: Test full word of the day flow

**Files**:
```
backend/
├── app/
│   ├── word_of_day/
│   │   ├── __init__.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── word_of_day_service.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_word_of_day.py
│   │       ├── test_integ_word_of_day.py
│   │       └── test_e2e_word_of_day.py
```

### 6. Feedback Engine Component
**Purpose**: Calculate letter feedback (green/yellow/gray) for guesses

**Sub-components**:
- `FeedbackEngine` (Infra - No Op)
  - Interface for calculating feedback
- `StandardFeedbackEngine` (Implementation)
  - Implements Wordle feedback rules
  - Handles duplicate letters correctly
- `FeedbackEngineTests` (Tests)
  - Unit: Test all feedback scenarios
  - Integ: N/A
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── feedback_engine/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── feedback_engine.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── standard_feedback_engine.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_unit_feedback_engine.py
```

### 7. Game State Component
**Purpose**: Manage game state and validation rules

**Sub-components**:
- `GameState` (Infra - No Op)
  - Interface for game state operations
- `InMemoryGameState` (Implementation)
  - Stores game ID, target word, guesses, feedback
  - Tracks remaining turns (N+1 where N = word length)
  - Validates game completion (win/loss)
- `GameStateTests` (Tests)
  - Unit: Test state transitions, validation, completion detection
  - Integ: N/A
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── game_state/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── game_state.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── in_memory_game_state.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_unit_game_state.py
```

### 8. Game Repository Component
**Purpose**: Persist and retrieve game data

**Sub-components**:
- `GameRepository` (Infra - No Op)
  - Interface for game CRUD operations
- `PostgresGameRepository` (Implementation)
  - Persist games to PostgreSQL
  - Retrieve game history
  - Query user's games
- `GameCache` (Implementation)
  - Redis cache for active games
  - TTL: 24 hours for completed games, 7 days for in-progress
- `GameRepositoryTests` (Tests)
  - Unit: Test with mocked dependencies
  - Integ: Test with PostgreSQL and Redis
  - E2E: Test full persistence flow

**Files**:
```
backend/
├── app/
│   ├── game_repository/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── game_repository.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   ├── postgres_game_repository.py
│   │   │   └── game_cache.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_game_repository.py
│   │       ├── test_integ_game_repository.py
│   │       └── test_e2e_game_repository.py
```

### 9. Word Validator Component
**Purpose**: Validate that guesses are valid words

**Sub-components**:
- `WordValidator` (Infra - No Op)
  - Interface for word validation
- `DictionaryWordValidator` (Implementation)
  - Checks if word exists in dictionary
  - Validates word length matches game configuration
- `WordValidatorTests` (Tests)
  - Unit: Test validation logic
  - Integ: Test integration with word dictionary
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── word_validator/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── word_validator.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── dictionary_word_validator.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_word_validator.py
│   │       └── test_integ_word_validator.py
```

### 10. Idempotency Component
**Purpose**: Ensure idempotent operations

**Sub-components**:
- `IdempotencyRepository` (Infra - No Op)
  - Interface for idempotency key storage
- `RedisIdempotencyRepository` (Implementation)
  - Store request/response pairs by idempotency key
  - TTL: 24 hours
  - Check for existing key before processing
- `IdempotencyService` (Implementation)
  - Generate/check idempotency keys
  - Return cached response if key exists
  - Store new responses
- `IdempotencyTests` (Tests)
  - Unit: Test idempotency logic
  - Integ: Test with Redis
  - E2E: Test idempotency in API calls

**Files**:
```
backend/
├── app/
│   ├── idempotency/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── idempotency_repository.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   ├── redis_idempotency_repository.py
│   │   │   └── idempotency_service.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_idempotency.py
│   │       ├── test_integ_idempotency.py
│   │       └── test_e2e_idempotency.py
```

### 11. Async Write Queue Component
**Purpose**: Handle async persistence to database

**Sub-components**:
- `AsyncWriteQueue` (Implementation)
  - Queue tasks for async database writes
  - Background worker processes queue
  - Retry logic for failed writes
  - Dead letter queue for permanently failed writes
- `AsyncWriteTests` (Tests)
  - Unit: Test queue operations
  - Integ: Test with real worker
  - E2E: Test async write flow

**Files**:
```
backend/
├── app/
│   ├── async_write/
│   │   ├── __init__.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── async_write_queue.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_async_write.py
│   │       └── test_integ_async_write.py
```

### 12. Stats Calculator Component
**Purpose**: Calculate user statistics

**Sub-components**:
- `StatsCalculator` (Implementation)
  - Calculate win/loss ratio
  - Calculate streaks (current, best)
  - Calculate average guesses to win
  - Calculate guess distribution
- `StatsTests` (Tests)
  - Unit: Test all stat calculations
  - Integ: N/A
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── stats/
│   │   ├── __init__.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── stats_calculator.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_unit_stats.py
```

### 13. Stats Service Component
**Purpose**: Manage user statistics

**Sub-components**:
- `StatsService` (Implementation)
  - Update stats after game completion
  - Retrieve user stats
  - Cache stats in Redis
- `StatsServiceTests` (Tests)
  - Unit: Test stats service logic
  - Integ: Test with repository and cache
  - E2E: Test stats updates through game flow

**Files**:
```
backend/
├── app/
│   ├── stats_service/
│   │   ├── __init__.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── stats_service.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_stats_service.py
│   │       ├── test_integ_stats_service.py
│   │       └── test_e2e_stats_service.py
```

### 14. Leaderboard Service Component
**Purpose**: Manage leaderboards

**Sub-components**:
- `LeaderboardService` (Implementation)
  - Calculate global leaderboard rankings
  - Calculate daily leaderboard rankings
  - Cache leaderboards in Redis (refresh every 5 minutes)
- `LeaderboardTests` (Tests)
  - Unit: Test leaderboard calculation logic
  - Integ: Test with cache
  - E2E: Test leaderboard API

**Files**:
```
backend/
├── app/
│   ├── leaderboard/
│   │   ├── __init__.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── leaderboard_service.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_leaderboard.py
│   │       ├── test_integ_leaderboard.py
│   │       └── test_e2e_leaderboard.py
```

### 15. Game Service Component
**Purpose**: Orchestrate game operations

**Sub-components**:
- `GameService` (Implementation)
  - Creates new games (custom, word of the day, practice)
  - Processes guesses and returns feedback
  - Retrieves game state
  - Enforces game rules
  - Triggers async writes and stats updates
- `GameServiceTests` (Tests)
  - Unit: Test service logic with mocked dependencies
  - Integ: Test service with real dependencies
  - E2E: Test full game flow

**Files**:
```
backend/
├── app/
│   ├── game_service/
│   │   ├── __init__.py
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── game_service.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_game_service.py
│   │       ├── test_integ_game_service.py
│   │       └── test_e2e_game_service.py
```

### 16. API Layer Components
**Purpose**: Expose REST endpoints

**Sub-components**:
- `GameRouter` (Implementation)
  - POST /api/games - Create new game
  - POST /api/games/{game_id}/guesses - Submit guess
  - GET /api/games/{game_id} - Get game state
  - GET /api/games - List user's games
- `AuthRouter` (Implementation)
  - POST /api/auth/register - Register user
  - POST /api/auth/login - Login user
  - POST /api/auth/logout - Logout user
  - POST /api/auth/refresh - Refresh token
  - POST /api/auth/reset-password - Request password reset
- `UserRouter` (Implementation)
  - GET /api/users/me - Get current user profile
  - GET /api/users/me/stats - Get user stats
  - GET /api/users/me/games - Get user game history
  - PUT /api/users/me - Update user profile
- `LeaderboardRouter` (Implementation)
  - GET /api/leaderboards/global - Get global leaderboard
  - GET /api/leaderboards/daily - Get daily leaderboard
- `HealthRouter` (Implementation)
  - GET /health - Health check
- `ErrorHandler` (Implementation)
  - Global exception handling
  - Standardized error responses
- `AuthMiddleware` (Implementation)
  - JWT validation middleware
  - Guest mode support
- `APITests` (Tests)
  - Unit: Test request/response validation
  - Integ: Test API with real service layer
  - E2E: Test full request lifecycle

**Files**:
```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── game_router.py
│   │   │   ├── auth_router.py
│   │   │   ├── user_router.py
│   │   │   ├── leaderboard_router.py
│   │   │   └── health_router.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth_middleware.py
│   │   │   └── error_handler.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_api.py
│   │       ├── test_integ_api.py
│   │       └── test_e2e_api.py
```

### 17. Models Component
**Purpose**: Define data structures and schemas

**Sub-components**:
- `GameModels` (Implementation)
  - Pydantic models for game operations
- `AuthModels` (Implementation)
  - Pydantic models for auth operations
- `UserModels` (Implementation)
  - Pydantic models for user operations
- `StatsModels` (Implementation)
  - Pydantic models for stats operations
- `ModelTests` (Tests)
  - Unit: Test model validation

**Files**:
```
backend/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── game_models.py
│   │   ├── auth_models.py
│   │   ├── user_models.py
│   │   ├── stats_models.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_unit_models.py
```

### 18. Database Component
**Purpose**: Database schema and migrations

**Sub-components**:
- `DatabaseSchema` (Implementation)
  - SQLAlchemy models for tables
  - Alembic migrations
- `DatabaseTests` (Tests)
  - Integ: Test schema migrations
  - E2E: N/A

**Files**:
```
backend/
├── app/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_integ_database.py
```

## Frontend Component Breakdown

### 1. API Client Component
**Purpose**: Handle HTTP communication with backend

**Sub-components**:
- `APIClient` (Implementation)
  - Methods for all API endpoints
  - Automatic JWT token attachment
  - Error handling and retry logic
  - Idempotency key generation
  - Offline queue for failed requests
- `APIClientTests` (Tests)
  - Unit: Test client with mocked fetch
  - Integ: Test client with mock server
  - E2E: Test with real backend

**Files**:
```
frontend/
├── src/
│   ├── api/
│   │   ├── apiClient.js
│   │   └── tests/
│   │       ├── apiClient.unit.test.js
│   │       ├── apiClient.integ.test.js
│   │       └── apiClient.e2e.test.js
```

### 2. Auth Context Component
**Purpose**: Manage authentication state

**Sub-components**:
- `AuthProvider` (Implementation)
  - React Context for auth state
  - State: user, token, isAuthenticated, isGuest
  - Actions: login, register, logout, guestLogin
  - JWT token storage (localStorage)
- `AuthContextTests` (Tests)
  - Unit: Test context provider and hooks
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── context/
│   │   ├── AuthContext.jsx
│   │   └── tests/
│   │       └── AuthContext.unit.test.jsx
```

### 3. Game State Context Component
**Purpose**: Manage global game state

**Sub-components**:
- `GameStateProvider` (Implementation)
  - React Context for game state
  - State: currentGame, guesses, feedback, gameStatus
  - Actions: createGame, submitGuess, resetGame
  - Optimistic updates with rollback on error
- `GameStateContextTests` (Tests)
  - Unit: Test context provider and hooks
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── context/
│   │   ├── GameStateContext.jsx
│   │   └── tests/
│   │       └── GameStateContext.unit.test.jsx
```

### 4. Offline Sync Manager Component
**Purpose**: Handle offline mode and sync

**Sub-components**:
- `OfflineSyncManager` (Implementation)
  - Detect online/offline status
  - Queue failed requests
  - Retry on reconnection
  - Resolve conflicts with server state
- `OfflineSyncTests` (Tests)
  - Unit: Test sync logic
  - Integ: N/A
  - E2E: Test offline/reconnect flow

**Files**:
```
frontend/
├── src/
│   ├── offline/
│   │   ├── offlineSyncManager.js
│   │   └── tests/
│   │       ├── offlineSyncManager.unit.test.js
│   │       └── offlineSyncManager.e2e.test.js
```

### 5. Client-Side Validation Component
**Purpose**: Validate input before sending to backend

**Sub-components**:
- `WordValidator` (Implementation)
  - Validate word length
  - Validate characters (letters only)
  - Check against local word list (subset)
- `GuessValidator` (Implementation)
  - Validate guess format
  - Validate guess not already submitted
- `InputSanitizer` (Implementation)
  - Sanitize user input
  - Prevent XSS
- `ClientValidationTests` (Tests)
  - Unit: Test all validation logic
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── validation/
│   │   ├── wordValidator.js
│   │   ├── guessValidator.js
│   │   ├── inputSanitizer.js
│   │   └── tests/
│   │       ├── validation.unit.test.js
```

### 6. Game Mode Selector Component
**Purpose**: Allow user to select game mode

**Sub-components**:
- `GameModeSelector` (Implementation)
  - UI: buttons for Word of the Day, Custom, Practice
  - Shows daily status for Word of the Day
- `GameModeSelectorTests` (Tests)
  - Unit: Test component rendering and selection
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── GameModeSelector/
│   │   │   ├── GameModeSelector.jsx
│   │   │   ├── GameModeSelector.css
│   │   │   └── tests/
│   │   │       └── GameModeSelector.unit.test.jsx
```

### 7. Word Length Selector Component
**Purpose**: Allow user to select word length (5-8)

**Sub-components**:
- `WordLengthSelector` (Implementation)
  - UI: dropdown or buttons for 5-8
  - Validation: ensure valid selection
- `WordLengthSelectorTests` (Tests)
  - Unit: Test component rendering and selection
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── WordLengthSelector/
│   │   │   ├── WordLengthSelector.jsx
│   │   │   ├── WordLengthSelector.css
│   │   │   └── tests/
│   │   │       └── WordLengthSelector.unit.test.jsx
```

### 8. Game Board Component
**Purpose**: Display grid of guesses with feedback

**Sub-components**:
- `GameBoard` (Implementation)
  - Renders N+1 rows (where N = word length)
  - Each row has N cells with letter and color
  - Animations for new guesses
  - Optimistic UI updates
- `GameBoardTests` (Tests)
  - Unit: Test rendering with various game states
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── GameBoard/
│   │   │   ├── GameBoard.jsx
│   │   │   ├── GameBoard.css
│   │   │   └── tests/
│   │   │       └── GameBoard.unit.test.jsx
```

### 9. Keyboard Component
**Purpose**: On-screen keyboard for entering guesses

**Sub-components**:
- `Keyboard` (Implementation)
  - QWERTY layout
  - Keys show feedback colors (green/yellow/gray) after guesses
  - Click handlers for letter entry
- `KeyboardTests` (Tests)
  - Unit: Test keyboard rendering and key press handling
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── Keyboard/
│   │   │   ├── Keyboard.jsx
│   │   │   ├── Keyboard.css
│   │   │   └── tests/
│   │   │       └── Keyboard.unit.test.jsx
```

### 10. Game Controls Component
**Purpose**: Start new game, reset, etc.

**Sub-components**:
- `GameControls` (Implementation)
  - "New Game" button
  - "Reset" button
  - Game mode selector integration
- `GameControlsTests` (Tests)
  - Unit: Test button rendering and click handlers
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── GameControls/
│   │   │   ├── GameControls.jsx
│   │   │   ├── GameControls.css
│   │   │   └── tests/
│   │   │       └── GameControls.unit.test.jsx
```

### 11. Feedback Display Component
**Purpose**: Show win/loss messages

**Sub-components**:
- `FeedbackDisplay` (Implementation)
  - Displays "You Won!" or "Game Over"
  - Shows the correct word on loss
  - Play again button
- `FeedbackDisplayTests` (Tests)
  - Unit: Test rendering for win/loss states
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── FeedbackDisplay/
│   │   │   ├── FeedbackDisplay.jsx
│   │   │   ├── FeedbackDisplay.css
│   │   │   └── tests/
│   │   │       └── FeedbackDisplay.unit.test.jsx
```

### 12. Stats Display Component
**Purpose**: Display user statistics

**Sub-components**:
- `StatsDisplay` (Implementation)
  - Display win/loss ratio
  - Display streaks
  - Display guess distribution graph
- `StatsDisplayTests` (Tests)
  - Unit: Test rendering with various stats
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── StatsDisplay/
│   │   │   ├── StatsDisplay.jsx
│   │   │   ├── StatsDisplay.css
│   │   │   └── tests/
│   │   │       └── StatsDisplay.unit.test.jsx
```

### 13. Leaderboard Display Component
**Purpose**: Display leaderboards

**Sub-components**:
- `LeaderboardDisplay` (Implementation)
  - Display global leaderboard
  - Display daily leaderboard
  - Tab switching between leaderboards
- `LeaderboardDisplayTests` (Tests)
  - Unit: Test rendering and tab switching
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── LeaderboardDisplay/
│   │   │   ├── LeaderboardDisplay.jsx
│   │   │   ├── LeaderboardDisplay.css
│   │   │   └── tests/
│   │   │       └── LeaderboardDisplay.unit.test.jsx
```

### 14. Profile View Component
**Purpose**: Display user profile and game history

**Sub-components**:
- `ProfileView` (Implementation)
  - Display user info
  - Display game history list
  - Link to individual games
- `ProfileViewTests` (Tests)
  - Unit: Test rendering
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── ProfileView/
│   │   │   ├── ProfileView.jsx
│   │   │   ├── ProfileView.css
│   │   │   └── tests/
│   │   │       └── ProfileView.unit.test.jsx
```

### 15. Keyboard Handler Component
**Purpose**: Handle physical keyboard input

**Sub-components**:
- `KeyboardHandler` (Implementation)
  - Listens for keydown events
  - Maps keys to game actions
  - Handles Enter (submit), Backspace (delete), letters
- `KeyboardHandlerTests` (Tests)
  - Unit: Test key mapping and event handling
  - Integ: N/A
  - E2E: N/A

**Files**:
```
frontend/
├── src/
│   ├── hooks/
│   │   ├── useKeyboardHandler.js
│   │   └── tests/
│   │       └── useKeyboardHandler.unit.test.js
```

### 16. Auth UI Components
**Purpose**: Authentication UI

**Sub-components**:
- `LoginForm` (Implementation)
  - Email/password input
  - Login button
  - Guest mode button
- `RegisterForm` (Implementation)
  - Email/password/confirm password input
  - Register button
- `AuthUITests` (Tests)
  - Unit: Test form rendering and validation
  - Integ: N/A
  - E2E: Test auth flow

**Files**:
```
frontend/
├── src/
│   ├── components/
│   │   ├── Auth/
│   │   │   ├── LoginForm.jsx
│   │   │   ├── RegisterForm.jsx
│   │   │   ├── Auth.css
│   │   │   └── tests/
│   │   │       ├── Auth.unit.test.jsx
│   │   │       └── Auth.e2e.test.jsx
```

### 17. App Component
**Purpose**: Main application orchestrator

**Sub-components**:
- `App` (Implementation)
  - Composes all components
  - Manages application-level state
  - Error boundaries
  - Route management (if using routing)
- `AppTests` (Tests)
  - Unit: Test component composition
  - Integ: N/A
  - E2E: Test full user flow

**Files**:
```
frontend/
├── src/
│   ├── App.jsx
│   ├── App.css
│   └── tests/
│       ├── App.unit.test.jsx
│       └── App.e2e.test.jsx
```

## Database Schema

### PostgreSQL Tables

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
```

#### game_attempts
```sql
CREATE TABLE game_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    guess VARCHAR(8) NOT NULL,
    feedback JSONB NOT NULL, -- Array of {letter, color}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, attempt_number)
);
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
    guess_distribution JSONB DEFAULT '{}', -- {1: count, 2: count, ...}
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
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
```

### Redis Cache Keys

#### Game Cache
```
game:{game_id} -> Game object (TTL: 24h for completed, 7d for in-progress)
user_games:{user_id} -> List of game IDs (TTL: 1h)
```

#### Word of the Day Cache
```
word_of_day:{date} -> Word (TTL: 48h)
user_wod_attempt:{user_id}:{date} -> Boolean (TTL: 48h)
```

#### User Session Cache
```
user_session:{user_id} -> User object (TTL: 24h)
user_stats:{user_id} -> Stats object (TTL: 1h)
```

#### Idempotency Cache
```
idempotency:{key} -> Response object (TTL: 24h)
```

#### Leaderboard Cache
```
leaderboard:global -> Leaderboard data (TTL: 5min)
leaderboard:daily:{date} -> Leaderboard data (TTL: 5min)
```

## API Design

### Authentication Endpoints

#### POST /api/auth/register
**Purpose**: Register a new user

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "username": "username"
}
```

**Response**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "access_token": "jwt_token",
  "refresh_token": "refresh_token"
}
```

#### POST /api/auth/login
**Purpose**: Login user

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "access_token": "jwt_token",
  "refresh_token": "refresh_token"
}
```

#### POST /api/auth/guest
**Purpose**: Start guest session

**Request**: (empty body)

**Response**:
```json
{
  "guest_id": "uuid",
  "access_token": "jwt_token"
}
```

#### POST /api/auth/refresh
**Purpose**: Refresh access token

**Request**:
```json
{
  "refresh_token": "refresh_token"
}
```

**Response**:
```json
{
  "access_token": "new_jwt_token"
}
```

### Game Endpoints

#### POST /api/games
**Purpose**: Create a new game

**Headers**: `Authorization: Bearer {token}`

**Request**:
```json
{
  "game_mode": "custom",
  "word_length": 5
}
```

**Response**:
```json
{
  "game_id": "uuid",
  "game_mode": "custom",
  "word_length": 5,
  "max_turns": 6,
  "status": "in_progress",
  "guesses": [],
  "feedback": [],
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Idempotency**: Include `Idempotency-Key: {uuid}` header

#### POST /api/games/{game_id}/guesses
**Purpose**: Submit a guess

**Headers**: `Authorization: Bearer {token}`, `Idempotency-Key: {uuid}`

**Request**:
```json
{
  "guess": "APPLE"
}
```

**Response**:
```json
{
  "game_id": "uuid",
  "status": "in_progress",
  "guesses": ["APPLE"],
  "feedback": [
    [
      {"letter": "A", "color": "green"},
      {"letter": "P", "color": "yellow"},
      {"letter": "P", "color": "gray"},
      {"letter": "L", "color": "gray"},
      {"letter": "E", "color": "gray"}
    ]
  ],
  "remaining_turns": 5
}
```

#### GET /api/games/{game_id}
**Purpose**: Get current game state

**Headers**: `Authorization: Bearer {token}`

**Response**:
```json
{
  "game_id": "uuid",
  "game_mode": "custom",
  "word_length": 5,
  "max_turns": 6,
  "status": "won",
  "guesses": ["APPLE", "PLEAD"],
  "feedback": [[...], [...]],
  "remaining_turns": 4,
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:00Z"
}
```

#### GET /api/games
**Purpose**: List user's games

**Headers**: `Authorization: Bearer {token}`

**Query Params**: `?limit=20&offset=0&game_mode=custom`

**Response**:
```json
{
  "games": [...],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

### User Endpoints

#### GET /api/users/me
**Purpose**: Get current user profile

**Headers**: `Authorization: Bearer {token}`

**Response**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /api/users/me/stats
**Purpose**: Get user statistics

**Headers**: `Authorization: Bearer {token}`

**Response**:
```json
{
  "games_played": 100,
  "games_won": 70,
  "games_lost": 30,
  "win_rate": 0.7,
  "current_streak": 5,
  "best_streak": 15,
  "avg_guesses_to_win": 4.2,
  "guess_distribution": {
    "1": 5,
    "2": 10,
    "3": 20,
    "4": 25,
    "5": 8,
    "6": 2
  }
}
```

#### GET /api/users/me/games
**Purpose**: Get user game history

**Headers**: `Authorization: Bearer {token}`

**Query Params**: `?limit=20&offset=0`

**Response**:
```json
{
  "games": [
    {
      "game_id": "uuid",
      "game_mode": "custom",
      "word_length": 5,
      "status": "won",
      "created_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:05:00Z"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

### Leaderboard Endpoints

#### GET /api/leaderboards/global
**Purpose**: Get global leaderboard

**Headers**: `Authorization: Bearer {token}` (optional for guests)

**Query Params**: `?limit=10&sort_by=win_rate`

**Response**:
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "user_id": "uuid",
      "username": "player1",
      "win_rate": 0.95,
      "games_played": 200,
      "best_streak": 25
    }
  ],
  "current_user_rank": 50
}
```

#### GET /api/leaderboards/daily
**Purpose**: Get daily leaderboard (word of the day)

**Headers**: `Authorization: Bearer {token}` (optional for guests)

**Query Params**: `?date=2024-01-01&limit=10`

**Response**:
```json
{
  "date": "2024-01-01",
  "leaderboard": [
    {
      "rank": 1,
      "user_id": "uuid",
      "username": "player1",
      "guesses_to_win": 3
    }
  ],
  "current_user_rank": null
}
```

### Health Endpoint

#### GET /health
**Purpose**: Health check

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "database": "healthy",
    "cache": "healthy"
  }
}
```

## Data Models

### Backend (Pydantic)

```python
class GameCreateRequest(BaseModel):
    game_mode: Literal["custom", "word_of_day", "practice"]
    word_length: int = Field(ge=5, le=8)

class GuessRequest(BaseModel):
    guess: str

class LetterFeedback(BaseModel):
    letter: str
    color: Literal["green", "yellow", "gray"]

class GameStateResponse(BaseModel):
    game_id: str
    game_mode: str
    word_length: int
    max_turns: int
    status: Literal["in_progress", "won", "lost"]
    guesses: List[str]
    feedback: List[List[LetterFeedback]]
    remaining_turns: int
    created_at: datetime
    completed_at: Optional[datetime]

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    username: Optional[str] = Field(max_length=100)

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    user_id: str
    email: str
    username: Optional[str]
    access_token: str
    refresh_token: Optional[str]

class StatsResponse(BaseModel):
    games_played: int
    games_won: int
    games_lost: int
    win_rate: float
    current_streak: int
    best_streak: int
    avg_guesses_to_win: Optional[float]
    guess_distribution: Dict[str, int]
```

### Frontend (JavaScript)

```javascript
// Game state structure
{
  gameId: string,
  gameMode: 'custom' | 'word_of_day' | 'practice',
  wordLength: number,
  maxTurns: number,
  status: 'in_progress' | 'won' | 'lost',
  guesses: string[],
  feedback: LetterFeedback[][],
  remainingTurns: number,
  createdAt: string,
  completedAt?: string
}

// Letter feedback structure
{
  letter: string,
  color: 'green' | 'yellow' | 'gray'
}

// User structure
{
  userId: string,
  email: string,
  username?: string,
  createdAt: string
}

// Stats structure
{
  gamesPlayed: number,
  gamesWon: number,
  gamesLost: number,
  winRate: number,
  currentStreak: number,
  bestStreak: number,
  avgGuessesToWin: number,
  guessDistribution: Record<string, number>
}
```

## Word List Strategy

For production, we have two options:

### Option 1: Embedded Word List (Assessment MVP)
- Load words from JSON file in backend
- Pre-filtered by length (5-8)
- Excludes plural words
- Location: `backend/data/words.json`

Structure:
```json
{
  "5": ["APPLE", "BEACH", "CRANE", ...],
  "6": ["ORANGE", "YELLOW", "PURPLE", ...],
  "7": ["ELEPHANT", "COMPUTER", "KEYBOARD", ...],
  "8": ["KEYBOARDS", "MONITORS", "SOFTWARE", ...]
}
```

### Option 2: External Word API (Production Enhancement)
- Call external word API for validation
- Cache results in Redis
- Fallback to embedded list if API unavailable
- Rate limit API calls

For this assessment, we'll use **Option 1** (embedded word list) for simplicity and reliability.

## Validation Strategy

### Frontend Validation (Optimistic)
- **Word Length**: Check before submission
- **Characters**: Only letters allowed
- **Local Word Check**: Subset of word list loaded in frontend
- **Input Sanitization**: Prevent XSS
- **Immediate Feedback**: Show errors immediately

**Benefits**:
- Fast user experience
- Reduces backend load
- Better UX with instant feedback

**Risks**:
- Frontend word list may be outdated
- Client can be bypassed

### Backend Validation (Source of Truth)
- **Word Length**: Strict validation
- **Word Existence**: Check against full word list
- **Game Rules**: Max turns, game status
- **Idempotency**: Check for duplicate requests
- **Authorization**: Verify user permissions

**Benefits**:
- Secure and reliable
- Single source of truth
- Cannot be bypassed

**Flow**:
```
User Input
    ↓
Frontend Validation (pass/fail)
    ↓ Pass
Optimistic UI Update
    ↓
API Request (with idempotency key)
    ↓
Backend Validation (pass/fail)
    ↓ Pass
Process Request
    ↓
Write to Cache (Redis)
    ↓
Enqueue Async Write
    ↓
Return Response
    ↓
Update UI (confirm or rollback)
```

**Conflict Resolution**:
- If backend validation fails, rollback UI and show error
- If async write fails, log and retry in background
- On reconnection, sync pending actions with idempotency keys

## Error Handling

### Backend Errors
- **400 Bad Request**: Invalid input (word length, guess format)
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Game/user not found
- **409 Conflict**: Game already completed, duplicate word of day attempt
- **422 Unprocessable Entity**: Invalid word (not in dictionary)
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Unexpected errors

### Frontend Errors
- Display user-friendly error messages
- Retry logic for network errors (with idempotency keys)
- Loading states for async operations
- Error boundaries for component errors
- Offline mode indication

## Performance Considerations

### Caching Strategy
- **Redis** for hot data:
  - Active game states (TTL: 7 days for in-progress, 24h for completed)
  - Word of the day (TTL: 48h)
  - User sessions (TTL: 24h)
  - User stats (TTL: 1h)
  - Leaderboards (TTL: 5min)
  - Idempotency keys (TTL: 24h)

### Database Optimization
- Indexes on:
  - `users.email`
  - `games.user_id`, `games.created_at`
  - `game_attempts.game_id`
  - `user_stats.user_id`
  - `word_of_day_attempts.user_id`, `word_of_day_attempts.attempt_date`

### Async Writes
- Queue non-critical writes (stats updates, leaderboard updates)
- Process in background workers
- Retry failed writes with exponential backoff
- Dead letter queue for permanently failed writes

### Frontend Performance
- Debounce keyboard input
- Lazy load word list (if large)
- Virtual scrolling for long lists (game history, leaderboards)
- Memoize expensive calculations
- Code splitting for routes

## Security Considerations

### Authentication
- JWT tokens with short expiration (15 minutes)
- Refresh tokens with longer expiration (7 days)
- Password hashing with bcrypt
- Secure cookie storage for refresh tokens

### Authorization
- Role-based access control (user, admin)
- Guest mode with limited features
- Resource ownership verification (users can only access their own data)

### Input Validation
- Strict validation on all inputs
- SQL injection prevention (parameterized queries)
- XSS prevention (input sanitization)
- CSRF protection (SameSite cookies)

### Rate Limiting
- Per-user rate limits on API endpoints
- IP-based rate limiting for unauthenticated requests
- Exponential backoff for retry attempts

### Data Privacy
- No sensitive data in logs
- Encrypt passwords at rest
- GDPR compliance (data deletion on request)

## Performance Analysis

### Backend Bottlenecks

#### 1. **Database I/O (Primary Bottleneck)**
**Risk Level**: HIGH

**Potential Issues**:
- Sequential database queries in a single request
- N+1 query problem (fetching game attempts one by one)
- Missing indexes on frequently queried columns
- Connection pool exhaustion under load
- Slow JOINs on large tables (user stats with many games)

**Mitigation Strategies**:
- **Redis Caching**: Cache hot data (active games, user stats, word of the day)
- **Connection Pooling**: Use SQLAlchemy connection pooling (default 5-20 connections)
- **Query Optimization**: Use `selectinload`/`joinedload` for eager loading
- **Read Replicas**: Offload read queries to read replicas (future enhancement)
- **Batch Operations**: Batch insert game attempts instead of individual inserts
- **Async Database Driver**: Use `asyncpg` for PostgreSQL async operations

**Expected Impact**:
- Without caching: 50-200ms per database query
- With Redis cache: 1-5ms for cached reads
- Connection pool reduces connection overhead by 80%

#### 2. **Redis Cache Latency (Secondary Bottleneck)**
**Risk Level**: MEDIUM

**Potential Issues**:
- Cache stampede (thundering herd) on cache miss
- Cache warming latency on cold start
- Network latency to Redis (if not co-located)
- Redis memory exhaustion under heavy load

**Mitigation Strategies**:
- **Cache Locking**: Use Redis SETNX to prevent stampede
- **Lazy Loading**: Populate cache on first access
- **TTL Strategy**: Staggered TTLs to prevent mass expiration
- **Redis Clustering**: Horizontal scaling for Redis (future)
- **Co-location**: Deploy Redis in same data center/region as API servers

**Expected Impact**:
- Cache hit: 1-5ms
- Cache miss: 50-100ms (database query + cache write)
- Network latency: <1ms if co-located, 5-20ms if distributed

#### 3. **JWT Token Validation (Minor Bottleneck)**
**Risk Level**: LOW

**Potential Issues**:
- Cryptographic signature verification on every request
- Token parsing overhead
- Database lookup for user session validation (if required)

**Mitigation Strategies**:
- **Stateless JWT**: No database lookup required for validation
- **Fast Cryptography**: Use RS256 or ES256 for faster verification
- **Token Caching**: Cache validated tokens in Redis (short TTL)
- **Public Key Caching**: Cache public keys for token verification

**Expected Impact**:
- Token validation: 1-3ms
- Negligible compared to database operations

#### 4. **Async Write Queue Backlog (Potential Bottleneck)**
**Risk Level**: MEDIUM

**Potential Issues**:
- Queue backlog if worker processes are too slow
- Dead letter queue filling up
- Stats/leaderboard updates delayed
- Database write contention

**Mitigation Strategies**:
- **Horizontal Scaling**: Multiple Celery workers
- **Priority Queues**: Separate queues for high/low priority tasks
- **Batch Writes**: Batch multiple updates into single DB transaction
- **Monitoring**: Alert on queue depth > threshold
- **Rate Limiting**: Throttle non-critical writes during peak load

**Expected Impact**:
- Normal operation: <100ms latency
- Under load: Up to 1-5 seconds for stats updates (acceptable)

#### 5. **Word Dictionary Loading (One-time Bottleneck)**
**Risk Level**: LOW

**Potential Issues**:
- Large word list loading time on startup
- Memory usage for word list

**Mitigation Strategies**:
- **Lazy Loading**: Load word list on first use
- **Pre-filtered Lists**: Separate files by word length
- **Memory-Mapped Files**: Use memory-mapped files for large word lists
- **Word Count**: Limit to common words (5,000-10,000 per length)

**Expected Impact**:
- One-time cost: 50-200ms on startup
- After loading: <1ms to query word list

### Frontend Bottlenecks

#### 1. **Large Component Re-renders (Primary Bottleneck)**
**Risk Level**: HIGH

**Potential Issues**:
- Unnecessary re-renders of GameBoard on every keystroke
- Keyboard re-rendering on every guess
- Entire app re-rendering on state changes
- Missing `useMemo`/`useCallback` optimizations

**Mitigation Strategies**:
- **React.memo**: Memoize expensive components (GameBoard, Keyboard)
- **useMemo**: Memoize computed values (feedback calculations)
- **useCallback**: Memoize event handlers
- **Virtualization**: Virtual scrolling for long lists (game history)
- **State Management**: Use Zustand/Redux for fine-grained updates
- **Context Optimization**: Split contexts to avoid unnecessary updates

**Expected Impact**:
- Without optimization: 50-200ms per keystroke
- With optimization: 5-20ms per keystroke
- Target: <16ms (60fps)

#### 2. **Network Latency (Secondary Bottleneck)**
**Risk Level**: MEDIUM

**Potential Issues**:
- Slow API responses on poor connections
- Serial API calls (get stats, then get games, then get leaderboard)
- Large payload sizes (full game history)
- No request deduplication

**Mitigation Strategies**:
- **Optimistic UI**: Update UI immediately, sync in background
- **Request Batching**: Batch multiple operations into single request
- **Parallel Requests**: Use Promise.all for independent requests
- **Response Compression**: Enable gzip compression on API
- **Request Caching**: Cache API responses in browser (short TTL)
- **GraphQL**: Consider GraphQL for precise data fetching (future)

**Expected Impact**:
- Good connection: 50-100ms per request
- Poor connection: 500-2000ms per request
- With optimistic UI: <50ms perceived latency

#### 3. **Bundle Size (Initial Load Bottleneck)**
**Risk Level**: MEDIUM

**Potential Issues**:
- Large JavaScript bundle size
- Slow initial page load
- Long time-to-interactive

**Mitigation Strategies**:
- **Code Splitting**: Split by routes (auth, game, profile, leaderboard)
- **Lazy Loading**: Load components on demand
- **Tree Shaking**: Remove unused code
- **Minification**: Minify JavaScript and CSS
- **CDN**: Serve static assets from CDN
- **Service Worker**: Cache assets for offline use

**Expected Impact**:
- Without optimization: 500KB-2MB bundle
- With optimization: 100-300KB bundle
- Load time: 2-5 seconds (slow) → 0.5-1 second (fast)

#### 4. **Word List Size (Memory Bottleneck)**
**Risk Level**: LOW

**Potential Issues**:
- Loading full word list in browser memory
- Increased initial bundle size
- Memory usage on mobile devices

**Mitigation Strategies**:
- **Subset Only**: Load only common words (1,000-2,000 per length)
- **Lazy Load**: Load word list only when needed
- **Server Validation**: Rely on backend for full validation
- **Bloom Filter**: Use Bloom filter for probabilistic validation (future)

**Expected Impact**:
- Full list: 200-500KB
- Subset: 50-100KB
- Memory impact: <10MB

### Performance Targets

#### Backend
- **API Response Time**: P50 < 100ms, P95 < 200ms, P99 < 500ms
- **Cache Hit Rate**: > 80% for hot data
- **Database Query Time**: < 50ms for 95% of queries
- **Token Validation**: < 5ms
- **Throughput**: 1,000+ requests/second per instance

#### Frontend
- **Time to Interactive**: < 2 seconds
- **First Contentful Paint**: < 1 second
- **Keystroke Response**: < 16ms (60fps)
- **API Response Handling**: < 100ms perceived latency (with optimistic UI)
- **Bundle Size**: < 300KB (gzipped)

## Security Deep Dive

### Authentication vs Authorization

#### Authentication (Who are you?)
**Purpose**: Verify user identity

**Implementation**:
- **JWT (JSON Web Tokens)**: Stateless tokens with user claims
- **Access Token**: Short-lived token for API access
- **Refresh Token**: Long-lived token for obtaining new access tokens
- **Password Hashing**: bcrypt with cost factor 12+

**Flow**:
```
1. User submits email/password
2. Backend validates credentials
3. Backend generates access token (15 min TTL) + refresh token (7 days TTL)
4. Client stores tokens (access in memory, refresh in httpOnly cookie)
5. Client includes access token in Authorization header
6. Backend validates token signature and expiration
7. If token expired, client uses refresh token to get new access token
```

#### Authorization (What can you do?)
**Purpose**: Verify user permissions

**Implementation**:
- **Role-Based Access Control (RBAC)**: User roles (user, admin, guest)
- **Resource Ownership**: Users can only access their own data
- **Scope-Based Authorization**: Token scopes limit access
- **Middleware**: FastAPI dependency injection for auth checks

**Roles**:
- **Guest**: Play practice mode, view public leaderboards
- **User**: Play all modes, view own stats, custom games
- **Admin**: Manage users, view all data, system configuration

**Authorization Check Points**:
- API Router level (permission to access endpoint)
- Service level (permission to access resource)
- Repository level (permission to modify data)

### Token Strategy

#### Access Token (Short-Lived)
**Purpose**: API authentication

**Properties**:
- **Lifetime**: 15 minutes (configurable: 5-30 minutes)
- **Storage**: Memory (JavaScript variable) or localStorage
- **Transmission**: Authorization: Bearer {token} header
- **Content**: User ID, email, role, scopes, issued_at, expires_at
- **Signature**: RS256 (asymmetric) or HS256 (symmetric)

**Why Short-Lived?**
- **Security**: Limited window if token is compromised
- **Revocation**: Tokens expire quickly, reducing impact of revocation failure
- **Refresh**: Forces regular re-authentication, reducing stale sessions
- **Best Practice**: Industry standard for modern auth systems

**Payload Example**:
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "user",
  "scopes": ["games:read", "games:write", "stats:read"],
  "iat": 1704067200,
  "exp": 1704068100
}
```

#### Refresh Token (Long-Lived)
**Purpose**: Obtain new access tokens without re-authentication

**Properties**:
- **Lifetime**: 7 days (configurable: 1-30 days)
- **Storage**: httpOnly, secure, SameSite cookie (not accessible to JavaScript)
- **Transmission**: Cookie automatically sent with requests
- **Content**: Random token, user ID, device fingerprint
- **Storage**: Database table (user_sessions) for revocation tracking

**Why Long-Lived?**
- **UX**: Users don't have to re-login frequently
- **Security**: Stored in httpOnly cookie, not vulnerable to XSS
- **Revocable**: Can be revoked in database (logout, password change)
- **Device Binding**: Can bind to specific device for added security

**Table Schema**:
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP
);
```

#### Token Refresh Flow
```
1. Client detects access token expired (401 response)
2. Client sends refresh token to /api/auth/refresh
3. Backend validates refresh token against database
4. Backend checks if token is revoked or expired
5. Backend generates new access token
6. Backend may rotate refresh token (optional, more secure)
7. Client updates access token in memory
8. Client retries original request
```

### Security Best Practices

#### 1. **Token Storage**
- **Access Token**: Memory (React state) - cleared on page refresh
- **Refresh Token**: httpOnly, secure, SameSite=strict cookie
- **Never**: Store access token in localStorage (XSS vulnerable)

#### 2. **Token Rotation (Optional but Recommended)**
- Generate new refresh token on each refresh
- Invalidate old refresh token
- Prevents refresh token replay attacks
- Adds complexity but improves security

#### 3. **Token Revocation**
- **On Logout**: Delete refresh token from database
- **On Password Change**: Revoke all user sessions
- **On Suspicious Activity**: Revoke specific session
- **Admin Action**: Revoke any user session

#### 4. **CORS Configuration**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains only
    allow_credentials=True,  # Required for cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
```

#### 5. **Rate Limiting**
- **Per-User**: 100 requests/minute per user
- **Per-IP**: 10 requests/minute for unauthenticated requests
- **Per-Endpoint**: Stricter limits on auth endpoints (5 login attempts/minute)
- **Implementation**: Redis-based rate limiting with sliding window

#### 6. **Input Validation**
- **Strict Validation**: Validate all inputs with Pydantic
- **Length Limits**: Max lengths on all string fields
- **Allow Lists**: Only allow specific characters (letters for guesses)
- **SQL Injection Prevention**: Parameterized queries (SQLAlchemy)
- **XSS Prevention**: Sanitize user input, escape output

#### 7. **Password Security**
- **Hashing**: bcrypt with cost factor 12+
- **Salt**: Automatic with bcrypt
- **Minimum Length**: 8 characters
- **Complexity**: Require mix of letters, numbers, symbols (optional)
- **Reset Flow**: Secure token-based reset (email link, expiring in 1 hour)

#### 8. **HTTPS Only**
- **Production**: Enforce HTTPS
- **HSTS**: HTTP Strict Transport Security header
- **Secure Cookies**: Set `secure` flag on cookies
- **No Mixed Content**: All resources over HTTPS

#### 9. **Logging and Monitoring**
- **Security Events**: Log login attempts, failed auth, suspicious activity
- **PII Redaction**: Don't log passwords, tokens, emails
- **Alerting**: Alert on brute force attempts, unusual patterns
- **Audit Trail**: Track user actions for compliance

#### 10. **Session Management**
- **Concurrent Sessions**: Limit to 3-5 active sessions per user
- **Session Expiration**: Refresh tokens expire after 7 days
- **Idle Timeout**: Logout after 30 minutes of inactivity (optional)
- **Device Binding**: Bind sessions to device fingerprint (optional)

### Security Trade-offs

#### Access Token Lifetime
| Lifetime | Security | UX | Recommendation |
|----------|----------|-----|----------------|
| 5 minutes | Very High | Poor (frequent refresh) | Too short |
| 15 minutes | High | Good | **Recommended** |
| 30 minutes | Medium | Very Good | Acceptable |
| 1 hour | Low | Excellent | Too long |

#### Refresh Token Lifetime
| Lifetime | Security | UX | Recommendation |
|----------|----------|-----|----------------|
| 1 day | Very High | Poor (frequent login) | Too short |
| 7 days | High | Good | **Recommended** |
| 30 days | Medium | Very Good | Acceptable |
| 90 days | Low | Excellent | Too long |

### Guest Mode Security

**Purpose**: Allow anonymous play without account

**Implementation**:
- **Guest Token**: JWT with `role: guest` and `guest_id`
- **Limited Features**: Practice mode only, no stats persistence
- **No Refresh Token**: Guest tokens don't have refresh tokens
- **Session Duration**: 24 hours, then must create new guest session
- **Conversion**: Option to convert guest account to real account

**Security Considerations**:
- **Rate Limiting**: Stricter rate limits for guests (per IP)
- **No PII**: Don't collect email or personal data
- **Data Isolation**: Guest data doesn't persist in database
- **Conversion**: Safe migration of guest progress to real account

## Implementation Order

### Phase 1: Backend Foundation (Data Layer)
1. Database schema and migrations
2. Word Dictionary component (embedded word list)
3. Word Selector component
4. Feedback Engine component
5. Tests for above components

### Phase 2: Backend Authentication
6. Auth Repository component
7. Auth Service component
8. Auth Router
9. Auth Middleware
10. Auth tests (unit, integ, e2e)

### Phase 3: Backend Game Logic
11. Game State component
12. Game Repository component (PostgreSQL + Redis)
13. Word Validator component
14. Word of the Day component
15. Tests for above components

### Phase 4: Backend Advanced Features
16. Idempotency component
17. Async Write Queue component
18. Stats Calculator component
19. Stats Service component
20. Leaderboard Service component
21. Tests for above components

### Phase 5: Backend API Layer
22. Game Service component (orchestration)
23. Game Router
24. User Router
25. Leaderboard Router
26. Error Handler
27. API tests (unit, integ, e2e)

### Phase 6: Frontend Foundation
28. API Client component
29. Auth Context component
30. Client-side Validation component
31. Offline Sync Manager component
32. Tests for above components

### Phase 7: Frontend UI Components
33. Auth UI components (Login, Register)
34. Game Mode Selector
35. Word Length Selector
36. Game Board
37. Keyboard
38. Game Controls
39. Feedback Display
40. Tests for above components

### Phase 8: Frontend Advanced UI
41. Stats Display
42. Leaderboard Display
43. Profile View
44. Keyboard Handler hook
45. Tests for above components

### Phase 9: Frontend Integration
46. App component
47. Game State Context component
48. E2E tests
49. Performance optimization

### Phase 10: Integration & Polish
50. End-to-end testing
51. Performance testing
52. Security audit
53. Documentation
54. Deployment preparation

## Dependencies to Add

### Backend
```txt
# Existing
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.0

# Cache
redis>=5.0.0

# Auth
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# Async
celery>=5.3.0
redis>=5.0.0  # For Celery broker

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0  # For async HTTP testing

# Utilities
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
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

## Deployment Considerations

### Backend
- Docker containerization
- Environment variables for configuration
- Health check endpoint for load balancers
- Graceful shutdown handling
- Database connection pooling
- Redis connection pooling
- Celery worker processes
- Log aggregation (structured logs)

### Frontend
- Static file generation (Vite build)
- CDN deployment for static assets
- Environment-specific configuration
- Service worker for offline support (optional)
- Progressive Web App (PWA) support (optional)

### Infrastructure
- PostgreSQL database (managed service or self-hosted)
- Redis cache (managed service or self-hosted)
- Load balancer for API servers
- Horizontal scaling for API workers
- Celery workers for async tasks
- Monitoring and alerting
- Backup strategy for database

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
