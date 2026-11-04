# Design Review - Issues, Holes, and Trade-off Errors

## Critical Issues (Must Fix Before Implementation)

### 1. Practice Mode Persistence Contradiction
**Severity**: HIGH
**Location**: Core Requirements vs Implementation

**Issue**:
- Requirements state: "Practice Mode: No persistence, purely for learning"
- But if practice games aren't persisted at all, users can't review their practice history
- Stats calculator needs to exclude practice games, but how do we know which games were practice if not persisted?

**Options**:
- **Option A**: Persist practice games but mark with `game_mode='practice'` and exclude from stats
- **Option B**: Never persist practice games (not even temporarily), accept that practice history is lost
- **Option C**: Persist practice games temporarily (24h) for session replay, then delete

**Recommendation**: Option A - Persist practice games with mode flag and exclude from stats calculations

---

### 2. Word of the Day - Timezone Handling
**Severity**: HIGH
**Location**: Word of the Day Component

**Issue**:
- Design says "same word for all users" based on date
- Doesn't specify timezone (UTC vs user's local timezone)
- Edge case: User in PST plays at 11:59pm, then at 12:01am - do they get two attempts?

**Recommendation**:
- Use UTC for word of the day determination
- Word changes at 00:00 UTC
- Display user's local time for "word resets in X hours"
- One attempt per UTC calendar day per user

---

### 3. Access Token Storage - UX Problem
**Severity**: HIGH
**Location**: Security Deep Dive - Token Storage

**Issue**:
- Design says: "Access Token: Memory (React state) - cleared on page refresh"
- This forces users to re-login on every page refresh
- Terrible UX for a game app

**Inconsistency**:
- Security section says "Memory (React state)"
- AuthContext component description says "JWT token storage (localStorage)"

**Recommendation**:
- Use **sessionStorage** instead of memory
- Persists across page refreshes
- Cleared when tab/window closes
- Better security than localStorage (isolated to tab)
- Better UX than memory (no re-login on refresh)

---

### 4. Game State - Async Write Risk
**Severity**: HIGH
**Location**: Data Flow Architecture - Write Path

**Issue**:
- Design suggests async writes for game state
- If async write fails and server crashes, user loses game progress
- Unacceptable for primary game data

**Recommendation**:
- **Critical path (game state)**: Write-through caching
  - Write to Redis synchronously (immediate)
  - Write to PostgreSQL synchronously (before returning response)
  - Or: Write to Redis sync, enqueue async DB write with retry logic
- **Non-critical path (stats, leaderboards)**: Async writes acceptable

---

### 5. Guest Mode - No Refresh Token Issue
**Severity**: MEDIUM
**Location**: Security Deep Dive - Guest Mode

**Issue**:
- Design says guest tokens don't have refresh tokens
- Guest sessions last 24 hours
- If access token expires after 15 minutes, guest is kicked out after 15 minutes of play
- This contradicts the 24-hour session duration

**Recommendation**:
- **Option A**: Give guests refresh tokens (with shorter TTL, e.g., 6 hours)
- **Option B**: Extend guest access token TTL to 24 hours (security trade-off)
- **Option C**: Require guests to re-login (create new guest session) every 15 minutes (bad UX)

**Recommendation**: Option A - Guest refresh tokens with 6-hour TTL

---

### 6. Idempotency Key Scope Undefined
**Severity**: MEDIUM
**Location**: Idempotency Component

**Issue**:
- Design mentions idempotency keys for all user actions
- Doesn't specify scope: per user? per game? global?
- If I submit guess "APPLE" with key "123" in game A, can I use "123" in game B?

**Recommendation**:
- Idempotency key scope: `{user_id}:{operation_type}:{resource_id}`
- Example: `user_123:submit_guess:game_456`
- This prevents cross-resource key collisions

---

### 7. Logout Endpoint - Cookie Clearing
**Severity**: MEDIUM
**Location**: API Design - Auth Endpoints

