# Outbox Pattern Implementation

## Purpose

Ensure reliable, atomic event publishing for leaderboard updates and UI notifications using the outbox pattern.

## Why Outbox Pattern?

### Problem
When a game completes, we need to:
1. Update game status in database
2. Update user stats
3. Update leaderboards
4. Notify UI of changes

Without outbox pattern:
- **Race conditions**: Game saved but stats update fails
- **Data inconsistency**: Leaderboard shows stale data
- **Lost events**: System crashes before notification sent
- **Non-atomic**: Separate transactions can fail independently

### Solution
Outbox pattern ensures:
- **Atomicity**: Event written in same transaction as data change
- **Reliability**: Events persist even if system crashes
- **Idempotency**: Failed events can be retried safely
- **Ordering**: Events processed in order
- **Eventual consistency**: UI updates happen reliably

## Architecture

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
Background Poller
    ↓
4. Read Unprocessed Events
    ↓
5. Process Event (Update Leaderboard, etc.)
    ↓
6. Mark Event as Processed
    ↓
[UI Notified via WebSocket/SSE]
```

## Database Schema

### Outbox Table

```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,  -- e.g., game_id, user_id
    aggregate_type VARCHAR(50) NOT NULL,  -- e.g., 'game', 'user'
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    CONSTRAINT check_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes for efficient polling
CREATE INDEX idx_outbox_status_created ON outbox_events(status, created_at);
CREATE INDEX idx_outbox_aggregate ON outbox_events(aggregate_type, aggregate_id);
```

## Event Types

### GameCompletedEvent
**Trigger**: When a game is won or lost

**Payload**:
```json
{
  "event_type": "game_completed",
  "aggregate_id": "game_123",
  "aggregate_type": "game",
  "payload": {
    "game_id": "game_123",
    "user_id": "user_456",
    "game_mode": "custom",
    "word_length": 5,
    "status": "won",
    "guesses_count": 4,
    "completed_at": "2024-01-01T00:05:00Z"
  }
}
```

**Actions**:
- Update user stats
- Update global leaderboard
- Update daily leaderboard (if word of day)
- Invalidate cache

### UserStatsUpdatedEvent
**Trigger**: When user stats are recalculated

**Payload**:
```json
{
  "event_type": "user_stats_updated",
  "aggregate_id": "user_456",
  "aggregate_type": "user",
  "payload": {
    "user_id": "user_456",
    "games_played": 100,
    "games_won": 70,
    "win_rate": 0.7,
    "current_streak": 5,
    "best_streak": 15
  }
}
```

**Actions**:
- Invalidate user stats cache
- Notify UI of stats change (if user is viewing their profile)

### LeaderboardUpdatedEvent
**Trigger**: When leaderboard is recalculated

**Payload**:
```json
{
  "event_type": "leaderboard_updated",
  "aggregate_id": "global",
  "aggregate_type": "leaderboard",
  "payload": {
    "leaderboard_type": "global",
    "date": null,
    "updated_at": "2024-01-01T00:05:00Z"
  }
}
```

**Actions**:
- Invalidate leaderboard cache
- Notify UI clients viewing leaderboard

## Implementation

### Backend Components

#### 1. Outbox Repository

**Files**:
```
backend/
├── app/
│   ├── outbox/
│   │   ├── __init__.py
│   │   ├── infra/
│   │   │   ├── __init__.py
│   │   │   └── outbox_repository.py  # Interface
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── postgres_outbox_repository.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_unit_outbox.py
│   │       └── test_integ_outbox.py
```

**Interface**:
```python
# app/outbox/infra/outbox_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class OutboxEvent(BaseModel):
    id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    payload: dict
    status: str
    created_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int

class OutboxRepository(ABC):
    @abstractmethod
    async def save_event(self, event: OutboxEvent) -> OutboxEvent:
        """Save an outbox event"""
        pass

    @abstractmethod
    async def get_pending_events(self, limit: int = 100) -> List[OutboxEvent]:
        """Get pending events for processing"""
        pass

    @abstractmethod
    async def mark_as_processing(self, event_id: str) -> None:
        """Mark event as being processed"""
        pass

    @abstractmethod
    async def mark_as_completed(self, event_id: str) -> None:
        """Mark event as successfully processed"""
        pass

    @abstractmethod
    async def mark_as_failed(self, event_id: str, error_message: str) -> None:
        """Mark event as failed"""
        pass

    @abstractmethod
    async def delete_old_events(self, days: int = 7) -> int:
        """Delete old completed events"""
        pass
