# Few-Shot Example: Task Planning

**Domain:** General | **Task Type:** Implementation Planning | **Complexity:** High

---

## User Request

```
I need to add real-time notifications to our web app. Users should see notifications for:
- New messages
- Friend requests
- System alerts

Plan the implementation.
```

## Claude Response

### Implementation Plan: Real-Time Notifications System

Comprehensive planning using **structured decomposition** approach.

---

## Phase 1: Requirements Analysis

### Functional Requirements

| Requirement | Priority | Details |
|-------------|----------|---------|
| **FR-1: Push notifications** | P0 (Critical) | Users receive notifications without page refresh |
| **FR-2: Notification types** | P0 | Messages, friend requests, system alerts |
| **FR-3: Notification history** | P1 (High) | View past 30 days of notifications |
| **FR-4: Mark as read** | P1 | Track read/unread status |
| **FR-5: Notification preferences** | P2 (Medium) | Enable/disable per type |
| **FR-6: Sound/desktop alerts** | P3 (Low) | Browser notifications API |

### Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Latency** | <500ms | User perceives real-time |
| **Scalability** | 10,000 concurrent users | Growth headroom |
| **Reliability** | 99.9% uptime | Critical user engagement feature |
| **Browser support** | Modern (Chrome 90+, Firefox 88+, Safari 14+) | 95% user coverage |

### Constraints

- **Budget:** Limited - use open source solutions
- **Timeline:** 3 weeks (MVP)
- **Team:** 2 developers (1 backend, 1 frontend)

---

## Phase 2: Architecture Design

### Technology Stack Selection

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE STACK                            │
├─────────────────────────────────────────────────────────────────┤
│  FRONTEND                                                        │
│  ├─► WebSocket Client (Socket.IO client or native WebSocket)    │
│  ├─► Notification UI Component (React/Vue)                      │
│  └─► Browser Notifications API (optional)                       │
│                                                                  │
│  BACKEND                                                         │
│  ├─► WebSocket Server (Socket.IO, ws, or Django Channels)       │
│  ├─► Message Queue (Redis Pub/Sub or RabbitMQ)                  │
│  ├─► Notification Service (Python/Node.js)                      │
│  └─► Database (PostgreSQL for persistence)                      │
│                                                                  │
│  INFRASTRUCTURE                                                  │
│  ├─► Load Balancer (nginx) for WebSocket connections            │
│  └─► Redis (caching + pub/sub)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Decision Records (ADRs)

#### ADR-001: WebSocket vs Server-Sent Events (SSE)

**Decision:** Use WebSockets

| Criterion | WebSocket | SSE | Winner |
|-----------|-----------|-----|--------|
| **Bidirectional** | ✅ Yes | ❌ No (server → client only) | WebSocket |
| **Browser support** | ✅ Universal | ⚠️ No IE11 | WebSocket |
| **Complexity** | Medium | Low | SSE |
| **Scalability** | High (with load balancing) | High | Tie |
| **Use case fit** | ✅ Interactive (mark as read) | ⚠️ Read-only | WebSocket |

**Rationale:** Need bidirectional for "mark as read" acknowledgments.

---

#### ADR-002: Socket.IO vs Native WebSocket

**Decision:** Use Socket.IO (for MVP)

**Pros:**
- ✅ Automatic reconnection
- ✅ Room-based broadcasting (easy user targeting)
- ✅ Fallback to polling if WebSocket unavailable
- ✅ Built-in heartbeat/ping-pong

**Cons:**
- ❌ Larger payload (protocol overhead)
- ❌ Additional dependency

**Trade-off:** Simplicity > Performance for MVP. Can optimize later.

---

#### ADR-003: Push vs Pull for Notification Delivery

**Decision:** Hybrid (Push via WebSocket + Pull on reconnect)

```
NORMAL FLOW (Push):
Event occurs → Backend publishes → WebSocket sends → Client displays

RECONNECTION FLOW (Pull):
Client reconnects → Fetch missed notifications → Display
```

**Rationale:** WebSocket can drop during network issues. Pull ensures no missed notifications.

---

## Phase 3: Database Schema

### Notifications Table

```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL,  -- 'message', 'friend_request', 'system_alert'
    title VARCHAR(255) NOT NULL,
    message TEXT,
    link VARCHAR(500),  -- URL to notification source
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- Optional: auto-delete old notifications

    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_user_unread (user_id, is_read) WHERE is_read = FALSE
);
```

### Notification Preferences Table

