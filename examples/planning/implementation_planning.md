# Example: Implementation Planning

**Task Type:** Plan feature implementation
**Complexity:** Medium
**Model:** Sonnet (structured planning)

---

## User Request

> Plan implementation for adding user authentication to our Flask API. We need:
> - User registration
> - Login/logout
> - Password reset
> - Session management

---

## Claude's Reasoning Process

### 1. Requirements Analysis
- **Scope:** Full authentication system
- **Components:** Registration, login, sessions, password reset
- **Concerns:** Security, scalability, UX

### 2. Architecture Decisions
- Use Flask-Login for session management
- JWT for stateless API auth (optional)
- bcrypt for password hashing
- Email service for password reset

### 3. Implementation Phases
- Phase 1: Core (register, login, logout)
- Phase 2: Password reset
- Phase 3: Security hardening

---

## Claude's Response

### Implementation Plan: User Authentication

#### Phase 1: Core Authentication (Est: 6-8 hours)

**1.1 Database Schema (1 hour)**

```python
# models/user.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
```

**Migration:**
```bash
flask db init
flask db migrate -m "Add users table"
flask db upgrade
```

---

**1.2 Registration Endpoint (2 hours)**

```python
# routes/auth.py
from flask import Blueprint, request, jsonify
from models.user import User, db
from validators import validate_email, validate_password

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Validation
    if not validate_email(data.get('email')):
        return jsonify({'error': 'Invalid email'}), 400

    if not validate_password(data.get('password')):
        return jsonify({'error': 'Password too weak'}), 400

    # Check if user exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Create user
    user = User(
        username=data['username'],
        email=data['email']
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email
    }), 201
```

**Tests:**
- Valid registration
- Duplicate email rejection
- Password validation
- SQL injection prevention

---

**1.3 Login/Logout Endpoints (2 hours)**

```python
from flask_login import login_user, logout_user, login_required

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data['email']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    login_user(user)
    user.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'}), 200
```

---

**1.4 Session Management (1-2 hours)**

```python
# app.py
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

**Configuration:**
```python
# config.py
SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # Prevent XSS
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
```

---

#### Phase 2: Password Reset (Est: 4-6 hours)

**2.1 Password Reset Token (2 hours)**

```python
import secrets
from datetime import datetime, timedelta

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    @staticmethod
    def generate_token(user_id):
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        reset = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        db.session.add(reset)
        db.session.commit()

        return token
```

**2.2 Email Service (2-3 hours)**

```python
from flask_mail import Mail, Message

mail = Mail(app)

def send_password_reset_email(user, token):
    reset_url = f"https://app.example.com/reset-password?token={token}"

    msg = Message(
        subject="Password Reset Request",
        recipients=[user.email],
        body=f"Reset your password: {reset_url}"
    )

    mail.send(msg)
```

**Endpoints:**
```python
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.get_json().get('email')
    user = User.query.filter_by(email=email).first()

    if user:
        token = PasswordResetToken.generate_token(user.id)
        send_password_reset_email(user, token)

    # Always return success (prevent email enumeration)
    return jsonify({'message': 'If account exists, reset email sent'}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')

    reset = PasswordResetToken.query.filter_by(token=token, used=False).first()

    if not reset or reset.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired token'}), 400

    user = User.query.get(reset.user_id)
    user.set_password(new_password)
    reset.used = True

    db.session.commit()

    return jsonify({'message': 'Password reset successful'}), 200
```

---

#### Phase 3: Security Hardening (Est: 3-4 hours)

**3.1 Rate Limiting**
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 login attempts/min
def login():
    ...
```

**3.2 Account Lockout**
```python
# Add to User model
login_attempts = db.Column(db.Integer, default=0)
locked_until = db.Column(db.DateTime)

def check_lockout(self):
    if self.locked_until and self.locked_until > datetime.utcnow():
        return True
    return False

def increment_failed_login(self):
    self.login_attempts += 1
    if self.login_attempts >= 5:
        self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    db.session.commit()
```

**3.3 Security Tests**
- SQL injection prevention
- XSS prevention (escape user input)
- CSRF protection (enabled by default)
- Timing attack prevention (constant-time password check)

---

### Summary

**Total Estimated Time:** 13-18 hours

**Dependencies:**
- Flask-Login
- Flask-SQLAlchemy
- Flask-Mail
- Flask-Limiter
- bcrypt (via werkzeug)

**Next Steps:**
1. Set up development environment
2. Implement Phase 1 (core auth)
3. Write unit + integration tests
4. Security audit
5. Deploy Phase 2 (password reset)
6. Deploy Phase 3 (hardening)

---

## Key Takeaways

**This example demonstrates:**

1. **Phased Approach** — Break into manageable chunks
2. **Time Estimates** — Help user plan resources
3. **Code Examples** — Show implementation details
4. **Security Focus** — Address concerns upfront
5. **Dependencies List** — Clear external requirements

**Complexity Routing:** Medium (planning) → **Sonnet**
