# Few-Shot Example: Bug Fix Implementation Workflow

## Task
Пользователь: "В API-эндпоинте `/api/users/{id}` при передаче несуществующего ID возвращается 500 вместо 404."

## Solution

**Reference:** `~/.claude/modules/14-implementation-workflow.md` (Bug Fix Workflow)

---

## Phase 1: Reproduce & Understand

### 1.1 Reproduce the Bug
```bash
# Confirm the issue
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/users/99999
# Expected: 404, Actual: 500
```

### 1.2 Read Error Logs
```
ERROR 2026-02-06 10:15:23 - KeyError: 99999
Traceback: app/routes/users.py:45 get_user()
```

### 1.3 Root Cause Analysis
```
Root Cause: `get_user()` calls `db.users[user_id]` which raises KeyError
for missing keys. No try/except or `.get()` used.
```

## Phase 2: Write Test First (TDD)

### 2.1 Create Failing Test
```python
# tests/test_users.py
def test_get_nonexistent_user_returns_404(client):
    """Bug fix: GET /api/users/{id} should return 404 for missing users."""
    response = client.get("/api/users/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
```

### 2.2 Verify Test Fails
```bash
pytest tests/test_users.py::test_get_nonexistent_user_returns_404 -v
# FAILED — confirms bug exists
```

## Phase 3: Implement Fix

### 3.1 Minimal Fix
```python
# app/routes/users.py
from fastapi import HTTPException

@router.get("/api/users/{user_id}")
async def get_user(user_id: int):
    user = db.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Phase 4: Verify Fix

### 4.1 Run Test
```bash
pytest tests/test_users.py::test_get_nonexistent_user_returns_404 -v
# PASSED
```

### 4.2 Run Full Suite
```bash
pytest tests/ -q
# All tests pass, no regressions
```

## Phase 5: Commit

```bash
git add app/routes/users.py tests/test_users.py
git commit -m "fix: return 404 for nonexistent user instead of 500"
```

---

## Verification

- Bug reproduced before fix
- Test written BEFORE fix (TDD)
- Minimal change — only the affected line
- Full test suite passes (no regressions)
- Commit message describes the fix clearly