```sql
CREATE TABLE notification_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    messages_enabled BOOLEAN DEFAULT TRUE,
    friend_requests_enabled BOOLEAN DEFAULT TRUE,
    system_alerts_enabled BOOLEAN DEFAULT TRUE,
    desktop_notifications BOOLEAN DEFAULT FALSE,
    sound_enabled BOOLEAN DEFAULT TRUE
);
```

---

## Phase 4: API Design

### REST API Endpoints

```
GET    /api/notifications              # List notifications (paginated)
GET    /api/notifications/unread/count # Unread count
POST   /api/notifications/:id/read     # Mark as read
POST   /api/notifications/read-all     # Mark all as read
GET    /api/notifications/preferences  # Get preferences
PUT    /api/notifications/preferences  # Update preferences
DELETE /api/notifications/:id          # Delete notification
```

### WebSocket Events

**Client → Server:**
```javascript
// Authenticate
socket.emit('authenticate', { token: 'jwt_token' });

// Mark as read
socket.emit('notification:read', { notificationId: 123 });
```

**Server → Client:**
```javascript
// New notification
socket.on('notification:new', (data) => {
    // data: { id, type, title, message, link, created_at }
});

// Read acknowledgment
socket.on('notification:read_ack', (data) => {
    // data: { notificationId, success: true }
});
```

---

## Phase 5: Implementation Breakdown

### Sprint 1: Backend Core (Week 1)

| Task | Effort | Owner | Dependencies |
|------|--------|-------|--------------|
| **Task 1.1:** Database schema setup | 4h | Backend | - |
| **Task 1.2:** REST API endpoints | 8h | Backend | 1.1 |
| **Task 1.3:** WebSocket server setup (Socket.IO) | 6h | Backend | - |
| **Task 1.4:** Authentication middleware for WebSocket | 4h | Backend | 1.3 |
| **Task 1.5:** Notification service (create, send) | 6h | Backend | 1.2, 1.3 |
| **Task 1.6:** Redis pub/sub integration | 4h | Backend | 1.5 |
| **Task 1.7:** Unit tests (80% coverage) | 4h | Backend | 1.1-1.6 |

**Total:** 36h (5 days)

---

### Sprint 2: Frontend Integration (Week 2)

| Task | Effort | Owner | Dependencies |
|------|--------|-------|--------------|
| **Task 2.1:** WebSocket client setup | 4h | Frontend | Backend 1.3 |
| **Task 2.2:** Notification context/store (React) | 3h | Frontend | 2.1 |
| **Task 2.3:** Notification bell UI component | 5h | Frontend | 2.2 |
| **Task 2.4:** Notification list UI | 4h | Frontend | 2.3 |
| **Task 2.5:** Mark as read functionality | 3h | Frontend | 2.4 |
| **Task 2.6:** Real-time updates (WebSocket listener) | 4h | Frontend | 2.2, 2.3 |
| **Task 2.7:** Reconnection logic (fetch missed) | 4h | Frontend | 2.6 |
| **Task 2.8:** Notification preferences UI | 4h | Frontend | Backend 1.2 |
| **Task 2.9:** Unit tests (Jest + React Testing Library) | 3h | Frontend | 2.1-2.8 |

**Total:** 34h (5 days)

---

### Sprint 3: Polish & Deploy (Week 3)

| Task | Effort | Owner | Dependencies |
|------|--------|-------|--------------|
| **Task 3.1:** Browser notifications API integration | 4h | Frontend | 2.1-2.8 |
| **Task 3.2:** Sound alerts | 2h | Frontend | 2.6 |
| **Task 3.3:** Integration tests (E2E with Cypress) | 6h | Both | All |
| **Task 3.4:** Load testing (10k concurrent connections) | 4h | Backend | All |
| **Task 3.5:** Performance optimization | 4h | Both | 3.4 |
| **Task 3.6:** Documentation (API docs, setup guide) | 4h | Both | - |
| **Task 3.7:** Staging deployment | 3h | Backend | All |
| **Task 3.8:** Production deployment | 3h | Backend | 3.7 |
| **Task 3.9:** Monitoring setup (logs, metrics) | 4h | Backend | 3.8 |

**Total:** 34h (5 days)

---

## Phase 6: Risk Management

### Risk Matrix

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| **WebSocket scaling issues** | Medium | High | Use Redis adapter for Socket.IO (multi-instance support) |
| **Notification spam** | Medium | Medium | Rate limiting (max 10 notifications/min per user) |
| **Database overload** | Low | High | Implement notification retention policy (30 days) |
| **Browser compatibility** | Low | Medium | Feature detection + graceful degradation (polling fallback) |
| **Timeline delay** | Medium | Medium | Cut P3 features (browser notifications, sound) if needed |

