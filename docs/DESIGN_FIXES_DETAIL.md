# Detailed Design Fixes Analysis

## Critical Fixes (Must Fix Before Implementation)

---

### Fix #1: Practice Mode Persistence

**Problem**:
- Requirements state "Practice Mode: No persistence, purely for learning"
- But stats calculator needs to exclude practice games from calculations
- If practice games aren't persisted at all, we can't distinguish them from other games
- Users might want to review their practice history

**Solution Options**:

#### Option A: Persist with Mode Flag (RECOMMENDED)
**Implementation**:
- Persist practice games to database with `game_mode='practice'`
- Stats calculator filters out `game_mode='practice'` when calculating stats
- Leaderboards exclude practice games
- User can view practice history in profile

**Pros**:
- Clear separation of game types
- Users can review practice history
- Stats accurately exclude practice games
- Simple to implement (just add filter to queries)

**Cons**:
- Slightly more database storage
- Need to ensure practice games never count in stats (bug risk)

**Implementation Details**:
```sql
-- Stats calculation query
SELECT COUNT(*) FROM games
WHERE user_id = ? AND game_mode != 'practice' AND status = 'won';
```

```python
# Stats calculator
def calculate_stats(user_id):
    games = game_repository.get_user_games(user_id)
    practice_games = [g for g in games if g.game_mode == 'practice']
    real_games = [g for g in games if g.game_mode != 'practice']
    # Calculate stats only from real_games
```

---

#### Option B: Never Persist Practice Games
**Implementation**:
- Practice games only exist in memory (client-side or Redis cache)
- Never written to database
- No game history for practice games
- Stats don't need filtering (practice games don't exist in DB)

**Pros**:
- True "no persistence" as per requirements
- Less database storage
- Simpler stats queries (no filtering needed)

