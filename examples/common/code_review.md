# Few-Shot Example: Code Review

**Domain:** General | **Task Type:** Code Review | **Complexity:** Medium

---

## User Request

```
Review this Python function for potential issues:

def process_users(users):
    results = []
    for user in users:
        if user['age'] > 18:
            results.append(user['name'].upper())
    return results
```

## Claude Response

### Code Review: `process_users` Function

I'll review this function for **correctness, safety, and best practices**.

---

#### **Issues Identified**

| Priority | Issue | Location | Impact |
|----------|-------|----------|--------|
| 🔴 **P1 - Critical** | **KeyError risk** | `user['age']`, `user['name']` | Runtime crash if keys missing |
| 🟡 **P2 - Medium** | **No input validation** | Function signature | Unexpected behavior with None/non-iterable |
| 🟢 **P3 - Minor** | **Type hints missing** | Function signature | Reduced IDE support, unclear contract |
| 🟢 **P3 - Minor** | **No docstring** | Function | Poor maintainability |

---

#### **Detailed Analysis**

**1. KeyError Risk (CRITICAL)**

```python
# Current code (unsafe):
if user['age'] > 18:
    results.append(user['name'].upper())

# Problem: If 'age' or 'name' keys are missing → KeyError
```

**Recommendation:** Use `.get()` with defaults or validate input schema.

**2. No Input Validation**

```python
# Current code:
def process_users(users):  # What if users is None? Empty string?
    for user in users:     # TypeError if users is not iterable
```

**Recommendation:** Add guard clause or type annotation enforcement.

---

#### **Refactored Version (Defensive)**

```python
from typing import List, Dict, Any, Optional

def process_users(
    users: Optional[List[Dict[str, Any]]]
) -> List[str]:
    """
    Extract names of adult users (age > 18) in uppercase.

    Args:
        users: List of user dictionaries with 'name' and 'age' keys.
               Can be None (returns empty list).

    Returns:
        List of uppercase names for users aged > 18.

    Examples:
        >>> process_users([{'name': 'Alice', 'age': 25}])
        ['ALICE']
        >>> process_users([{'name': 'Bob', 'age': 15}])
        []
        >>> process_users(None)
        []
    """
    if users is None:
        return []

    results = []
    for user in users:
        # Defensive: use .get() with defaults
        age = user.get('age', 0)
        name = user.get('name', '')

        if age > 18 and name:  # Also check name is not empty
            results.append(name.upper())

    return results
```

---

#### **Alternative: Fail-Fast Version (With Validation)**

```python
from typing import List, Dict
from pydantic import BaseModel, ValidationError

class User(BaseModel):
    name: str
    age: int

def process_users_strict(users_data: List[Dict]) -> List[str]:
    """
    Extract names of adult users with strict validation.

    Raises:
        ValidationError: If any user dict doesn't match User schema.
    """
    users = [User(**data) for data in users_data]  # Validates schema
    return [user.name.upper() for user in users if user.age > 18]
```

**Trade-off:**
- **Defensive version:** Tolerant (skips bad data)
- **Fail-fast version:** Strict (raises errors immediately)

**Recommendation:** Use **fail-fast for APIs** (data contract), **defensive for internal tools** (graceful degradation).

---

#### **Testing Recommendation**

```python
import pytest

def test_process_users_happy_path():
    users = [{'name': 'Alice', 'age': 25}, {'name': 'Bob', 'age': 17}]
    assert process_users(users) == ['ALICE']

def test_process_users_missing_keys():
    users = [{'age': 25}, {'name': 'Charlie'}]
    assert process_users(users) == []  # Defensive: skip invalid entries

def test_process_users_none_input():
    assert process_users(None) == []

def test_process_users_empty_list():
    assert process_users([]) == []
```

**Coverage target:** ≥90% (critical paths + edge cases)

---

## Key Takeaways

1. **Always use `.get()` for dictionary access** when key presence is uncertain
2. **Add type hints** for better IDE support and runtime validation
3. **Validate inputs** at function boundaries (None, empty, wrong types)
4. **Document with docstrings** (especially non-obvious behavior)
5. **Choose defensive vs fail-fast** based on context (internal vs API)

---

**Next Steps:**
- Apply refactored version
- Add unit tests (pytest)
- Consider using Pydantic for data validation if this is part of an API
