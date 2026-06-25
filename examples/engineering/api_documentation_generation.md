# Example: Technical Documentation

**Task Type:** Generate API documentation
**Complexity:** Simple
**Model:** Haiku (straightforward task)

---

## User Request

> Write documentation for this API endpoint:
>
> ```python
> @app.route('/api/users/<int:user_id>', methods=['GET'])
> def get_user(user_id):
>     user = User.query.get_or_404(user_id)
>     return jsonify({
>         'id': user.id,
>         'username': user.username,
>         'email': user.email,
>         'created_at': user.created_at.isoformat()
>     })
> ```

---

## Claude's Response

### API Endpoint Documentation

#### `GET /api/users/{user_id}`

Retrieve a single user by ID.

**Parameters:**

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
| `user_id` | integer | path | Yes | Unique identifier of the user |

**Request Example:**
```http
GET /api/users/123 HTTP/1.1
Host: api.example.com
Accept: application/json
```

**Response (200 OK):**
```json
{
  "id": 123,
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "2026-01-27T10:30:00Z"
}
```

**Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | User's unique identifier |
| `username` | string | User's display name |
| `email` | string | User's email address |
| `created_at` | string (ISO 8601) | Account creation timestamp |

**Error Responses:**

| Status | Description | Response Body |
|--------|-------------|---------------|
| 404 Not Found | User does not exist | `{"error": "User not found"}` |
| 500 Internal Server Error | Server error | `{"error": "Internal server error"}` |

**Example Usage:**

```bash
# cURL
curl -X GET "https://api.example.com/api/users/123" \
     -H "Accept: application/json"
```

```python
# Python (requests)
import requests

response = requests.get("https://api.example.com/api/users/123")
user = response.json()
print(f"Username: {user['username']}")
```

```javascript
// JavaScript (fetch)
fetch("https://api.example.com/api/users/123")
  .then(response => response.json())
  .then(user => console.log(`Username: ${user.username}`));
```

**Notes:**
- Requires authentication: No (public endpoint)
- Rate limit: 1000 requests/hour per IP
- Caching: 5 minutes

---

## Key Takeaways

**This example demonstrates:**

1. **Complete API Documentation** — All essential sections
2. **Multiple Languages** — Examples in bash, Python, JavaScript
3. **Schema Documentation** — Table format for clarity
4. **Error Cases** — Document failure scenarios
5. **Practical Examples** — Copy-paste ready code

**Complexity Routing:** Simple → **Haiku** (straightforward documentation generation)