---

## Phase 7: Testing Strategy

### Test Coverage Targets

| Level | Coverage | Tools |
|-------|----------|-------|
| **Unit Tests** | 80%+ | pytest (backend), Jest (frontend) |
| **Integration Tests** | Key flows | pytest-asyncio |
| **E2E Tests** | 5 critical paths | Cypress |
| **Load Tests** | 10k concurrent users | Locust |
| **Security Tests** | OWASP Top 10 | OWASP ZAP |

### Critical Test Scenarios

```
✅ T1: User receives notification within 500ms of event
✅ T2: Notification marked as read updates database and UI
✅ T3: Reconnection fetches missed notifications
✅ T4: 10,000 concurrent WebSocket connections stable
✅ T5: Unauthorized users cannot connect to WebSocket
✅ T6: Notification preferences filter correctly
✅ T7: Browser notifications work (Chrome, Firefox, Safari)
```

---

## Phase 8: Deployment Plan

### Infrastructure Setup

```yaml
# docker-compose.yml
services:
  backend:
    image: notification-backend:latest
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://db:5432/app
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=app

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
```

### Monitoring Checklist

```
✅ WebSocket connection count (Prometheus metric)
✅ Notification delivery latency (p50, p95, p99)
✅ Redis pub/sub message rate
✅ Database query performance (pg_stat_statements)
✅ Error rate (Sentry)
✅ Uptime monitoring (UptimeRobot)
```

---

## Phase 9: Success Metrics

### KPIs (Key Performance Indicators)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Delivery latency (p95)** | <500ms | Prometheus |
| **Notification open rate** | >40% | Analytics |
| **System uptime** | 99.9% | Monitoring |
| **User engagement increase** | +15% DAU | Analytics |
| **Support tickets (notification issues)** | <5/month | Ticket system |

---

## Phase 10: Future Enhancements (Post-MVP)

| Feature | Priority | Effort | Value |
|---------|----------|--------|-------|
| **Push notifications (mobile)** | High | 2 weeks | High |
| **Notification grouping** | Medium | 1 week | Medium |
| **Rich notifications (images, actions)** | Medium | 1 week | Medium |
| **Email fallback** | Low | 3 days | Low |
| **Advanced filtering/search** | Low | 1 week | Low |

---

## Implementation Checklist

### Week 1 (Backend Core)
- [ ] Database schema created and migrated
- [ ] REST API endpoints implemented and tested
- [ ] WebSocket server running with authentication
- [ ] Notification service creates and sends notifications
- [ ] Redis pub/sub working
- [ ] Unit tests pass (80%+ coverage)

### Week 2 (Frontend Integration)
- [ ] WebSocket client connects and authenticates
- [ ] Notification UI component displays notifications
- [ ] Mark as read functionality works
- [ ] Real-time updates appear instantly
- [ ] Reconnection fetches missed notifications
- [ ] Preferences UI functional
- [ ] Frontend tests pass

### Week 3 (Polish & Deploy)
- [ ] Browser notifications work (with permission)
- [ ] Sound alerts functional
- [ ] E2E tests pass (5 critical paths)
- [ ] Load test passes (10k concurrent users)
- [ ] Performance optimized (caching, indexing)
- [ ] Documentation complete
- [ ] Deployed to staging
- [ ] Deployed to production
- [ ] Monitoring active

---

## Key Takeaways

1. **Architecture first** — design before coding
2. **Incremental delivery** — 3 sprints with clear milestones
3. **Risk mitigation** — identify and plan for risks early
4. **Test coverage** — define targets and critical scenarios
5. **Monitoring** — plan observability from day 1
6. **Stakeholder alignment** — share plan for feedback before starting

---

## Estimated Timeline

```
Week 1: Backend Core        ██████████████░░░░░░░░░░░░ 60%
Week 2: Frontend Integration ░░░░░░░░░░░░░░██████████░░ 60%
Week 3: Polish & Deploy     ░░░░░░░░░░░░░░░░░░░░░░████ 100%

Total: 3 weeks (15 working days)
```

**Confidence:** 75% (medium-high) — known technologies, clear requirements

---

**Next Steps:**
1. Review plan with team and stakeholders
2. Create GitHub issues for each task
3. Set up project board (Kanban)
4. Begin Sprint 1 (Backend Core)
