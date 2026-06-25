# Few-Shot Example: Technical Documentation

**Domain:** General | **Task Type:** Documentation Writing | **Complexity:** Medium

---

## User Request

```
Write documentation for this authentication middleware:

def auth_required(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not verify_token(token):
            return {"error": "Unauthorized"}, 401
        return f(*args, **kwargs)
    return decorated_function
```

## Claude Response

### Documentation: `auth_required` Decorator

Comprehensive documentation for API authentication middleware.

---

## Overview

```python
@auth_required
def protected_route():
    return {"data": "sensitive"}
```

The `auth_required` decorator enforces Bearer token authentication for Flask routes. Requests without valid tokens receive 401 Unauthorized responses.

---

## API Reference

### `auth_required(f)`

Decorator that protects routes by requiring valid authentication tokens.

**Parameters:**
- `f` (callable): The Flask route function to protect

**Returns:**
- `callable`: Wrapped function with authentication check

**Raises:**
- Returns `401 Unauthorized` response if:
  - `Authorization` header is missing
  - Token verification fails via `verify_token()`

**Example Usage:**

```python
from flask import Flask, request
from auth import auth_required

app = Flask(__name__)

@app.route('/api/user/profile')
@auth_required
def get_profile():
    """Protected endpoint requiring authentication."""
    user_id = get_user_id_from_token(request.headers['Authorization'])
    return {"user_id": user_id, "name": "Alice"}
```

---

## Request Format

### Headers Required

```http
GET /api/user/profile HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Authorization Header Format:**
- **Scheme:** `Bearer`
- **Token:** JWT (JSON Web Token) issued by `/auth/login`

---

## Response Codes

| Code | Condition | Response Body | Action Required |
|------|-----------|---------------|-----------------|
| **200 OK** | Valid token | Protected resource data | None |
| **401 Unauthorized** | Missing token | `{"error": "Unauthorized"}` | Obtain token via `/auth/login` |
| **401 Unauthorized** | Invalid/expired token | `{"error": "Unauthorized"}` | Refresh token or re-authenticate |

---

## Implementation Details

### Authentication Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Request with token
       ▼
┌────────────────────────────────────┐
│  @auth_required decorator          │
│  ├─► Extract Authorization header  │
│  ├─► Check header exists           │
│  ├─► Verify token signature        │
│  │   (calls verify_token)          │
│  └─► Decision:                     │
│      ├─ Valid   → call f()         │
│      └─ Invalid → 401 response     │
└────────────────────────────────────┘
```

### Token Verification

The decorator delegates verification to `verify_token()`:

```python
def verify_token(token: str) -> bool:
    """
    Verify JWT token signature and expiration.

    Args:
        token: JWT string (with or without "Bearer " prefix)

    Returns:
        True if token is valid and not expired, False otherwise.
    """
    # Implementation checks:
    # 1. Token format (JWT structure)
    # 2. Signature (using secret key)
    # 3. Expiration time
    # 4. Issuer (optional)
```

---

## Security Considerations

### 🔒 Best Practices

1. **HTTPS Required**
   - **Why:** Tokens in headers are transmitted in plaintext
   - **Enforcement:** Configure reverse proxy (nginx/Apache) to reject HTTP

2. **Token Expiration**
   - **Recommended TTL:** 15-60 minutes for access tokens
   - **Refresh mechanism:** Issue refresh tokens (longer TTL, stored securely)

3. **Secret Key Management**
   - **Never hardcode** JWT secret in source code
   - **Use environment variables** or secret managers (Vault, AWS Secrets Manager)

4. **Rate Limiting**
   - Apply rate limiting to authentication endpoints
   - **Tool:** Flask-Limiter

   ```python
   from flask_limiter import Limiter

   limiter = Limiter(app, default_limits=["100 per hour"])

   @app.route('/auth/login')
   @limiter.limit("10 per minute")
   def login():
       ...
   ```

---

## Testing Guide

### Unit Tests

```python
import pytest
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_auth_required_valid_token(client, mocker):
    """Test decorator allows access with valid token."""
    mocker.patch('app.verify_token', return_value=True)

    response = client.get(
        '/api/user/profile',
        headers={'Authorization': 'Bearer valid_token'}
    )
    assert response.status_code == 200

def test_auth_required_missing_token(client):
    """Test decorator blocks access without token."""
    response = client.get('/api/user/profile')
    assert response.status_code == 401
    assert response.json['error'] == 'Unauthorized'

def test_auth_required_invalid_token(client, mocker):
    """Test decorator blocks access with invalid token."""
    mocker.patch('app.verify_token', return_value=False)

    response = client.get(
        '/api/user/profile',
        headers={'Authorization': 'Bearer invalid_token'}
    )
    assert response.status_code == 401
```

### Integration Tests

```python
def test_end_to_end_authentication(client):
    """Test full authentication flow."""
    # 1. Login to get token
    login_response = client.post('/auth/login', json={
        "username": "alice",
        "password": "secure_password"
    })
    assert login_response.status_code == 200
    token = login_response.json['token']

    # 2. Access protected resource with token
    protected_response = client.get(
        '/api/user/profile',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert protected_response.status_code == 200
    assert 'user_id' in protected_response.json
```

---

## Troubleshooting

### Common Issues

| Problem | Symptoms | Solution |
|---------|----------|----------|
| **"Unauthorized" despite valid token** | 401 response | Check token format (must include "Bearer " prefix) |
| **Token expires too quickly** | Frequent re-authentication | Increase TTL in token generation |
| **verify_token() always returns False** | All requests rejected | Verify secret key matches between generation and verification |
| **CORS errors in browser** | Preflight requests fail | Add CORS headers to 401 responses |

### Debug Mode

Enable detailed logging for authentication issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def auth_required(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        logger.debug(f"Auth attempt - Token present: {bool(token)}")

        if not token:
            logger.warning("Missing Authorization header")
            return {"error": "Unauthorized"}, 401

        is_valid = verify_token(token)
        logger.debug(f"Token validation result: {is_valid}")

        if not is_valid:
            logger.warning(f"Invalid token: {token[:20]}...")
            return {"error": "Unauthorized"}, 401

        return f(*args, **kwargs)
    return decorated_function
```

---

## Migration Guide

### Upgrading from Basic Auth

**Before:**
```python
@app.route('/api/user/profile')
@auth.login_required  # Flask-HTTPAuth
def get_profile():
    return {"data": "..."}
```

**After:**
```python
@app.route('/api/user/profile')
@auth_required  # JWT-based
def get_profile():
    return {"data": "..."}
```

**Changes required:**
1. Update client to send `Authorization: Bearer <token>` instead of Basic Auth
2. Implement `/auth/login` endpoint to issue JWT tokens
3. Store tokens in client (localStorage or secure cookie)

---

## Related Documentation

- [JWT Specification (RFC 7519)](https://tools.ietf.org/html/rfc7519)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-27 | Initial documentation |

---

## Support

For issues or questions:
- **GitHub Issues:** https://github.com/yourorg/project/issues
- **Slack:** #api-support channel
- **Email:** api-support@example.com