**Cons**:
- Users lose practice history on refresh
- Can't review practice games
- If we add practice mode later, no historical data
- Confusing UX (why can't I see my practice games?)

**Implementation Details**:
```python
# Game service
def create_practice_game(user_id):
    game = GameState(...)  # Only in memory
    return game  # Don't persist to DB
```

---

#### Option C: Temporary Persistence (24h)
**Implementation**:
- Persist practice games with short TTL (24h)
- Auto-delete after 24h
- Users can review recent practice games
- Stats never include practice games (deleted before stats calc)

**Pros**:
- Users can review recent practice games
- True temporary persistence
- Stats remain accurate

**Cons**:
- Complex TTL management
- Cleanup jobs required
- Still no long-term history
- What if user plays at 11:59pm, gone by 12:01am?

**Implementation Details**:
```python
# Async cleanup job
async def cleanup_old_practice_games():
    await game_repository.delete_practice_games_older_than(hours=24)
```

---

**Recommendation**: Option A (Persist with Mode Flag)
**Rationale**:
- Best UX for users (can review history)
- Simplest implementation
- Clear separation of concerns
- Aligns with "production-ready" goal
- Practice games are valuable data for users

**Impact**:
- Database: +1 column (game_mode already exists)
- Stats: Add filter to all stat queries
- Leaderboard: Add filter to leaderboard queries
- Frontend: Display game mode in game history

---

### Fix #2: Word of the Day Timezone

**Problem**:
- "Same word for all users" based on date
- Timezone not specified
- Edge case: User in PST plays at 11:59pm, then at 12:01am - do they get two attempts?
- Confusing UX if word changes at unexpected times

**Solution Options**:

#### Option A: UTC-Based (RECOMMENDED)
**Implementation**:
- Word of the day determined by UTC date
- Word changes at 00:00 UTC
- One attempt per UTC calendar day per user
- Display "Word resets in X hours" based on user's local time relative to UTC

**Pros**:
- Consistent for all users globally
- Simple to implement
- No timezone confusion
- Industry standard for daily challenges

**Cons**:
- Word might change at inconvenient times for some users (e.g., 5pm local time)
- Requires users to understand UTC (display helps with this)

**Implementation Details**:
```python
def get_word_of_the_day(date: datetime = None) -> str:
    if date is None:
        date = datetime.utcnow().date()  # Use UTC date
    return word_selector.select_word_by_date(date)
```

```python
def get_time_until_next_word(user_timezone: str) -> timedelta:
    utc_now = datetime.utcnow()
    next_midnight_utc = (utc_now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    return next_midnight_utc - utc_now
```

**Frontend Display**:
```
Word of the Day
Resets in 5 hours 23 minutes
```

---

#### Option B: User's Local Timezone
**Implementation**:
- Word of the day determined by user's local date
- Word changes at midnight in user's timezone
- One attempt per local calendar day per user
- Store user's timezone in profile

**Pros**:
- Word always changes at midnight for user (intuitive)
- Better UX for daily habit formation

**Cons**:
- Different users get different words on same calendar day
- More complex implementation (timezone storage, conversion)
- Leaderboard comparison less fair (different words)
- Users can game system by changing timezone

**Implementation Details**:
```sql
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';
```

```python
def get_word_of_the_day(user_id: str) -> str:
    user = user_repository.get(user_id)
    local_date = datetime.now(user.timezone).date()
    return word_selector.select_word_by_date(local_date)
```

---

#### Option C: Fixed Global Timezone (e.g., EST)
**Implementation**:
- Word of the day determined by fixed timezone (e.g., EST)
- Word changes at midnight in that timezone
- One attempt per that timezone's calendar day

**Pros**:
- Consistent for all users
- Simpler than user-specific timezones

**Cons**:
- Arbitrary choice of timezone
- Confusing for users in other timezones
- No benefit over UTC

---

**Recommendation**: Option A (UTC-Based)
**Rationale**:
- Industry standard (NYT Wordle uses UTC)
- Simplest implementation
- Fair for all users globally
- Clear display helps users understand

**Impact**:
- Backend: Use UTC for all date calculations
- Frontend: Display countdown to next word in local time
- Database: Store attempt_date as DATE (UTC-based)
- No schema changes needed

---

### Fix #3: Access Token Storage

**Problem**:
- Design says "Memory (React state) - cleared on page refresh"
- Forces users to re-login on every page refresh
- Terrible UX for a game app
- Inconsistent with AuthContext description ("localStorage")

**Solution Options**:

#### Option A: sessionStorage (RECOMMENDED)
**Implementation**:
- Store access token in sessionStorage
- Persists across page refreshes
- Cleared when tab/window closes
- Better security than localStorage (isolated to tab)
- Better UX than memory (no re-login on refresh)

**Pros**:
- Persists across refreshes (good UX)
- More secure than localStorage (tab-isolated)
- Standard practice for modern apps
- No re-login on refresh

**Cons**:
- Lost if user closes tab (expected behavior)
- Slightly less convenient than localStorage
- Multiple tabs need separate logins (acceptable)

**Implementation Details**:
```javascript
// Login
function login(email, password) {
  const response = await apiClient.login(email, password);
  sessionStorage.setItem('access_token', response.access_token);
  setAuthState(response);
}

// Logout
function logout() {
  sessionStorage.removeItem('access_token');
  setAuthState(null);
}

// API client
function getAuthHeader() {
  const token = sessionStorage.getItem('access_token');
  return token ? `Bearer ${token}` : null;
}
```

---

#### Option B: localStorage
**Implementation**:
- Store access token in localStorage
- Persists across page refreshes and tab closures
- Cleared only on logout or manual clear

**Pros**:
- Most convenient UX (persist across sessions)
- Standard approach for many apps

**Cons**:
- **Security Risk**: XSS vulnerability - malicious script can steal token
- Token persists even after user closes browser (security concern)
- If user forgets to logout, token remains accessible

**Implementation Details**:
```javascript
localStorage.setItem('access_token', response.access_token);
```

---

#### Option C: Memory Only (Current Design)
**Implementation**:
- Store access token in React state only
- Cleared on page refresh
- Forces re-login on every refresh

**Pros**:
- Most secure (token never persisted)
- Simple implementation

**Cons**:
- **Terrible UX**: Re-login on every refresh
- Not acceptable for a game app
- Users will abandon app

---

#### Option D: httpOnly Cookie
**Implementation**:
- Store access token in httpOnly cookie
- Similar to refresh token but shorter TTL

**Pros**:
- Secure (not accessible to JavaScript)
- Automatic transmission with requests

**Cons**:
- Can't manually attach to Authorization header
- CSRF vulnerability (need SameSite, CSRF tokens)
- Overkill for short-lived access token
- Refresh token already uses httpOnly cookie

---

**Recommendation**: Option A (sessionStorage)
**Rationale**:
- Best balance of security and UX
- Industry standard for access tokens
- Persists across refreshes (required for game app)
- More secure than localStorage (tab-isolated)
- Refresh token already handles long-term persistence

**Impact**:
- Frontend: Change from memory/localStorage to sessionStorage
- Backend: No changes
- Security: More secure than localStorage, less secure than memory (acceptable trade-off)
- UX: Significant improvement (no re-login on refresh)

---

### Fix #4: Game State Async Write Risk

**Problem**:
- Design suggests async writes for game state
- If async write fails and server crashes, user loses game progress
- Unacceptable for primary game data (core feature)
- Stats/leaderboards can tolerate delay, but game state cannot

**Solution Options**:

#### Option A: Write-Through Caching (RECOMMENDED)
**Implementation**:
- Write to Redis synchronously (immediate)
- Write to PostgreSQL synchronously (before returning response)
- Or: Write to Redis sync, enqueue async DB write with retry

**Flow**:
```
User Action
    ↓
Backend Validation
    ↓
Write to Redis (synchronous) - <5ms
    ↓
Write to PostgreSQL (synchronous) - <50ms
    ↓
Return Response
```

**Pros**:
- Data durability guaranteed
- No risk of data loss on crash
- Redis cache is always in sync
- Simple implementation

**Cons**:
- Slower response time (adds DB write latency)
- More database load

**Performance Impact**:
- Without: 50-100ms response time
- With: 100-150ms response time (acceptable)

---

#### Option B: Write-Behind with Acknowledgment
**Implementation**:
- Write to Redis synchronously
- Enqueue async DB write
- Return response immediately
- Client waits for acknowledgment (optional)

**Flow**:
```
User Action
    ↓
Backend Validation
    ↓
Write to Redis (synchronous) - <5ms
    ↓
Enqueue Async DB Write
    ↓
Return Response
    ↓
Background: Write to PostgreSQL
```

**Pros**:
- Fast response time
- Redis has data (survives crash if Redis persists)
- Better performance

**Cons**:
- Risk of data loss if Redis crashes before DB write
- More complex implementation
- Need Redis persistence (AOF/RDB)

**Redis Persistence Config**:
```conf
appendonly yes
appendfsync everysec
```

---

#### Option C: Hybrid Approach
**Implementation**:
- Critical operations (game creation, guess submission): sync DB write
- Non-critical operations (stats, leaderboards): async write
- Game state always written to DB synchronously

**Pros**:
- Best of both worlds
- Game data guaranteed
- Stats/leaderboards optimized

**Cons**:
- More complex logic
- Need to categorize operations

---

#### Option D: Current Design (Pure Async)
**Implementation**:
- All writes async
- No sync writes
- Fast but risky

**Pros**:
- Fastest response time
- Simplest implementation

**Cons**:
- **Unacceptable risk**: Data loss on crash
- Not production-ready
- Fails durability requirement

---

**Recommendation**: Option A (Write-Through Caching) for Game State
**Rationale**:
- Game state is core feature, cannot tolerate data loss
- 50ms latency is acceptable for game operations
- Simpler than write-behind with Redis persistence
- Production-ready approach

**For Stats/Leaderboards**: Use Option B (Write-Behind)
- Stats updates can tolerate delay
- Leaderboards can be stale for a few seconds
- Performance more important here

**Implementation Details**:
```python
# Game service - sync write
async def submit_guess(game_id: str, guess: str):
    # Write to Redis
    await game_cache.set(game_id, updated_state)
    # Write to DB (sync)
    await game_repository.save_game(updated_state)
    return updated_state

# Stats service - async write
async def update_stats(user_id: str, game_result):
    # Enqueue async write
    await async_write_queue.enqueue('update_stats', user_id, game_result)
    # Return immediately
```

**Impact**:
- Backend: Change game state writes to synchronous
- Performance: +50ms latency for game operations (acceptable)
- Reliability: Significant improvement (no data loss)
- Complexity: Minimal change

---

### Fix #5: Guest Mode Refresh Token

**Problem**:
- Design says guest tokens don't have refresh tokens
- Guest sessions last 24 hours
- Access token expires after 15 minutes
- Guest is kicked out after 15 minutes of play
- Contradicts 24-hour session duration

**Solution Options**:

#### Option A: Guest Refresh Tokens (RECOMMENDED)
**Implementation**:
- Give guests refresh tokens with shorter TTL (6 hours)
- Same refresh flow as regular users
- Session limited to 6 hours total

**Pros**:
- Consistent auth flow
- Guests can play for 6 hours without re-login
- Simple implementation
- Good UX

**Cons**:
- Requires refresh token storage (even for guests)
- Slightly more database storage
- Need to limit guest features separately

**Implementation Details**:
```python
# Guest login
async def create_guest_session():
    guest_id = str(uuid.uuid4())
    access_token = create_jwt(guest_id, role='guest', ttl=15*60)
    refresh_token = create_refresh_token(guest_id, ttl=6*60*60)
    await session_repository.save(guest_id, refresh_token, expires_in=6*60*60)
    return {
        'guest_id': guest_id,
        'access_token': access_token,
        'refresh_token': refresh_token
    }
```

---

#### Option B: Extended Access Token TTL
**Implementation**:
- Give guests 24-hour access token
- No refresh token needed
- Security trade-off

**Pros**:
- Simplest implementation
- No refresh token logic for guests

**Cons**:
- **Security Risk**: 24-hour access token if compromised
- Violates short-lived token principle
- Not production-ready

---

#### Option C: Re-login Every 15 Minutes
**Implementation**:
- Guests must create new guest session every 15 minutes
- Or: Extend session with one-click "continue as guest"

**Pros**:
- Most secure (short-lived tokens)
- No refresh token storage

**Cons**:
- **Terrible UX**: Disrupts gameplay every 15 minutes
- Users will abandon app
- Not acceptable for game app

---

#### Option D: No Time Limit (Anonymous)
**Implementation**:
- Guests play indefinitely without expiration
- Only limited by session cookie (browser close)

**Pros**:
- Best UX for guests
- Simplest

**Cons**:
- **Security Risk**: Unlimited access for anonymous users
- Can abuse system (rate limit evasion)
- Not production-ready

---

**Recommendation**: Option A (Guest Refresh Tokens with 6-hour TTL)
**Rationale**:
- Balances security and UX
- Consistent auth flow for all users
- 6 hours is reasonable for a gaming session
- Industry standard approach

**Impact**:
- Backend: Add refresh token support for guests
- Database: Guest sessions stored in user_sessions table (with role='guest')
- Security: Shorter TTL than regular users (6h vs 7d)
- UX: Guests can play for 6 hours without interruption

---

### Fix #6: Idempotency Key Scope

**Problem**:
- Design mentions idempotency keys for all user actions
- Doesn't specify scope: per user? per game? global?
- Risk of key collisions if scope not defined
- Example: Can I use key "123" for guess in game A and game B?

**Solution Options**:

#### Option A: Hierarchical Scope (RECOMMENDED)
**Implementation**:
- Scope: `{user_id}:{operation_type}:{resource_id}`
- Example: `user_123:submit_guess:game_456`
- Prevents cross-resource key collisions
- Allows same key for different resources

**Pros**:
- Prevents collisions
- Flexible (same key can be used for different games)
- Clear structure
- Easy to debug

**Cons**:
- Slightly more complex key generation
- Need to parse scope for validation

**Implementation Details**:
```python
def generate_idempotency_key(user_id: str, operation: str, resource_id: str) -> str:
    return f"{user_id}:{operation}:{resource_id}:{uuid.uuid4()}"

# Examples
# user_123:submit_guess:game_456:abc-123-def
# user_123:create_game:abc-789-xyz
# user_456:submit_guess:game_789:def-456-ghi
```

```python
def check_idempotency(key: str) -> Optional[Response]:
    # Parse key to validate scope
    parts = key.split(':')
    user_id = parts[0]
    operation = parts[1]
    resource_id = parts[2]
    # Check Redis
    return redis.get(f"idempotency:{key}")
```

---

#### Option B: Global Scope
**Implementation**:
- Keys must be globally unique
- Client generates UUID for each request
- Simple but inflexible

**Pros**:
- Simplest implementation
- No scope parsing needed

**Cons**:
- Client must track unique keys per resource
- Risk of key collision if client reuses keys
- Less flexible

**Implementation Details**:
```python
# Client generates UUID
const idempotencyKey = uuidv4();
```

---

#### Option C: Per-User Scope
**Implementation**:
- Keys unique per user only
- Scope: `{user_id}:{uuid}`
- Same key can be used for different operations

**Pros**:
- Simpler than hierarchical
- Prevents cross-user collisions

**Cons**:
- Still risk of same-key collisions for different operations
- Less granular control

---

#### Option D: Per-Operation Scope
**Implementation**:
- Keys unique per operation type
- Scope: `{operation}:{uuid}`
- Very flexible but complex

**Pros**:
- Most flexible
- Keys can be reused across users (rarely needed)

**Cons**:
- Over-engineered
- Unnecessary complexity

---

**Recommendation**: Option A (Hierarchical Scope)
**Rationale**:
- Prevents collisions
- Clear structure
- Industry standard approach
- Easy to debug and validate

**Impact**:
- Backend: Change idempotency key generation to include scope
- Frontend: API client generates scoped keys
- Redis: Key format unchanged (just content changes)
- Complexity: Minimal increase

---

### Fix #7: Logout Cookie Clearing

**Problem**:
- Design mentions POST /api/auth/logout
- Doesn't specify how to clear httpOnly refresh token cookie
- Client cannot delete httpOnly cookies (JavaScript can't access them)
- Need server-side cookie clearing

**Solution Options**:

#### Option A: Server-Side Cookie Deletion (RECOMMENDED)
**Implementation**:
- Logout endpoint returns Set-Cookie header with expired cookie
- Client-side: Clear access token from sessionStorage
- Backend: Delete refresh token from database

**Pros**:
- Correct implementation of httpOnly cookies
- Client cannot interfere with logout
- Industry standard

**Cons**:
- Requires server-side cookie handling
- Slightly more complex

**Implementation Details**:
```python
@router.post("/api/auth/logout")
async def logout(
    response: Response,
    user_id: str = Depends(get_current_user)
):
    # Delete from database
    await session_repository.delete(user_id)
    # Clear cookie
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="strict"
    )
    return {"message": "Logged out"}
```

```javascript
// Client-side
async function logout() {
  await apiClient.logout();
  sessionStorage.removeItem('access_token');
  setAuthState(null);
}
```

---

#### Option B: Client-Side Cookie Deletion
**Implementation**:
- Try to delete cookie from client
- Won't work for httpOnly cookies

**Pros**:
- Simple

**Cons**:
- **Won't work**: JavaScript can't access httpOnly cookies
- Incorrect implementation

---

#### Option C: No Cookie Clearing
**Implementation**:
- Delete from database only
- Cookie expires naturally (7 days)

**Pros**:
- Simplest

**Cons**:
- **Security Risk**: Cookie remains valid even after logout
- Not production-ready
- Violates security requirements

---

**Recommendation**: Option A (Server-Side Cookie Deletion)
**Rationale**:
- Only correct way to handle httpOnly cookies
- Industry standard
- Secure implementation

**Impact**:
- Backend: Add cookie deletion to logout endpoint
- Frontend: Clear access token from sessionStorage
- Security: Proper logout implementation
- Complexity: Minimal

---

## Important Fixes (Should Address)

### Fix #8: Async Write Queue Failure Handling

**Problem**:
- Design mentions dead letter queue for permanently failed writes
- No retry policy specified
- No queue size limits
- No alerting strategy

**Solution Options**:

#### Option A: Configurable Retry with Dead Letter Queue (RECOMMENDED)
**Implementation**:
- Retry policy: 3 retries with exponential backoff (1s, 5s, 15s)
- Dead letter queue after 3 failures
- Alert on queue depth > 1000
- Maximum queue size: 10,000 (reject new writes if full)

**Pros**:
- Robust error handling
- Prevents queue overflow
- Monitoring and alerting
- Industry standard

**Cons**:
- More complex implementation
- Need monitoring setup

**Implementation Details**:
```python
class AsyncWriteQueue:
    def __init__(self):
        self.max_retries = 3
        self.backoff_delays = [1, 5, 15]  # seconds
        self.max_queue_size = 10000
        self.alert_threshold = 1000

    async def enqueue(self, task):
        if self.queue_size >= self.max_queue_size:
            raise QueueFullError()
        await self.queue.push(task)

    async def process_task(self, task):
        for attempt in range(self.max_retries):
            try:
                await self.execute(task)
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    await self.dead_letter_queue.push(task)
                    await self.alert(f"Task failed: {task}")
                else:
                    await asyncio.sleep(self.backoff_delays[attempt])
```

---

#### Option B: Infinite Retry
**Implementation**:
- Retry forever until success
- No dead letter queue

**Pros**:
- Simple
- Eventually succeeds (if transient errors)

**Cons**:
- Can block queue permanently
- No way to detect permanent failures
- Not production-ready

---

#### Option C: No Retry
**Implementation**:
- Fail immediately on error
- Dead letter queue for all failures

**Pros**:
- Simplest

**Cons**:
- Too aggressive (many transient errors)
- Unnecessary dead letter queue usage

---

**Recommendation**: Option A (Configurable Retry)
**Rationale**:
- Robust production-ready approach
- Handles transient errors
- Prevents queue overflow
- Monitoring and alerting

**Impact**:
- Backend: Add retry logic to async write queue
- Monitoring: Add queue depth monitoring
- Complexity: Moderate increase
- Reliability: Significant improvement

---

### Fix #9: Cache Invalidation Strategy

**Problem**:
- Design specifies TTLs for cache entries
- Doesn't specify how to invalidate cache when data changes
- Stale data until TTL expires (up to 24 hours for some data)

**Solution Options**:

#### Option A: Write-Through + Explicit Invalidation (RECOMMENDED)
**Implementation**:
- Update cache on write (write-through)
- Set TTL as backup
- Explicitly delete cache keys on data updates
- Hybrid approach: cache-aside with invalidation

**Pros**:
- Fresh data on updates
- TTL as safety net
- Best of both worlds

**Cons**:
- More complex logic
- Need to track all cache keys

**Implementation Details**:
```python
# Update user profile
async def update_user(user_id: str, data: dict):
    # Update database
    await user_repository.update(user_id, data)
    # Invalidate cache
    await redis.delete(f"user_session:{user_id}")
    await redis.delete(f"user_stats:{user_id}")
    # Update cache (write-through)
    await redis.set(f"user_session:{user_id}", updated_user, ex=24*60*60)
```

---

#### Option B: TTL Only (Current Design)
**Implementation**:
- Only use TTL
- No explicit invalidation
- Data eventually fresh

**Pros**:
- Simplest

**Cons**:
- Stale data until TTL expires
- Poor UX for profile updates
- Not production-ready

---

#### Option C: Event-Driven Invalidation
**Implementation**:
- Publish events on data changes
- Cache subscribers invalidate on events
- More complex but scalable

**Pros**:
- Scalable architecture
- Decoupled components

**Cons**:
- Over-engineered for this scope
- Complex implementation
- Not needed for assessment

---

**Recommendation**: Option A (Write-Through + Explicit Invalidation)
**Rationale**:
- Fresh data on updates
- TTL as safety net
- Simple implementation
- Production-ready

**Impact**:
- Backend: Add cache invalidation to update operations
- Complexity: Moderate increase
- UX: Significant improvement (fresh data)
- Performance: Minimal impact

---

### Fix #10: Leaderboard Cache Update Frequency

**Problem**:
- Design says "refresh every 5 minutes"
- Competitive game - users expect immediate rank updates after winning
- 5-minute delay is frustrating

**Solution Options**:

#### Option A: Event-Driven + Periodic Fallback (RECOMMENDED)
**Implementation**:
- Invalidate leaderboard cache on game completion
- Periodic refresh every 5 minutes as backup
- Gives immediate updates with periodic sync as safety net

**Pros**:
- Immediate updates on game completion
- Periodic sync as safety net
- Best UX

**Cons**:
- More complex logic
- Need to trigger invalidation

**Implementation Details**:
```python
# On game completion
async def complete_game(game_id: str):
    # ... game completion logic ...
    # Invalidate leaderboard cache
    await redis.delete("leaderboard:global")
    await redis.delete(f"leaderboard:daily:{date}")

# Background job (fallback)
async def refresh_leaderboards():
    while True:
        await leaderboard_service.refresh_global()
        await leaderboard_service.refresh_daily()
        await asyncio.sleep(5*60)  # 5 minutes
```

---

#### Option B: Periodic Only (Current Design)
**Implementation**:
- Refresh every 5 minutes
- No event-driven updates

**Pros**:
- Simple

**Cons**:
- Poor UX (5-minute delay)
- Frustrating for competitive players

---

#### Option C: Real-Time (WebSockets)
**Implementation**:
- Push leaderboard updates via WebSockets
- Immediate updates for all users

**Pros**:
- Best UX
- Real-time updates

**Cons**:
- Over-engineered for this scope
- Complex implementation
- Not needed for assessment

---

**Recommendation**: Option A (Event-Driven + Periodic Fallback)
**Rationale**:
- Immediate updates on game completion
- Periodic sync as safety net
- Simple implementation
- Great UX

**Impact**:
- Backend: Add cache invalidation to game completion
- Complexity: Minor increase
- UX: Significant improvement
- Performance: Minimal impact

---

### Fix #11: Word of the Day Word Length

**Problem**:
- Custom games allow configurable word length (5-8)
- Word of the Day - what's the word length?
- Not specified in design

**Solution Options**:

#### Option A: Always 5 Letters (RECOMMENDED)
**Implementation**:
- Word of the Day is always 5 letters
- Consistent with original Wordle
- Traditional daily challenge

**Pros**:
- Consistent with original Wordle
- Simple
- Familiar to users
- Easy to compare with original Wordle

**Cons**:
- Less variety
- Users might want longer words

---

#### Option B: Rotates Daily
**Implementation**:
- Word length rotates: 5, 6, 7, 8, then back to 5
- Different challenge each day
- Display word length prominently

**Pros**:
- More variety
- Different challenge each day

**Cons**:
- Confusing for users
- Breaks consistency with original Wordle
- Harder to compare across days

---

#### Option C: User Selectable
**Implementation**:
- User selects word length for Word of the Day
- Multiple Word of the Day challenges per day

**Pros**:
- More flexibility
- Users can choose preferred length

**Cons**:
- Breaks "same word for all users" requirement
- Fragmented user base
- More complex

---

**Recommendation**: Option A (Always 5 Letters)
**Rationale**:
- Consistent with original Wordle
- Simple
- Familiar to users
- Aligns with "Wordle" brand

**Impact**:
- Backend: Hardcode word length to 5 for WOD
- Frontend: Display "5-letter word" prominently
- Complexity: No change
- UX: Consistent with expectations

---

### Fix #12: Stats Distribution Across Word Lengths

**Problem**:
- Design tracks "guess distribution (won in 1, 2, 3, 4, 5, 6 turns)"
- But 8-letter words have 9 turns (N+1)
- How to track distribution across different word lengths?

**Solution Options**:

#### Option A: Per-Word-Length Distribution (RECOMMENDED)
**Implementation**:
- Track distribution separately for each word length
- Structure: `{5: {1: 5, 2: 10, ...}, 6: {1: 3, 2: 7, ...}, ...}`
- Display distribution per word length in stats

**Pros**:
- Accurate stats per word length
- Clear comparison
- More informative

**Cons**:
- More complex data structure
- More complex display

**Implementation Details**:
```python
{
  "guess_distribution": {
    "5": {"1": 5, "2": 10, "3": 20, "4": 25, "5": 8, "6": 2},
    "6": {"1": 3, "2": 7, "3": 15, "4": 18, "5": 6, "6": 3, "7": 1},
    "7": {"1": 2, "2": 5, "3": 12, "4": 15, "5": 5, "6": 2, "7": 1, "8": 0},
    "8": {"1": 1, "2": 3, "3": 10, "4": 12, "5": 4, "6": 1, "7": 0, "8": 0, "9": 0}
  }
}
```

---

#### Option B: Normalized Distribution
**Implementation**:
- Track distribution as percentage of max turns
- Structure: {"1/6": 5, "2/6": 10, ...}
- Normalize across word lengths

**Pros**:
- Unified distribution
- Simpler data structure

**Cons**:
- Less intuitive for users
- Harder to understand
- Loses granularity

---

#### Option C: Max Turns Fixed at 6
**Implementation**:
- All games have 6 turns regardless of word length
- Simplifies stats
- But breaks N+1 rule

**Pros**:
- Simplest stats
- Consistent with original Wordle

**Cons**:
- Breaks "N+1 turns" requirement
- Harder for longer words
- Not fair across word lengths

---

**Recommendation**: Option A (Per-Word-Length Distribution)
**Rationale**:
- Accurate stats per word length
- Clear comparison
- More informative for users
- Fair comparison across word lengths

**Impact**:
- Backend: Change stats data structure
- Database: Update guess_distribution column structure
- Frontend: Display distribution per word length
- Complexity: Moderate increase
- UX: More informative stats

---

### Fix #13: Feedback Engine Duplicate Letters Algorithm

**Problem**:
- Design says "handles duplicate letters correctly"
- This is the hardest part of Wordle logic
- No algorithm documented
- Example: Target "APPLE", guess "PAPER" - how should feedback work?

**Solution Options**:

#### Option A: Multi-Pass Algorithm (RECOMMENDED)
**Implementation**:
- Pass 1: Mark green letters (correct position)
- Pass 2: Count remaining letters in target
- Pass 3: Mark yellow letters (wrong position) up to remaining count
- Pass 4: Mark gray letters

**Pros**:
- Correct implementation
- Industry standard algorithm
- Handles all edge cases

**Cons**:
- More complex than naive approach
- Need to document clearly

**Implementation Details**:
```python
def calculate_feedback(target: str, guess: str) -> List[LetterFeedback]:
    result = [{'letter': g, 'color': 'gray'} for g in guess]
    target_chars = list(target)
    guess_chars = list(guess)

    # Pass 1: Mark green letters
    for i in range(len(guess)):
        if guess_chars[i] == target_chars[i]:
            result[i]['color'] = 'green'
            target_chars[i] = None  # Mark as used
            guess_chars[i] = None

    # Pass 2: Count remaining letters in target
    target_remaining = [c for c in target_chars if c is not None]

    # Pass 3: Mark yellow letters
    for i in range(len(guess)):
        if guess_chars[i] is not None and guess_chars[i] in target_remaining:
            result[i]['color'] = 'yellow'
            target_remaining.remove(guess_chars[i])

    return result
```

**Example**:
```
Target: APPLE
Guess: PAPER

Pass 1 (green):
- P(0) != A, gray
- A(1) != P, gray
- P(2) == P, green ✓
- E(3) != L, gray
- R(4) != E, gray

After pass 1: target = [A, None, None, L, E]

Pass 2 (count remaining):
Remaining: [A, L, E]

Pass 3 (yellow):
- P(0): Not in remaining, gray
- A(1): In remaining, yellow ✓
- E(3): In remaining, yellow ✓
- R(4): Not in remaining, gray

Final: P(gray), A(yellow), P(green), E(yellow), R(gray)
```

---

#### Option B: Naive Algorithm
**Implementation**:
- Single pass, mark all matches
- Doesn't handle duplicates correctly

**Pros**:
- Simple

**Cons**:
- **Incorrect**: Doesn't handle duplicates properly
- Example: Target "APPLE", guess "PAPER" would show both P's as yellow (wrong)

---

#### Option C: Count-Based Algorithm
**Implementation**:
- Count letter frequencies in target
- Decrement counts as matches found
- Similar to multi-pass but different approach

**Pros**:
- Correct implementation
- Different approach

**Cons**:
- More complex to understand
- Same complexity as multi-pass

---

**Recommendation**: Option A (Multi-Pass Algorithm)
**Rationale**:
- Correct implementation
- Industry standard
- Clear and documented
- Handles all edge cases

**Impact**:
- Backend: Implement multi-pass algorithm in feedback engine
- Tests: Add comprehensive test cases for duplicate letters
- Complexity: Moderate increase
- Correctness: Critical improvement

---

### Fix #14: Offline Sync Conflict Resolution

**Problem**:
- Design mentions "resolve conflicts with server state"
- Doesn't specify conflict resolution strategy
- What if I made 3 guesses offline, but played on another device?

**Solution Options**:

#### Option A: Server-Wins Simple (RECOMMENDED for Assessment)
**Implementation**:
- Server state is source of truth
- On reconnection, client resyncs from server
- Offline changes discarded if conflict
- Simple approach

**Pros**:
- Simplest implementation
- No complex conflict resolution
- Acceptable for assessment

**Cons**:
- Users lose offline progress if conflict
- Poor UX in conflict scenarios

**Implementation Details**:
```javascript
async function syncWithServer() {
  const serverState = await apiClient.getGameState(gameId);
  setGameState(serverState);  // Replace local state
  clearOfflineQueue();  // Discard pending changes
}
```

---

#### Option B: Last-Write-Wins
**Implementation**:
- Compare timestamps
- Most recent write wins
- Merge changes where possible

**Pros**:
- Better UX (less data loss)
- More sophisticated

**Cons**:
- More complex implementation
- Still some data loss possible
- Need timestamp tracking

---

#### Option C: Manual Conflict Resolution
**Implementation**:
- Detect conflicts
- Prompt user to choose
- Complex UI

**Pros**:
- Best UX (user control)
- No automatic data loss

**Cons**:
- Over-engineered for this scope
- Complex UI
- Poor UX (user has to resolve conflicts)

---

#### Option D: Merge with Reconciliation
**Implementation**:
- Merge changes where possible
- Automatic reconciliation
- Complex logic

**Pros**:
- Best data preservation
- Sophisticated

**Cons**:
- Over-engineered
- Complex implementation
- Not needed for assessment

---

**Recommendation**: Option A (Server-Wins Simple)
**Rationale**:
- Simplest implementation
- Acceptable for assessment
- Offline play is edge case
- Most users will be online

**Impact**:
- Frontend: Simple sync logic (server state replaces local)
- Complexity: Minimal
- UX: Acceptable for assessment
- Reliability: Server state is source of truth

---

### Fix #15: Email Service for Password Reset

**Problem**:
- Design mentions password reset flow
- No email service component to send reset emails
- No details on token generation/storage/validation

**Solution Options**:

#### Option A: Add Email Service (Full Implementation)
**Implementation**:
- Add email service component (SES, SendGrid, etc.)
- Generate reset tokens
- Store tokens in database with expiration
- Send reset emails
- Validate tokens on password reset

**Pros**:
- Complete implementation
- Production-ready

**Cons**:
- Significant complexity increase
- Requires email service account (SES, SendGrid)
- Out of scope for assessment
- Adds timeline risk

**Implementation Details**:
```python
# New component: email_service
class EmailService:
    async def send_password_reset(self, email: str, token: str):
        reset_link = f"https://app.com/reset-password?token={token}"
        await self.send_email(email, "Reset your password", reset_link)

# New component: password_reset_service
class PasswordResetService:
    async def request_reset(self, email: str):
        token = generate_secure_token()
        await self.store_token(email, token, ttl=1*60*60)
        await email_service.send_password_reset(email, token)

    async def reset_password(self, token: str, new_password: str):
        if not await self.validate_token(token):
            raise InvalidTokenError()
        await self.update_password(token, new_password)
        await self.delete_token(token)
```

---

#### Option B: Mark as Out of Scope (RECOMMENDED for Assessment)
**Implementation**:
- Document password reset as future enhancement
- Remove from current design
- Add to "Future Enhancements" section

**Pros**:
- Reduces scope
- Faster implementation
- Focus on core features
- Lower risk

**Cons**:
- Incomplete auth system
- Users can't reset passwords (UX issue)
- Not production-ready

**Mitigation**:
- Document as future enhancement
- Provide admin reset as workaround
- Accept limitation for assessment

---

#### Option C: Mock Email Service
**Implementation**:
- Implement email service but log to console instead of sending
- Complete logic without actual email sending
- Can be swapped for real service later

**Pros**:
- Complete implementation
- No external dependencies
- Easy to swap later

**Cons**:
- Still adds complexity
- Doesn't actually send emails
- Users can't actually reset passwords

---

**Recommendation**: Option B (Mark as Out of Scope)
**Rationale**:
- Reduces scope for assessment
- Focus on core game features
- Can be added later
- Acceptable limitation for assessment

**Impact**:
- Backend: Remove password reset from auth service
- Design: Document as future enhancement
- Timeline: Significant reduction
- Completeness: Minor reduction (acceptable)

---

## Trade-off Decisions

### Trade-off 1: Component Complexity vs Timeline
**Current**: 35 total components (18 backend, 17 frontend)
**Concern**: May be over-engineered for assessment timeline

**Recommendation**: Implement MVP subset first
- Phase 1 (Core): Skip friends leaderboard, advanced offline sync, email service
- Phase 2 (Enhancement): Add if time permits
- This is a "feature flag" approach - design stays the same, implementation phases change

---

### Trade-off 2: Redis vs In-Memory
**Current**: Redis for caching
**Concern**: Adds infrastructure complexity

**Recommendation**: Keep Redis, document fallback
- Use Redis for production
- Document in-memory fallback for local dev
- Environment variable to switch

---

### Trade-off 3: PostgreSQL vs SQLite
**Current**: PostgreSQL
**Concern**: Requires database setup

**Recommendation**: Support both
- SQLite for local development
- PostgreSQL for production
- Environment variable to switch
- Same code, different drivers

---

### Trade-off 4: Celery vs asyncio
**Current**: Celery for async writes
**Concern**: Celery adds significant complexity

**Recommendation**: Use asyncio for assessment
- Use `asyncio.create_task` for background tasks
- Document Celery for production
- Simpler for assessment

---

## Summary of Recommended Fixes

### Critical (Must Implement)
1. ✅ Practice Mode: Persist with `game_mode='practice'` flag
2. ✅ Word of the Day: Use UTC timezone
3. ✅ Access Token: Use sessionStorage
4. ✅ Game State: Write-through caching (sync DB write)
5. ✅ Guest Mode: Add 6-hour refresh tokens
6. ✅ Idempotency: Hierarchical scope `{user_id}:{operation}:{resource_id}`
7. ✅ Logout: Server-side cookie deletion

### Important (Should Implement)
8. ✅ Async Write: 3 retries with exponential backoff, DLQ, queue limits
9. ✅ Cache Invalidation: Write-through + explicit invalidation
10. ✅ Leaderboard: Event-driven + periodic fallback
11. ✅ Word of the Day: Always 5 letters
12. ✅ Stats: Per-word-length distribution
13. ✅ Feedback: Multi-pass algorithm for duplicates
14. ✅ Offline Sync: Server-wins simple approach
15. ✅ Password Reset: Mark as out of scope

### Trade-offs (Decisions Made)
- Keep component complexity (production-ready design)
- Use Redis with in-memory fallback documented
- Support SQLite/PostgreSQL via environment
- Use asyncio instead of Celery for assessment