```

**Implementation**:
```python
# app/outbox/implementation/postgres_outbox_repository.py
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.outbox.infra.outbox_repository import OutboxRepository, OutboxEvent
import uuid

class PostgresOutboxRepository(OutboxRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_event(self, event: OutboxEvent) -> OutboxEvent:
        if not event.id:
            event.id = str(uuid.uuid4())
        event.created_at = datetime.utcnow()
        event.status = 'pending'
        event.retry_count = 0

        from app.database.models import OutboxEventModel
        db_event = OutboxEventModel(**event.dict())
        self.session.add(db_event)
        await self.session.flush()
        await self.session.refresh(db_event)

        return OutboxEvent(**db_event.__dict__)

    async def get_pending_events(self, limit: int = 100) -> List[OutboxEvent]:
        from app.database.models import OutboxEventModel

        query = (
            select(OutboxEventModel)
            .where(OutboxEventModel.status == 'pending')
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
        )
        result = await self.session.execute(query)
        events = result.scalars().all()
        return [OutboxEvent(**e.__dict__) for e in events]

    async def mark_as_processing(self, event_id: str) -> None:
        from app.database.models import OutboxEventModel

        query = (
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(status='processing')
        )
        await self.session.execute(query)

    async def mark_as_completed(self, event_id: str) -> None:
        from app.database.models import OutboxEventModel

        query = (
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(
                status='completed',
                processed_at=datetime.utcnow()
            )
        )
        await self.session.execute(query)

    async def mark_as_failed(self, event_id: str, error_message: str) -> None:
        from app.database.models import OutboxEventModel

        query = (
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(
                status='failed',
                error_message=error_message,
                retry_count=OutboxEventModel.retry_count + 1
            )
        )
        await self.session.execute(query)

    async def delete_old_events(self, days: int = 7) -> int:
        from app.database.models import OutboxEventModel

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = (
            delete(OutboxEventModel)
            .where(
                OutboxEventModel.status == 'completed',
                OutboxEventModel.processed_at < cutoff_date
            )
        )
        result = await self.session.execute(query)
        return result.rowcount
```

#### 2. Outbox Event Publisher

**Files**:
```
backend/
├── app/
│   ├── outbox/
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── outbox_publisher.py
```

**Implementation**:
```python
# app/outbox/implementation/outbox_publisher.py
from app.outbox.infra.outbox_repository import OutboxEvent
from typing import Callable, Dict
import structlog

logger = structlog.get_logger()

class OutboxPublisher:
    def __init__(self, outbox_repository):
        self.outbox_repository = outbox_repository
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for an event type"""
        self.handlers[event_type] = handler

    async def publish_event(self, event_type: str, aggregate_id: str, aggregate_type: str, payload: dict):
        """Publish an event to the outbox"""
        event = OutboxEvent(
            id=None,
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=payload,
            status='pending',
            created_at=None,
            processed_at=None,
            error_message=None,
            retry_count=0
        )

        saved_event = await self.outbox_repository.save_event(event)
        logger.info(
            "Event published to outbox",
            event_id=saved_event.id,
            event_type=event_type,
            aggregate_id=aggregate_id
        )
        return saved_event

    async def process_events(self):
        """Process pending events"""
        events = await self.outbox_repository.get_pending_events(limit=100)

        for event in events:
            try:
                # Mark as processing
                await self.outbox_repository.mark_as_processing(event.id)

                # Get handler
                handler = self.handlers.get(event.event_type)
                if not handler:
                    logger.warning("No handler for event type", event_type=event.event_type)
                    await self.outbox_repository.mark_as_completed(event.id)
                    continue

                # Process event
                await handler(event.payload)

                # Mark as completed
                await self.outbox_repository.mark_as_completed(event.id)
                logger.info("Event processed successfully", event_id=event.id)

            except Exception as e:
                logger.error(
                    "Event processing failed",
                    event_id=event.id,
                    error=str(e)
                )
                await self.outbox_repository.mark_as_failed(event.id, str(e))
```

#### 3. Event Handlers

**Files**:
```
backend/
├── app/
│   ├── event_handlers/
│   │   ├── __init__.py
│   │   ├── game_completed_handler.py
│   │   ├── user_stats_updated_handler.py
│   │   └── leaderboard_updated_handler.py
```

**Game Completed Handler**:
```python
# app/event_handlers/game_completed_handler.py
from app.stats_service.stats_service import StatsService
from app.leaderboard.leaderboard_service import LeaderboardService
import structlog

logger = structlog.get_logger()

class GameCompletedHandler:
    def __init__(self, stats_service: StatsService, leaderboard_service: LeaderboardService):
        self.stats_service = stats_service
        self.leaderboard_service = leaderboard_service

    async def handle(self, payload: dict):
        """Handle game completed event"""
        game_id = payload['game_id']
        user_id = payload['user_id']
        game_mode = payload['game_mode']
        status = payload['status']

        logger.info("Processing game completed event", game_id=game_id, user_id=user_id)

        # Update user stats
        if game_mode != 'practice':  # Don't update stats for practice games
            await self.stats_service.update_user_stats(user_id, payload)

        # Update leaderboards
        if game_mode == 'word_of_day':
            await self.leaderboard_service.update_daily_leaderboard(payload['completed_at'])
        else:
            await self.leaderboard_service.update_global_leaderboard()

        # Invalidate caches
        await self.stats_service.invalidate_user_stats_cache(user_id)
        await self.leaderboard_service.invalidate_leaderboard_cache()

        logger.info("Game completed event processed", game_id=game_id)
```

#### 4. Background Poller

**Files**:
```
backend/
├── app/
│   ├── outbox/
│   │   ├── implementation/
│   │   │   ├── __init__.py
│   │   │   └── outbox_poller.py
```

**Implementation**:
```python
# app/outbox/implementation/outbox_poller.py
import asyncio
from app.outbox.implementation.outbox_publisher import OutboxPublisher
import structlog

logger = structlog.get_logger()

class OutboxPoller:
    def __init__(self, publisher: OutboxPublisher, poll_interval: int = 5):
        self.publisher = publisher
        self.poll_interval = poll_interval
        self.running = False

    async def start(self):
        """Start the background poller"""
        self.running = True
        logger.info("Outbox poller started")

        while self.running:
            try:
                await self.publisher.process_events()
            except Exception as e:
                logger.error("Error processing outbox events", error=str(e))

            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop the background poller"""
        self.running = False
        logger.info("Outbox poller stopped")
```

#### 5. Integration with Game Service

**Modified Game Service**:
```python
# app/game_service/implementation/game_service.py
from app.outbox.implementation.outbox_publisher import OutboxPublisher

class GameService:
    def __init__(
        self,
        game_repository,
        feedback_engine,
        outbox_publisher: OutboxPublisher
    ):
        self.game_repository = game_repository
        self.feedback_engine = feedback_engine
        self.outbox_publisher = outbox_publisher

    async def submit_guess(self, game_id: str, guess: str):
        # ... existing guess logic ...

        # Check if game is completed
        if game_status in ['won', 'lost']:
            # Publish event in same transaction
            await self.outbox_publisher.publish_event(
                event_type='game_completed',
                aggregate_id=game_id,
                aggregate_type='game',
                payload={
                    'game_id': game_id,
                    'user_id': user_id,
                    'game_mode': game.game_mode,
                    'word_length': game.word_length,
                    'status': game_status,
                    'guesses_count': len(game.guesses),
                    'completed_at': datetime.utcnow().isoformat()
                }
            )

        return game_state
```

### Frontend Integration

#### Real-time Updates via Server-Sent Events (SSE)

**Backend SSE Endpoint**:
```python
# app/api/routers/sse_router.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

async def event_generator(user_id: str):
    """Generate SSE events for user"""
    while True:
        # Check for new events in outbox related to user
        # This could be optimized with Redis pub/sub
        await asyncio.sleep(1)  # Poll every second

@router.get("/api/events")
async def sse_endpoint(user_id: str = Depends(get_current_user)):
    return StreamingResponse(
        event_generator(user_id),
        media_type="text/event-stream"
    )
```

**Frontend SSE Client**:
```javascript
// src/hooks/useSSE.js
import { useEffect, useState } from 'react';

export function useSSE(userId) {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const eventSource = new EventSource(`${API_URL}/api/events?user_id=${userId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
    };

    return () => {
      eventSource.close();
    };
  }, [userId]);

  return events;
}
```

**Usage in Leaderboard Component**:
```javascript
import { useSSE } from '../hooks/useSSE';

function LeaderboardDisplay() {
  const { user } = useAuth();
  const events = useSSE(user?.userId);
  const [leaderboard, setLeaderboard] = useState(initialLeaderboard);

  useEffect(() => {
    // Listen for leaderboard update events
    const leaderboardEvents = events.filter(e => e.event_type === 'leaderboard_updated');
    if (leaderboardEvents.length > 0) {
      // Refresh leaderboard
      fetchLeaderboard();
    }
  }, [events]);

  return (
    <div>
      <Leaderboard data={leaderboard} />
    </div>
  );
}
```

## Testing

### Unit Tests

```python
# tests/outbox/test_unit_outbox.py
import pytest
from app.outbox.implementation.postgres_outbox_repository import PostgresOutboxRepository

async def test_save_event(outbox_repo):
    event = OutboxEvent(
        id=None,
        event_type='game_completed',
        aggregate_id='game_123',
        aggregate_type='game',
        payload={'test': 'data'},
        status='pending',
        created_at=None,
        processed_at=None,
        error_message=None,
        retry_count=0
    )

    saved = await outbox_repo.save_event(event)
    assert saved.id is not None
    assert saved.status == 'pending'

async def test_get_pending_events(outbox_repo):
    # Create pending events
    await outbox_repo.save_event(test_event_1)
    await outbox_repo.save_event(test_event_2)

    events = await outbox_repo.get_pending_events()
    assert len(events) == 2
```

### Integration Tests

```python
# tests/outbox/test_integ_outbox.py
async def test_event_processing_flow(outbox_publisher, game_completed_handler):
    # Publish event
    event = await outbox_publisher.publish_event(
        event_type='game_completed',
        aggregate_id='game_123',
        aggregate_type='game',
        payload={'game_id': 'game_123', 'user_id': 'user_456'}
    )

    # Process events
    await outbox_publisher.process_events()

    # Verify handler was called
    # (would need to mock handler or check side effects)
```

## Monitoring

### Metrics

Track outbox metrics:
- Pending events count
- Processing time per event
- Failed events count
- Retry count distribution

**Implementation**:
```python
# In outbox publisher
async def process_events(self):
    events = await self.outbox_repository.get_pending_events()

    track_metric('outbox_pending_count', len(events))

    for event in events:
        start = time.time()
        try:
            await self._process_single_event(event)
            duration = time.time() - start
            track_metric('outbox_processing_duration_ms', duration * 1000)
        except Exception as e:
            track_metric('outbox_failed_count', 1)
```

### Alerts

Alert on:
- High pending event count (>1000)
- High failure rate (>10%)
- Events not processed for >5 minutes

## Performance Considerations

### Polling Interval
- Default: 5 seconds
- Can be increased for low-traffic systems
- Can be decreased for real-time requirements

### Batch Size
- Default: 100 events per poll
- Can be tuned based on throughput requirements

### Cleanup
- Delete completed events after 7 days
- Prevents table growth
- Can be adjusted based on retention requirements

### Database Indexes
Critical indexes for performance:
```sql
CREATE INDEX idx_outbox_status_created ON outbox_events(status, created_at);
CREATE INDEX idx_outbox_aggregate ON outbox_events(aggregate_type, aggregate_id);
```

## Future Enhancements

### 1. Redis Pub/Sub Instead of Polling
**Current**: Poll database every 5 seconds
**Enhancement**: Use Redis pub/sub for real-time notification
**Benefit**: Lower latency, less database load

**Implementation**:
```python
# After saving event, publish to Redis
await redis.publish(f"outbox:{event.event_type}", event.id)

# Poller subscribes to Redis channels
pubsub = redis.pubsub()
await pubsub.subscribe("outbox:game_completed")
async for message in pubsub.listen():
    await process_event(message.data)
```

### 2. Message Queue (RabbitMQ, Kafka)
**Current**: Database as queue
**Enhancement**: Use dedicated message queue
**Benefit**: Better scalability, more features (dead letter queues, etc.)

### 3. Event Sourcing
**Current**: Outbox pattern with current state
**Enhancement**: Full event sourcing (rebuild state from events)
**Benefit**: Complete audit trail, time travel debugging

## Impact

### Backend
- +1 outbox repository (~150 lines)
- +1 outbox publisher (~100 lines)
- +1 outbox poller (~50 lines)
- +3 event handlers (~150 lines)
- +1 database table (outbox_events)
- +2 indexes
- Modified game service (~20 lines)
- Total: ~470 lines

### Frontend
- +1 SSE hook (~40 lines)
- +1 SSE endpoint (~30 lines)
- Integration in components (~50 lines)
- Total: ~120 lines

### Total Impact
- ~590 lines of code
- Timeline: +2 days
- Complexity: Medium
- Benefit: High (reliable event processing, real-time updates)

## Recommendation

**Implement outbox pattern for**:
1. Game completion events (stats + leaderboard updates)
2. User stats updates (UI notifications)
3. Leaderboard updates (real-time leaderboard)

**Defer to future**:
- Redis pub/sub optimization
- Message queue migration
- Full event sourcing

This is a **critical pattern** for production reliability and should be implemented in **Phase 1** alongside core game logic.
