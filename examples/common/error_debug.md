# Few-Shot Example: Error Debugging

**Domain:** General | **Task Type:** Debugging | **Complexity:** Medium

---

## User Request

```
I'm getting this error when running my Flask app:

TypeError: 'NoneType' object is not subscriptable
  File "/app/routes.py", line 45, in get_user
    return user['name']
```

## Claude Response

### Debugging Analysis: TypeError in Flask Route

Let me systematically debug this error using a **structured approach**.

---

#### **Step 1: Error Interpretation**

```
TypeError: 'NoneType' object is not subscriptable
```

**Translation:**
- **NoneType:** Variable is `None` (not a dict, list, or other subscriptable type)
- **Not subscriptable:** Attempted `user['name']` but `user` is `None`
- **Root cause:** `user` variable is `None` when code expects a dictionary

---

#### **Step 2: Reproduce the Issue**

**Minimal Reproduction:**

```python
user = None  # This is what's happening
print(user['name'])  # TypeError: 'NoneType' object is not subscriptable
```

---

#### **Step 3: Identify the Failure Point**

```python
# File: /app/routes.py, line 45
def get_user():
    user = User.query.filter_by(id=request.args.get('user_id')).first()
    return user['name']  # ← CRASH HERE if .first() returns None
```

**Why `.first()` returns None:**
- No matching user in database
- `user_id` not provided in request
- `user_id` is invalid format

---

#### **Step 4: Add Diagnostic Logging**

```python
import logging

@app.route('/user')
def get_user():
    user_id = request.args.get('user_id')
    logging.debug(f"Received user_id: {user_id}")  # Log input

    user = User.query.filter_by(id=user_id).first()
    logging.debug(f"Query result: {user}")  # Log query result

    if user is None:
        logging.warning(f"User not found: user_id={user_id}")
        return {"error": "User not found"}, 404

    return {"name": user.name}, 200
```

---

#### **Step 5: Root Cause Analysis**

**Hypothesis Matrix:**

| Hypothesis | Check | Likely? |
|------------|-------|---------|
| **User ID not in database** | Query returns no results | ⭐ **HIGH** |
| **user_id parameter missing** | `request.args.get('user_id')` is None | ⭐ **HIGH** |
| **Type mismatch** | user_id is string, DB expects int | 🟡 Medium |
| **Database connection issue** | Query execution fails silently | 🟢 Low |

**Most Likely:** User ID not found OR parameter missing.

---

#### **Step 6: Defensive Fix**

```python
from flask import request, jsonify

@app.route('/user')
def get_user():
    # Guard 1: Validate parameter presence
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Missing user_id parameter"}), 400

    # Guard 2: Validate parameter format
    try:
        user_id = int(user_id)  # Assuming ID is integer
    except ValueError:
        return jsonify({"error": "Invalid user_id format"}), 400

    # Guard 3: Handle query returning None
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Safe access: user is guaranteed to exist here
    return jsonify({
        "name": user.name,
        "id": user.id,
        "email": user.email
    }), 200
```

---

#### **Step 7: Testing Strategy**

```python
import pytest
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_get_user_success(client, mocker):
    """Test successful user retrieval."""
    # Mock database query
    mock_user = mocker.Mock(name="Alice", id=123, email="alice@example.com")
    mocker.patch('app.routes.User.query.filter_by().first', return_value=mock_user)

    response = client.get('/user?user_id=123')
    assert response.status_code == 200
    assert response.json['name'] == 'Alice'

def test_get_user_not_found(client, mocker):
    """Test user not found scenario (original bug)."""
    mocker.patch('app.routes.User.query.filter_by().first', return_value=None)

    response = client.get('/user?user_id=999')
    assert response.status_code == 404
    assert 'User not found' in response.json['error']

def test_get_user_missing_parameter(client):
    """Test missing user_id parameter."""
    response = client.get('/user')  # No user_id
    assert response.status_code == 400
    assert 'Missing user_id' in response.json['error']

def test_get_user_invalid_format(client):
    """Test invalid user_id format."""
    response = client.get('/user?user_id=abc')
    assert response.status_code == 400
    assert 'Invalid user_id format' in response.json['error']
```

---

#### **Step 8: Prevention Strategies**

**1. Use Optional Type Hints**

```python
from typing import Optional

def get_user_by_id(user_id: int) -> Optional[User]:
    """Returns User or None if not found."""
    return User.query.filter_by(id=user_id).first()
```

**2. Monadic Error Handling (Advanced)**

```python
from typing import Union

def get_user() -> Union[dict, tuple]:
    user_id = request.args.get('user_id')

    return (
        validate_user_id(user_id)  # Returns error or user_id
        .then(lambda id: query_user(id))  # Returns error or user
        .then(lambda user: serialize_user(user))  # Returns JSON
        .unwrap_or(default={"error": "Something went wrong"}, status=500)
    )
```

**3. Enable Linter Rules**

```yaml
# .pylintrc
[MESSAGES CONTROL]
enable=
    no-member,
    unsubscriptable-object  # Catches potential None access
```

---

## Debugging Checklist

✅ **Reproduce** error in isolation
✅ **Log** inputs and intermediary values
✅ **Identify** exact line where error occurs
✅ **Hypothesize** root causes (multiple)
✅ **Test** each hypothesis systematically
✅ **Fix** defensively (validate all inputs)
✅ **Test** fix with unit tests (happy + edge cases)
✅ **Prevent** recurrence (linters, type hints, code review)

---

## Key Takeaways

1. **Never assume variables exist** — always validate
2. **Guard at boundaries** — validate inputs at function entry
3. **Log liberally** during debugging (remove after fix)
4. **Test edge cases** — None, empty, invalid types
5. **Use type hints** — `Optional[Type]` signals potential None

---

**Next Steps:**
- Apply defensive fix to routes.py
- Add unit tests (pytest + mocker)
- Enable pylint rule for unsubscriptable-object
- Review other routes for similar patterns