**Issue**:
- Design mentions POST /api/auth/logout
- Doesn't specify how to clear httpOnly refresh token cookie
- Client cannot delete httpOnly cookies (JavaScript can't access them)

**Recommendation**:
- Logout endpoint must return `Set-Cookie: refresh_token=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Secure; SameSite=Strict`
- Client-side: Clear access token from sessionStorage
- Backend: Delete refresh token from database

---

## Important Issues (Should Address)

### 8. Async Write Queue - Failure Handling
**Severity**: MEDIUM
**Location**: Async Write Queue Component

**Issue**:
- Design mentions dead letter queue for permanently failed writes
- Doesn't specify retry policy (how many retries? backoff strategy?)
- Doesn't specify queue size limits
- What happens when queue grows too large?

**Recommendation**:
- Retry policy: 3 retries with exponential backoff (1s, 5s, 15s)
- Dead letter queue after 3 failures
- Alert on queue depth > 1000
- Maximum queue size: 10,000 (reject new writes if full)

---

### 9. Cache Invalidation Strategy
**Severity**: MEDIUM
**Location**: Performance Considerations - Caching Strategy

**Issue**:
- Design specifies TTLs for cache entries
- Doesn't specify how to invalidate cache when data changes
- If I update my profile, cached user data remains stale until TTL expires

**Recommendation**:
- **Write-through cache**: Update cache on write, set TTL
- **Cache invalidation**: Explicitly delete cache keys on data updates
- Example: On profile update, delete `user_session:{user_id}` and `user_stats:{user_id}`

---

### 10. Leaderboard Cache - Update Frequency
**Severity**: MEDIUM
**Location**: Leaderboard Service Component

**Issue**:
- Design says "refresh every 5 minutes"
- Competitive game - users expect immediate rank updates after winning
- 5-minute delay is frustrating

**Recommendation**:
- **Event-driven**: Invalidate leaderboard cache on game completion
- **Fallback**: Periodic refresh every 5 minutes as backup
- This gives immediate updates with periodic sync as safety net

---

### 11. Word of the Day - Word Length
**Severity**: MEDIUM
**Location**: Game Modes

**Issue**:
- Custom games allow configurable word length (5-8)
- Word of the Day - what's the word length?
- Always 5? Rotates daily? Configurable per day?

**Recommendation**:
- Word of the Day is always 5 letters (traditional Wordle)
- Or: Rotates daily (5, 6, 7, 8, then back to 5)
- **Recommendation**: Always 5 letters for consistency with original Wordle

---

### 12. Stats - Guess Distribution for Different Word Lengths
**Severity**: MEDIUM
**Location**: Stats Calculator Component

**Issue**:
- Design tracks "guess distribution (won in 1, 2, 3, 4, 5, 6 turns)"
- But 8-letter words have 9 turns (N+1)
- How do we track distribution across different word lengths?

**Recommendation**:
- **Option A**: Track distribution per word length (separate for 5, 6, 7, 8)
- **Option B**: Normalize to percentage of max turns (won in 1/6, 2/6, etc.)
- **Recommendation**: Option A - Track distribution per word length for more accurate stats

---

### 13. Feedback Engine - Duplicate Letters Algorithm
**Severity**: MEDIUM
**Location**: Feedback Engine Component

**Issue**:
- Design says "handles duplicate letters correctly"
- This is the hardest part of Wordle logic
- No algorithm documented
- Example: Target "APPLE", guess "PAPER" - how should feedback work?

**Recommendation**:
Add detailed algorithm:
```
1. First pass: Mark green letters (correct position)
2. Second pass: Count remaining letters in target
3. Third pass: Mark yellow letters (wrong position) up to remaining count
4. Fourth pass: Mark gray letters

Example:
Target: APPLE
Guess: PAPER

Pass 1 (green):
- P(0) != A, gray
- A(1) == P, gray
- P(2) == P, green
- E(3) == L, gray
- R(4) == E, gray

Pass 2 (count remaining):
Target after removing green P: APLE (1 P, 1 A, 1 L, 1 E)

Pass 3 (yellow):
- P(0): Target has 1 P remaining, mark yellow
- A(1): Target has 1 A, mark yellow
- E(3): Target has 1 E, mark yellow
- R(4): Target has 0 R, mark gray

Final: P(yellow), A(yellow), P(green), E(yellow), R(gray)
```

---

### 14. Offline Sync - Conflict Resolution Strategy
**Severity**: MEDIUM
**Location**: Offline Sync Manager Component

**Issue**:
- Design mentions "resolve conflicts with server state"
- Doesn't specify conflict resolution strategy
- What if I made 3 guesses offline, but played on another device?

**Recommendation**:
- **Last-write-wins** for guesses (most recent wins)
- **Server-wins** for game status (can't resume completed game)
- **Merge** for stats (recalculate from all game data)
- For this assessment: Simple approach - server state is source of truth, client resyncs

---

### 15. Missing Email Service for Password Reset
**Severity**: MEDIUM
**Location**: Auth Service Component

**Issue**:
- Design mentions password reset flow
- No email service component to send reset emails
- No details on token generation/storage/validation

**Recommendation**:
- **Option A**: Add email service component (SES, SendGrid, etc.)
- **Option B**: Defer password reset to future enhancement (out of scope for MVP)
- **Recommendation**: Option B - Mark as out of scope for assessment, document future implementation

---

## Minor Issues (Nice to Have)

### 16. Database Indexes - Missing Composite Indexes
**Severity**: LOW
**Location**: Database Schema

**Issue**:
- Design lists single-column indexes
- Missing composite indexes for common query patterns
- Example: Querying games by user_id + created_at for pagination needs composite index

**Recommendation**:
Add composite indexes:
```sql
CREATE INDEX idx_games_user_created ON games(user_id, created_at DESC);
CREATE INDEX idx_game_attempts_game_number ON game_attempts(game_id, attempt_number);
CREATE INDEX idx_wod_user_date ON word_of_day_attempts(user_id, attempt_date);
```

---

### 17. Guest Mode - Allow Word of the Day Preview
**Severity**: LOW
**Location**: Game Modes

**Issue**:
- Design says Guest Mode is "Practice mode only"
- Users might want to try Word of the Day as guest before creating account
- Reduces conversion funnel

**Recommendation**:
- Allow guests to play Word of the Day (one attempt per day)
- Show "Create account to save your stats" prompt
- Better conversion strategy

---

### 18. Token Storage Inconsistency
**Severity**: LOW
**Location**: Multiple sections

**Issue**:
- Security section: "Access Token: Memory (React state)"
- AuthContext: "JWT token storage (localStorage)"
- Inconsistent documentation

**Recommendation**:
- Standardize on sessionStorage throughout document
- Update all references

---

### 19. CSRF Protection for Refresh Token
**Severity**: LOW
**Location**: Security Deep Dive

**Issue**:
- Refresh token in httpOnly cookie with SameSite=strict
- SameSite=strict prevents most CSRF, but not subdomain attacks
- No explicit CSRF token mechanism

**Recommendation**:
- SameSite=strict is sufficient for most cases
- Add note: For subdomain scenarios, consider double-submit cookie pattern
- Acceptable as-is for assessment

---

### 20. Async Database Driver Not Specified
**Severity**: LOW
**Location**: Performance Analysis

**Issue**:
- Performance section mentions "Use asyncpg for PostgreSQL async operations"
- But implementation components don't specify async/sync choice
- Inconsistent with FastAPI's async nature

**Recommendation**:
- Specify: Use SQLAlchemy 2.0 with async engine (AsyncSession)
- Or: Use sync SQLAlchemy with run_in_executor
- **Recommendation**: Async SQLAlchemy 2.0 for consistency with FastAPI

---

## Trade-off Analysis

### Trade-off 1: Complexity vs Speed
**Current Design**: 18 backend components, 17 frontend components
**Concern**: May be over-engineered for assessment timeline
**Recommendation**: Consider MVP subset:
- Phase 1: Skip email service, friends leaderboard, advanced offline sync
- Phase 2: Add later if time permits

---

### Trade-off 2: Redis vs In-Memory Only
**Current Design**: Redis for caching
**Concern**: Adds infrastructure complexity (Redis deployment)
**Alternative**: In-memory caching (Python dict) for MVP
**Recommendation**: Keep Redis for production readiness, document fallback for local dev

---

### Trade-off 3: PostgreSQL vs SQLite
**Current Design**: PostgreSQL
**Concern**: Requires database setup
**Alternative**: SQLite for local development, PostgreSQL for production
**Recommendation**: Support both via environment variable

---

### Trade-off 4: Celery vs Simple Background Thread
**Current Design**: Celery for async writes
**Concern**: Celery adds significant complexity (Redis broker, worker processes)
**Alternative**: Simple asyncio.create_task for MVP
**Recommendation**: Use asyncio background tasks for assessment, document Celery for production

---

## Summary of Required Changes

### Must Fix (Blockers)
1. ✅ Clarify Practice Mode persistence (Option A - persist with mode flag)
2. ✅ Specify Word of the Day timezone (UTC)
3. ✅ Change access token storage to sessionStorage
4. ✅ Change game state to write-through or sync DB write
5. ✅ Add guest refresh tokens (6-hour TTL)
6. ✅ Specify idempotency key scope
7. ✅ Specify logout cookie clearing mechanism

### Should Fix (Important)
8. ✅ Add async write retry policy and queue limits
9. ✅ Add cache invalidation strategy
10. ✅ Change leaderboard to event-driven + periodic fallback
11. ✅ Specify Word of the Day word length (always 5)
12. ✅ Change stats distribution to per-word-length
13. ✅ Add detailed feedback algorithm for duplicate letters
14. ✅ Specify offline sync conflict resolution (server-wins)
15. ✅ Mark password reset as out of scope or add email service

### Nice to Have
16. Add composite database indexes
17. Allow guests to play Word of the Day
18. Fix token storage inconsistency
19. Add CSRF protection note
20. Specify async SQLAlchemy 2.0

### Trade-off Decisions
- Accept component complexity (production-ready design)
- Keep Redis (document local dev fallback)
- Support SQLite/PostgreSQL via environment
- Use asyncio background tasks instead of Celery for assessment

## Next Steps

1. Update DESIGN.md with all fixes
2. Create DESIGN_DECISIONS.md documenting trade-offs
3. Proceed with implementation once design is finalized
