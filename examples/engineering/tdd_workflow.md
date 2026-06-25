# Example: Test-Driven Development Workflow

## User Request

```
Покажи TDD workflow: напиши функцию для валидации email с тестами, начиная с тестов.
```

## Reasoning

**Domain:** Engineering (TDD best practices)
**Complexity:** Simple
**Model:** Haiku

## Response

### Step 1: Write Failing Tests First

```python
# test_validators.py
import pytest
from validators import validate_email

def test_valid_email():
    """Test valid email addresses."""
    assert validate_email("user@example.com") == True
    assert validate_email("first.last@company.co.uk") == True
    assert validate_email("test+tag@domain.org") == True

def test_invalid_email_missing_at():
    """Test email without @ symbol."""
    assert validate_email("userexample.com") == False

def test_invalid_email_missing_domain():
    """Test email without domain."""
    assert validate_email("user@") == False

def test_invalid_email_missing_username():
    """Test email without username."""
    assert validate_email("@example.com") == False

def test_invalid_email_multiple_at():
    """Test email with multiple @ symbols."""
    assert validate_email("user@@example.com") == False

def test_invalid_email_empty():
    """Test empty email."""
    assert validate_email("") == False

def test_invalid_email_none():
    """Test None input."""
    assert validate_email(None) == False

def test_invalid_email_spaces():
    """Test email with spaces."""
    assert validate_email("user @example.com") == False

# Run tests (should fail - function doesn't exist yet)
# pytest test_validators.py -v
```

### Step 2: Write Minimal Implementation

```python
# validators.py (first attempt)
def validate_email(email):
    """Validate email address format."""
    if not email:
        return False

    if '@' not in email:
        return False

    return True

# Run tests again - some pass, some fail
```

### Step 3: Iterate Until All Tests Pass

```python
# validators.py (final implementation)
import re
from typing import Optional

def validate_email(email: Optional[str]) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address string to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid")
        False
    """
    if not email or not isinstance(email, str):
        return False

    # Basic email regex (RFC 5322 simplified)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    return bool(re.match(pattern, email))

# Run tests - all should pass now ✅
# pytest test_validators.py -v --cov=validators
```

### Step 4: Refactor with Confidence

```python
# validators.py (refactored with email-validator library)
from email_validator import validate_email as ev_validate, EmailNotValidError

def validate_email(email: Optional[str]) -> bool:
    """
    Validate email address using email-validator library.

    More robust validation including DNS checks (optional).
    """
    if not email:
        return False

    try:
        # Validate and normalize email
        valid = ev_validate(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

# Tests still pass - refactoring successful ✅
```

---

## TDD Workflow Summary

```
1. 🔴 RED — Write failing test
   ├─► Test describes expected behavior
   ├─► Run test → should FAIL (no implementation yet)
   └─► Verify test failure message is correct

2. 🟢 GREEN — Write minimal code to pass
   ├─► Write simplest implementation
   ├─► Run tests → should PASS
   └─► Don't optimize yet (just make it work)

3. 🔵 REFACTOR — Improve code quality
   ├─► Clean up implementation
   ├─► Remove duplication
   ├─► Run tests → should still PASS
   └─► Commit only when green

4. 🔁 REPEAT for next feature
```

## Key Takeaways

1. **Tests first** — define behavior before implementation
2. **Minimal implementation** — just enough to pass tests
3. **Refactor safely** — tests protect against regressions
4. **Fast feedback** — run tests continuously
5. **100% coverage** — every line has a test

**Benefits:** Fewer bugs, better design, living documentation
**Tools:** pytest, coverage.py, pytest-watch (auto-run)
