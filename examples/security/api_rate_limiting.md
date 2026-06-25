# Example: API Rate Limiting & DoS Prevention

## User Request

```
Защити API от DDoS/брутфорса. Нужен rate limiting для:
- Общих API запросов: 100 req/min per IP
- Login endpoint: 5 attempts/min per IP
- Password reset: 3 req/hour per email
```

## Reasoning

**Domain:** Security (DoS prevention + rate limiting)
**Complexity:** Medium (distributed systems + Redis)
**Model:** Sonnet

## Response

### Implementation with Redis Token Bucket

```python
import redis
import time
import hashlib
from typing import Optional, Tuple
from functools import wraps
from flask import request, jsonify

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    @staticmethod
    def check_rate_limit(
        key: str,
        max_requests: int,
        window_seconds: int,
        cost: int = 1
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Args:
            key: Unique identifier (e.g., IP, user_id, email)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            cost: Token cost for this request (default 1)

        Returns:
            (allowed: bool, metadata: dict)
        """
        now = time.time()
        window_key = f"ratelimit:{key}:{int(now // window_seconds)}"

        pipe = redis_client.pipeline()
        pipe.incr(window_key, cost)
        pipe.expire(window_key, window_seconds * 2)  # Cleanup old keys
        results = pipe.execute()

        current_requests = results[0]
        allowed = current_requests <= max_requests

        metadata = {
            'limit': max_requests,
            'remaining': max(0, max_requests - current_requests),
            'reset_at': int((int(now // window_seconds) + 1) * window_seconds)
        }

        return allowed, metadata

    @staticmethod
    def sliding_window_check(
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, dict]:
        """
        Sliding window rate limiter (more accurate, higher overhead).

        Uses sorted set to track individual request timestamps.
        """
        now = time.time()
        window_start = now - window_seconds
        requests_key = f"ratelimit:sliding:{key}"

        pipe = redis_client.pipeline()
        # Remove old entries
        pipe.zremrangebyscore(requests_key, 0, window_start)
        # Count current requests
        pipe.zcard(requests_key)
        # Add current request
        pipe.zadd(requests_key, {str(now): now})
        # Set expiration
        pipe.expire(requests_key, window_seconds * 2)
        results = pipe.execute()

        current_requests = results[1]
        allowed = current_requests < max_requests

        metadata = {
            'limit': max_requests,
            'remaining': max(0, max_requests - current_requests - 1),
            'reset_at': int(now + window_seconds)
        }

        return allowed, metadata


def rate_limit(max_requests: int, window_seconds: int, key_func=None):
    """
    Decorator for rate limiting Flask routes.

    Args:
        max_requests: Maximum requests in window
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key (default: IP address)

    Example:
        @rate_limit(max_requests=100, window_seconds=60)
        def api_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr or 'unknown'

            # Check rate limit
            allowed, metadata = RateLimiter.check_rate_limit(
                key, max_requests, window_seconds
            )

            # Add rate limit headers
            response_headers = {
                'X-RateLimit-Limit': str(metadata['limit']),
                'X-RateLimit-Remaining': str(metadata['remaining']),
                'X-RateLimit-Reset': str(metadata['reset_at'])
            }

            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': metadata['reset_at'] - int(time.time())
                }), 429, response_headers

            # Execute route
            response = func(*args, **kwargs)

            # Add headers to successful response
            if isinstance(response, tuple):
                data, status = response[0], response[1]
                return data, status, response_headers
            else:
                return response, 200, response_headers

        return wrapper
    return decorator


# Example usage
@app.route('/api/data')
@rate_limit(max_requests=100, window_seconds=60)  # 100 req/min per IP
def get_data():
    return jsonify({'data': 'example'})


@app.route('/auth/login', methods=['POST'])
@rate_limit(
    max_requests=5,
    window_seconds=60,
    key_func=lambda: request.remote_addr  # Per IP
)
def login():
    # Additional per-email rate limit
    email = request.json.get('email')
    if email:
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        allowed, _ = RateLimiter.check_rate_limit(
            f"email:{email_hash}",
            max_requests=5,
            window_seconds=300  # 5 attempts per 5 min per email
        )
        if not allowed:
            return jsonify({'error': 'Too many login attempts for this email'}), 429

    # Process login
    ...
    return jsonify({'token': 'xyz'})


@app.route('/auth/reset-password', methods=['POST'])
@rate_limit(
    max_requests=3,
    window_seconds=3600,  # 3 req/hour
    key_func=lambda: hashlib.sha256(
        request.json.get('email', '').encode()
    ).hexdigest()
)
def reset_password():
    # Process password reset
    ...
    return jsonify({'message': 'Reset email sent'})
```

---

### Advanced: Distributed Rate Limiting

```python
class DistributedRateLimiter:
    """
    Rate limiter for multi-instance deployments with Redis Lua scripts.
    Atomic operations prevent race conditions.
    """

    # Lua script for atomic token bucket check
    TOKEN_BUCKET_SCRIPT = """
    local key = KEYS[1]
    local max_requests = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])

    local current = redis.call('GET', key)
    if not current then
        current = 0
    end

    current = tonumber(current)

    if current < max_requests then
        redis.call('INCR', key)
        redis.call('EXPIRE', key, window * 2)
        return {1, max_requests - current - 1}
    else
        return {0, 0}
    end
    """

    @classmethod
    def check(cls, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """Atomic rate limit check using Lua script."""
        now = int(time.time())
        window_key = f"ratelimit:{key}:{now // window_seconds}"

        result = redis_client.eval(
            cls.TOKEN_BUCKET_SCRIPT,
            1,
            window_key,
            max_requests,
            window_seconds,
            now
        )

        allowed = bool(result[0])
        remaining = result[1]

        return allowed, remaining
```

---

## Key Takeaways

1. **Token bucket** for simple, efficient rate limiting
2. **Sliding window** for accurate enforcement (higher cost)
3. **Redis Lua scripts** for atomic operations (no race conditions)
4. **Multiple dimensions** — per IP, per user, per email
5. **Graceful responses** — 429 status + Retry-After header
6. **Cleanup old keys** with EXPIRE to prevent memory leaks

**OWASP:** API4:2023 – Unrestricted Resource Consumption
**HTTP Status:** 429 Too Many Requests
**Headers:** X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
