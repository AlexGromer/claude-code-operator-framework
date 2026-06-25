# Example: JWT Security Audit & Hardening

## User Request

```
Проверь безопасность нашей JWT-аутентификации:

import jwt
import datetime

SECRET_KEY = "my_secret_123"

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256', 'RS256', 'none'])
        return payload['user_id']
    except:
        return None
```

## Reasoning

**Domain:** Security (JWT implementation audit)
**Complexity:** Medium (authentication security + cryptography)
**Model:** Sonnet (security-critical review)

**Audit focus:**
1. Secret key strength and storage
2. Algorithm selection and validation
3. Token expiration and refresh strategy
4. Payload security (PII, privilege escalation)
5. Exception handling and error disclosure

## Response

### 🔴 Critical Vulnerabilities

#### 1. **Weak Secret Key** (CRITICAL)
**Issue:** Hardcoded, predictable secret `"my_secret_123"`
**Risk:** Token forgery via brute-force attack

**Attack:**
```python
# Attacker can brute-force weak secret in minutes
import jwt
import itertools

def crack_jwt_secret(token):
    wordlist = ["secret", "password", "my_secret_123", "admin", ...]
    for secret in wordlist:
        try:
            jwt.decode(token, secret, algorithms=['HS256'])
            return secret  # Found!
        except:
            continue
```

---

#### 2. **Algorithm Confusion Attack** (CRITICAL)
**Issue:** Accepts multiple algorithms including `'none'`
**Risk:** Bypass authentication entirely

**Attack:**
```python
# Attacker modifies token to use 'none' algorithm
import jwt
import base64
import json

# Original token header: {"alg": "HS256", "typ": "JWT"}
# Attacker changes to: {"alg": "none", "typ": "JWT"}

header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip('=')
payload = base64.urlsafe_b64encode(b'{"user_id":"admin"}').decode().rstrip('=')
fake_token = f"{header}.{payload}."

# verify_token() accepts this because 'none' is in allowed algorithms!
user_id = verify_token(fake_token)  # Returns 'admin' without signature check
```

---

#### 3. **Excessive Token Lifetime** (HIGH)
**Issue:** 30-day expiration with no refresh mechanism
**Risk:** Stolen token remains valid for 30 days

---

#### 4. **Silent Exception Handling** (MEDIUM)
**Issue:** Generic `except:` returns `None` without logging
**Risk:** Hides attack attempts, no audit trail

---

### ✅ Secure Implementation

```python
import jwt
import datetime
import secrets
import os
import logging
from typing import Optional, Dict
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

# Security configuration
class JWTConfig:
    """Centralized JWT security configuration."""

    # CRITICAL: Use cryptographically secure secret from environment
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not SECRET_KEY or len(SECRET_KEY) < 32:
        raise ValueError("JWT_SECRET_KEY must be set and >= 32 bytes")

    ALGORITHM = 'HS256'  # Only one algorithm - prevent confusion attacks
    ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS = 7  # Longer-lived refresh token
    ISSUER = 'myapp.example.com'
    AUDIENCE = 'myapp-api'


def generate_access_token(user_id: str, role: str = 'user') -> str:
    """
    Generate short-lived access token.

    Security features:
    - Strong secret from environment
    - Short expiration (15 min)
    - Issuer/Audience validation
    - Role-based access control
    - JTI (unique token ID) for revocation
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    jti = secrets.token_urlsafe(16)  # Unique token ID

    payload = {
        'user_id': user_id,
        'role': role,
        'iat': now,  # Issued At
        'exp': now + datetime.timedelta(minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES),
        'nbf': now,  # Not Before
        'iss': JWTConfig.ISSUER,
        'aud': JWTConfig.AUDIENCE,
        'jti': jti,
        'type': 'access'
    }

    token = jwt.encode(
        payload,
        JWTConfig.SECRET_KEY,
        algorithm=JWTConfig.ALGORITHM
    )

    logger.info(f"Generated access token for user={user_id}, jti={jti}")
    return token


def generate_refresh_token(user_id: str) -> str:
    """Generate refresh token for obtaining new access tokens."""
    now = datetime.datetime.now(datetime.timezone.utc)
    jti = secrets.token_urlsafe(16)

    payload = {
        'user_id': user_id,
        'iat': now,
        'exp': now + datetime.timedelta(days=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS),
        'iss': JWTConfig.ISSUER,
        'aud': JWTConfig.AUDIENCE,
        'jti': jti,
        'type': 'refresh'
    }

    token = jwt.encode(
        payload,
        JWTConfig.SECRET_KEY,
        algorithm=JWTConfig.ALGORITHM
    )

    logger.info(f"Generated refresh token for user={user_id}, jti={jti}")
    return token


def verify_token(token: str, expected_type: str = 'access') -> Optional[Dict]:
    """
    Verify and decode JWT token with comprehensive validation.

    Security features:
    - Explicit algorithm whitelist (single algorithm only)
    - Issuer/Audience validation
    - Expiration enforcement
    - Type checking (access vs refresh)
    - Detailed error logging
    - No information leakage on failure

    Returns:
        Payload dict if valid, None if invalid
    """
    try:
        # CRITICAL: Explicitly specify allowed algorithms (only one!)
        payload = jwt.decode(
            token,
            JWTConfig.SECRET_KEY,
            algorithms=[JWTConfig.ALGORITHM],  # Only HS256, no 'none' or RS256
            issuer=JWTConfig.ISSUER,
            audience=JWTConfig.AUDIENCE,
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_nbf': True,
                'verify_iat': True,
                'verify_aud': True,
                'verify_iss': True,
                'require_exp': True,
                'require_iat': True,
                'require_nbf': True
            }
        )

        # Verify token type
        if payload.get('type') != expected_type:
            logger.warning(f"Token type mismatch: expected={expected_type}, got={payload.get('type')}")
            return None

        logger.info(f"Token verified: user={payload['user_id']}, jti={payload.get('jti')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidAudienceError:
        logger.warning("Invalid audience")
        return None
    except jwt.InvalidIssuerError:
        logger.warning("Invalid issuer")
        return None
    except jwt.InvalidSignatureError:
        logger.warning("Invalid signature - potential forgery attempt")
        return None
    except jwt.DecodeError:
        logger.warning("Token decode error - malformed token")
        return None
    except Exception as e:
        logger.error(f"Unexpected token verification error: {type(e).__name__}")
        return None


def require_auth(role: str = None):
    """
    Decorator for protecting routes with JWT authentication.

    Usage:
        @require_auth()
        def protected_route():
            ...

        @require_auth(role='admin')
        def admin_route():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract token from Authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return {'error': 'Missing or invalid Authorization header'}, 401

            token = auth_header[7:]  # Remove 'Bearer ' prefix
            payload = verify_token(token, expected_type='access')

            if not payload:
                return {'error': 'Invalid or expired token'}, 401

            # Check role if required
            if role and payload.get('role') != role:
                logger.warning(f"Insufficient privileges: user={payload['user_id']}, required={role}")
                return {'error': 'Insufficient privileges'}, 403

            # Attach user info to request context
            request.user_id = payload['user_id']
            request.user_role = payload.get('role')

            return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

### 🛡️ Security Controls Comparison

| Control | Vulnerable | Secure |
|---------|-----------|--------|
| **Secret Key** | ❌ Hardcoded `"my_secret_123"` | ✅ Environment var, ≥32 bytes |
| **Algorithms** | ❌ Multiple (`HS256`, `RS256`, `none`) | ✅ Single (`HS256` only) |
| **Expiration** | ❌ 30 days | ✅ 15 min (access) + 7 days (refresh) |
| **Validation** | ❌ None (no iss/aud) | ✅ Full (iss, aud, exp, nbf, iat) |
| **Error Handling** | ❌ Silent (`except: return None`) | ✅ Specific exceptions + logging |
| **Token Type** | ❌ No distinction | ✅ Access vs Refresh separation |
| **Revocation** | ❌ Impossible | ✅ JTI tracking (can blacklist) |
| **Logging** | ❌ None | ✅ All events logged |

---

### 📋 Deployment Checklist

```bash
# 1. Generate strong secret (64 bytes)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 2. Set environment variable (NEVER commit to git!)
export JWT_SECRET_KEY="<generated_secret>"

# 3. Add to .env (for local development)
echo "JWT_SECRET_KEY=<generated_secret>" >> .env

# 4. Add .env to .gitignore
echo ".env" >> .gitignore

# 5. Configure production secret (e.g., Kubernetes secret)
kubectl create secret generic jwt-secret \
  --from-literal=JWT_SECRET_KEY=<generated_secret>

# 6. Rotate secret quarterly
# - Generate new secret
# - Deploy new secret
# - Invalidate old tokens (force re-login)
```

---

## Key Takeaways

1. **Never hardcode secrets** — use environment variables + secret management
2. **Algorithm confusion is real** — whitelist ONE algorithm only
3. **Short-lived tokens** — 15-min access token + refresh token pattern
4. **Validate everything** — issuer, audience, expiration, signature
5. **Log security events** — detect and respond to attacks
6. **Token revocation** — use JTI for blacklisting compromised tokens
7. **Rotate secrets** — quarterly rotation as best practice

**OWASP Reference:** A02:2021 – Cryptographic Failures, A07:2021 – Identification and Authentication Failures
**JWT Best Practices:** RFC 8725
