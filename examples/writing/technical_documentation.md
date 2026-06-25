# Example: Technical Documentation Writing

## User Request

```
Напиши методологию создания технической документации для open-source проекта (API reference, user guides, architecture docs).
```

## Reasoning

**Domain:** Writing (Technical documentation, developer experience)
**Complexity:** Medium
**Model:** Sonnet

## Response

---

# Technical Documentation Framework for Open-Source Projects

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DOCUMENTATION HIERARCHY (Developer Experience Focus)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Tier 1: QUICKSTART (5 minutes to first success)                           │
│  ├─► Installation (copy-paste commands)                                     │
│  ├─► Hello World example (runnable immediately)                             │
│  └─► Core concepts (1-2 sentences per concept)                              │
│                                                                              │
│  Tier 2: TUTORIALS (30 minutes, goal-oriented)                             │
│  ├─► Step-by-step guides for common use cases                               │
│  ├─► Build something real (to-do app, API client, etc.)                     │
│  └─► Explain decisions and trade-offs                                       │
│                                                                              │
│  Tier 3: HOW-TO GUIDES (5-15 minutes, task-focused)                        │
│  ├─► Solve specific problems                                                │
│  ├─► Authentication, error handling, deployment, etc.                       │
│  └─► Assume basic knowledge                                                 │
│                                                                              │
│  Tier 4: API REFERENCE (exhaustive, look-up)                               │
│  ├─► All functions, classes, parameters                                     │
│  ├─► Auto-generated from docstrings                                         │
│  └─► Examples for each method                                               │
│                                                                              │
│  Tier 5: ARCHITECTURE DOCS (deep understanding)                            │
│  ├─► System design, data flow, component interaction                        │
│  ├─► Decision records (ADRs)                                                │
│  └─► Performance characteristics, scalability                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Documentation Type 1: Quickstart Guide

### Example: Python Web Framework (FastAPI-like)

#### BAD (overwhelming, no quick win):

```markdown
# WebFramework Documentation

WebFramework is a modern, high-performance web framework for building APIs with
Python 3.7+ based on standard Python type hints. It provides automatic API
documentation, data validation using Pydantic, dependency injection, OAuth2
authentication, WebSocket support, GraphQL integration, and...

[10 more paragraphs before any code]
```

**Problem:** User falls asleep before seeing code.

---

#### GOOD (quick win in 2 minutes):

```markdown
# WebFramework Quickstart

Get your API running in **2 minutes**.

### Install

```bash
pip install webframework
```

### Hello World

```python
# main.py
from webframework import WebFramework

app = WebFramework()

@app.get("/")
def hello():
    return {"message": "Hello World"}

# Run: webframework run main.py
# Open: http://localhost:8000
```

**You should see:** `{"message": "Hello World"}`

🎉 **Done!** Now let's build something real → [Tutorial: Build a TODO API](tutorial.md)

---

### Core Concepts (30 seconds read)

- **Routes**: Functions decorated with `@app.get/post/put/delete`
- **Auto validation**: Type hints → automatic request validation
- **Auto docs**: Swagger UI at `/docs` (try it now!)

---

### What's Next?

- [Tutorial: TODO API](tutorial-todo.md) (15 min)
- [How-To: Authentication](howto-auth.md) (10 min)
- [API Reference](api.md) (look-up)
```

**Key Principles:**
- Install + Hello World **before** any explanation
- Quick win in first 2 minutes (builds motivation)
- Core concepts: 3-5 bullet points maximum
- Clear next steps

---

## Documentation Type 2: Tutorial (Goal-Oriented)

### Example: Build a TODO API (Full CRUD)

```markdown
# Tutorial: Build a TODO API with WebFramework

**Goal:** Create a fully functional TODO API with database persistence.

**Time:** 30 minutes
**Prerequisites:** Completed Quickstart
**You'll learn:** CRUD operations, database integration, validation, error handling

---

## Step 1: Project Setup (5 min)

```bash
mkdir todo-api
cd todo-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install webframework sqlalchemy
```

Create project structure:
```
todo-api/
├── main.py        # API entry point
├── models.py      # Database models
├── schemas.py     # Pydantic schemas (validation)
└── database.py    # Database connection
```

---

## Step 2: Define Data Models (5 min)

### models.py — Database Schema

```python
# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class TodoItem(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500))
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TodoItem(id={self.id}, title={self.title})>"
```

**Why SQLAlchemy?** ORM provides type safety, migrations, and query builder.

---

### schemas.py — Request/Response Validation

```python
# schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TodoCreate(BaseModel):
    """Schema for creating a TODO item."""
    title: str = Field(..., min_length=1, max_length=100,
                       description="Title of the TODO item")
    description: Optional[str] = Field(None, max_length=500)

class TodoUpdate(BaseModel):
    """Schema for updating a TODO item."""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    completed: Optional[bool] = None

class TodoResponse(BaseModel):
    """Schema for TODO item in responses."""
    id: int
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode

# Example usage:
# valid_input = TodoCreate(title="Buy milk", description="2% fat")
# invalid_input = TodoCreate(title="")  # ValidationError: min_length=1
```

**Why Pydantic?** Automatic validation + serialization + API docs generation.

---

## Step 3: Database Connection (5 min)

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# SQLite for simplicity (use PostgreSQL in production)
DATABASE_URL = "sqlite:///./todos.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite only
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for route handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## Step 4: Build CRUD API (10 min)

```python
# main.py
from webframework import WebFramework, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import init_db, get_db
from models import TodoItem
from schemas import TodoCreate, TodoUpdate, TodoResponse

app = WebFramework()

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()

# CREATE: POST /todos
@app.post("/todos", response_model=TodoResponse, status_code=201)
def create_todo(
    todo: TodoCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new TODO item.

    - **title**: Required, 1-100 characters
    - **description**: Optional, up to 500 characters
    """
    db_todo = TodoItem(
        title=todo.title,
        description=todo.description
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

# READ: GET /todos (list all)
@app.get("/todos", response_model=List[TodoResponse])
def list_todos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all TODO items with pagination.

    - **skip**: Number of items to skip (default: 0)
    - **limit**: Max items to return (default: 100)
    """
    todos = db.query(TodoItem).offset(skip).limit(limit).all()
    return todos

# READ: GET /todos/{id} (get one)
@app.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(
    todo_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific TODO item by ID."""
    todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()

    if todo is None:
        raise HTTPException(status_code=404, detail="TODO not found")

    return todo

# UPDATE: PUT /todos/{id}
@app.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(
    todo_id: int,
    todo_update: TodoUpdate,
    db: Session = Depends(get_db)
):
    """Update a TODO item (partial updates allowed)."""
    db_todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()

    if db_todo is None:
        raise HTTPException(status_code=404, detail="TODO not found")

    # Update only provided fields (partial update)
    update_data = todo_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_todo, key, value)

    db.commit()
    db.refresh(db_todo)
    return db_todo

# DELETE: DELETE /todos/{id}
@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db)
):
    """Delete a TODO item."""
    db_todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()

    if db_todo is None:
        raise HTTPException(status_code=404, detail="TODO not found")

    db.delete(db_todo)
    db.commit()
    return None  # 204 No Content

# Bonus: Mark as completed
@app.patch("/todos/{todo_id}/complete", response_model=TodoResponse)
def complete_todo(
    todo_id: int,
    db: Session = Depends(get_db)
):
    """Mark TODO as completed."""
    db_todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()

    if db_todo is None:
        raise HTTPException(status_code=404, detail="TODO not found")

    db_todo.completed = True
    db.commit()
    db.refresh(db_todo)
    return db_todo
```

---

## Step 5: Test Your API (5 min)

### Start the server:

```bash
webframework run main.py
# Server running at http://localhost:8000
```

### Interactive API Docs:

Open http://localhost:8000/docs → Try it out!

### Manual testing with curl:

```bash
# CREATE
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk", "description": "2% fat"}'

# Response: {"id": 1, "title": "Buy milk", ...}

# LIST
curl http://localhost:8000/todos

# GET ONE
curl http://localhost:8000/todos/1

# UPDATE
curl -X PUT http://localhost:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

# DELETE
curl -X DELETE http://localhost:8000/todos/1
```

---

## What You Built

✅ Full CRUD API (Create, Read, Update, Delete)
✅ Database persistence (SQLite)
✅ Automatic validation (Pydantic schemas)
✅ Interactive docs (Swagger UI)
✅ Proper error handling (404 for missing items)
✅ Pagination support (skip/limit)

---

## Next Steps

### Add Authentication
[How-To: JWT Authentication](howto-auth.md)

### Deploy to Production
[How-To: Deploy with Docker + PostgreSQL](howto-deploy.md)

### Add Tests
[How-To: Test Your API](howto-testing.md)
```

**Tutorial Best Practices:**
- Build something real (not toy examples)
- Show complete working code (copy-pasteable)
- Explain WHY (not just HOW)
- Test instructions (verify it works)
- Clear next steps

---

## Documentation Type 3: API Reference

### Auto-Generation from Docstrings

```python
# example_module.py

def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    unit: str = "km"
) -> float:
    """
    Calculate distance between two geographic coordinates.

    Uses the Haversine formula to compute the great-circle distance
    between two points on Earth's surface.

    Args:
        lat1: Latitude of first point (decimal degrees, -90 to 90)
        lon1: Longitude of first point (decimal degrees, -180 to 180)
        lat2: Latitude of second point (decimal degrees, -90 to 90)
        lon2: Longitude of second point (decimal degrees, -180 to 180)
        unit: Distance unit, either "km" (kilometers) or "mi" (miles).
              Defaults to "km".

    Returns:
        Distance between the two points in the specified unit.

    Raises:
        ValueError: If coordinates are out of valid range or unit is invalid.

    Examples:
        >>> calculate_distance(40.7128, -74.0060, 34.0522, -118.2437)
        3944.42  # New York to Los Angeles

        >>> calculate_distance(51.5074, -0.1278, 48.8566, 2.3522, unit="mi")
        213.37  # London to Paris

        >>> calculate_distance(100, 0, 0, 0)
        ValueError: Latitude must be between -90 and 90

    Notes:
        - Assumes Earth is a perfect sphere (R = 6371 km)
        - Accuracy decreases for very small distances (<1 meter)
        - For precise geodesic calculations, use GeographicLib

    See Also:
        - haversine_formula: Low-level implementation
        - vincenty_distance: More accurate geodesic calculation

    References:
        - https://en.wikipedia.org/wiki/Haversine_formula
    """
    import math

    # Validation
    if not (-90 <= lat1 <= 90) or not (-90 <= lat2 <= 90):
        raise ValueError("Latitude must be between -90 and 90")

    if not (-180 <= lon1 <= 180) or not (-180 <= lon2 <= 180):
        raise ValueError("Longitude must be between -180 and 180")

    if unit not in ["km", "mi"]:
        raise ValueError("Unit must be 'km' or 'mi'")

    # Haversine formula
    R = 6371 if unit == "km" else 3959  # Earth radius

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return round(distance, 2)
```

**Docstring Structure (Google Style):**

```python
"""
One-line summary (appears in function signature).

Multi-paragraph extended description. Explain behavior, algorithms,
edge cases, and any gotchas.

Args:
    param1 (type): Description with valid range/format
    param2 (type, optional): Description. Defaults to value.

Returns:
    type: Description of return value

Raises:
    ErrorType: When this error occurs

Examples:
    >>> code_example()
    expected_output

Notes:
    - Important implementation detail
    - Performance characteristics

See Also:
    - related_function: Brief description

References:
    - URL or paper citation
"""
```

**Auto-generate docs:**

```bash
# Sphinx (Python standard)
sphinx-apidoc -o docs/api myproject/
sphinx-build docs docs/_build

# MkDocs (modern, fast)
mkdocstrings myproject/

# pdoc (minimal setup)
pdoc --html myproject/
```

---

## Documentation Type 4: Architecture Decision Records (ADRs)

### Template: ADR-001-database-choice.md

```markdown
# ADR-001: Use PostgreSQL for Primary Database

**Status:** Accepted
**Date:** 2024-01-15
**Deciders:** Engineering Team
**Consulted:** DBA Team, Security Team

---

## Context

We need to choose a relational database for the new user management system.
Requirements:
- Support 10M+ users
- ACID transactions (financial data)
- Full-text search
- JSON fields for flexible metadata
- Mature ecosystem (ORMs, tools, monitoring)

---

## Decision

We will use **PostgreSQL 15** as the primary database.

---

## Rationale

### Considered Alternatives

| Database | Pros | Cons | Score |
|----------|------|------|-------|
| **PostgreSQL** | ACID, JSON, full-text search, MVCC, extensions | Slightly slower writes than MySQL | ⭐⭐⭐⭐⭐ |
| **MySQL** | Fast writes, wide adoption | Weaker JSON support, no MVCC | ⭐⭐⭐ |
| **SQLite** | Zero setup, embedded | Single writer, no network | ⭐⭐ (dev only) |
| **MongoDB** | Flexible schema, fast reads | No ACID across collections | ⭐⭐ |

### Why PostgreSQL?

1. **ACID Guarantees**: Critical for financial transactions
   - MVCC (Multi-Version Concurrency Control) prevents read locks
   - Serializable isolation level available

2. **JSON Support**: JSONB type with indexing
   ```sql
   SELECT * FROM users WHERE metadata @> '{"premium": true}';
   -- Uses GIN index, fast lookup
   ```

3. **Full-Text Search**: Built-in, no Elasticsearch needed (initially)
   ```sql
   SELECT * FROM articles WHERE to_tsvector(content) @@ to_tsquery('postgresql');
   ```

4. **Extensions**: PostGIS (geo), pg_stat_statements (monitoring), pgcrypto
5. **Ecosystem**: Supported by all major ORMs (Django, SQLAlchemy, Prisma)
6. **Performance**: 50K writes/sec, 200K reads/sec (tested on our hardware)

---

## Consequences

### Positive

- ✅ Strong ACID guarantees (no data corruption)
- ✅ JSON + relational in one DB (no MongoDB needed)
- ✅ Rich indexing (B-tree, GIN, GiST, BRIN)
- ✅ Excellent observability (pg_stat_* views)

### Negative

- ❌ Slightly slower writes than MySQL (acceptable trade-off)
- ❌ More complex tuning (shared_buffers, work_mem, etc.)
- ❌ No built-in sharding (use Citus extension if needed)

### Neutral

- ⚪ Team needs to learn PostgreSQL-specific features (CTEs, window functions)
- ⚪ Monitoring setup required (pg_stat_statements, pgBadger)

---

## Implementation

- **Phase 1** (Week 1-2): PostgreSQL 15 setup, pgBouncer connection pooling
- **Phase 2** (Week 3-4): Schema design, migrations with Alembic
- **Phase 3** (Week 5-6): Performance tuning, index optimization
- **Phase 4** (Week 7+): Monitoring (Grafana + Prometheus)

---

## Related ADRs

- ADR-002: Use pgBouncer for Connection Pooling
- ADR-005: Database Backup Strategy (pg_basebackup + WAL archiving)

---

## References

- [PostgreSQL vs MySQL Benchmark](https://example.com/benchmark)
- [Why Uber Switched from PostgreSQL to MySQL](https://example.com/uber) (opposite decision, context matters!)
- [PostgreSQL 15 Release Notes](https://www.postgresql.org/docs/15/release-15.html)
```

**ADR Best Practices:**
- Record decisions, not requirements
- Capture alternatives considered (not just winner)
- Document consequences (positive + negative)
- Date decisions (context changes over time)
- Link related ADRs

---

## Documentation Anti-Patterns

| Anti-Pattern | Why Bad | Solution |
|--------------|---------|----------|
| **"Obviously"** | Not obvious to beginners | Explain or link to prerequisite |
| **Outdated examples** | Copy-paste fails, trust lost | CI tests for docs examples |
| **No code examples** | Abstract explanations confuse | Show code first, explain after |
| **Wall of text** | Hard to scan | Use headers, lists, code blocks |
| **Missing error examples** | Users don't know what went wrong | Show common errors + fixes |
| **No search** | Users can't find information | Algolia DocSearch or built-in search |
| **Single format only** | Excludes learning styles | Provide text + video + interactive |

---

## Documentation Automation

### 1. Auto-Generate API Docs from Code

```python
# docs_generator.py — Extract API docs from code

import ast
import inspect
from pathlib import Path
from typing import List, Dict

class APIDocGenerator:
    """
    Generate API documentation from Python source code.
    Extracts docstrings, type hints, and examples.
    """

    def __init__(self, source_dir: Path):
        self.source_dir = source_dir
        self.docs = []

    def extract_function_docs(self, module_path: Path) -> List[Dict]:
        """
        Extract function documentation from a Python module.
        """
        with open(module_path, 'r') as f:
            tree = ast.parse(f.read(), filename=str(module_path))

        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_doc = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node),
                    'args': [arg.arg for arg in node.args.args],
                    'returns': self._get_return_annotation(node),
                    'examples': self._extract_examples(ast.get_docstring(node))
                }
                functions.append(func_doc)

        return functions

    def _get_return_annotation(self, node: ast.FunctionDef) -> str:
        """Extract return type annotation."""
        if node.returns:
            return ast.unparse(node.returns)
        return "None"

    def _extract_examples(self, docstring: str) -> List[str]:
        """Extract code examples from docstring."""
        if not docstring:
            return []

        examples = []
        in_example = False
        current_example = []

        for line in docstring.split('\n'):
            if line.strip().startswith('>>>'):
                in_example = True
                current_example.append(line.strip())
            elif in_example:
                if line.strip() and not line.strip().startswith('...'):
                    examples.append('\n'.join(current_example))
                    current_example = []
                    in_example = False
                else:
                    current_example.append(line.strip())

        return examples

    def generate_markdown(self, functions: List[Dict]) -> str:
        """Generate Markdown API reference."""
        md = "# API Reference\n\n"

        for func in functions:
            md += f"## `{func['name']}({', '.join(func['args'])})`\n\n"

            if func['docstring']:
                md += f"{func['docstring']}\n\n"

            md += f"**Returns:** `{func['returns']}`\n\n"

            if func['examples']:
                md += "**Examples:**\n\n"
                for example in func['examples']:
                    md += f"```python\n{example}\n```\n\n"

            md += "---\n\n"

        return md

# Usage
generator = APIDocGenerator(Path("myproject"))
functions = generator.extract_function_docs(Path("myproject/api.py"))
markdown = generator.generate_markdown(functions)

with open("docs/api-reference.md", "w") as f:
    f.write(markdown)
```

### 2. Test Documentation Examples

```python
# test_docs.py — Ensure all examples in docs are valid

import re
import subprocess
from pathlib import Path

def extract_code_blocks(markdown_path: Path) -> list:
    """Extract Python code blocks from Markdown."""
    with open(markdown_path, 'r') as f:
        content = f.read()

    # Regex to find ```python ... ``` blocks
    pattern = r'```python\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    return matches

def test_code_block(code: str) -> bool:
    """Test if code block is valid Python."""
    try:
        # Write to temp file
        temp_file = Path("/tmp/test_doc_example.py")
        temp_file.write_text(code)

        # Run syntax check
        result = subprocess.run(
            ["python", "-m", "py_compile", str(temp_file)],
            capture_output=True,
            text=True
        )

        return result.returncode == 0

    except Exception as e:
        print(f"Error testing code: {e}")
        return False

# CI Integration
docs_dir = Path("docs")
all_passed = True

for doc_file in docs_dir.glob("**/*.md"):
    print(f"Testing {doc_file}...")

    code_blocks = extract_code_blocks(doc_file)

    for i, code in enumerate(code_blocks):
        if not test_code_block(code):
            print(f"  ❌ Code block {i+1} failed")
            all_passed = False
        else:
            print(f"  ✅ Code block {i+1} passed")

if not all_passed:
    exit(1)  # Fail CI
```

---

## Documentation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Coverage** | 100% public APIs documented | Count functions with docstrings |
| **Freshness** | Updated within 1 week of code change | Git blame on docs vs code |
| **Accuracy** | >95% examples work | CI tests all code examples |
| **Search success** | >80% queries find answer | Google Analytics on docs site |
| **Time to first success** | <5 minutes | User testing on Quickstart |
| **Bounce rate** | <30% | Analytics: users leave immediately |

---

## Key Takeaways

1. **Hierarchy matters** — Quickstart → Tutorials → How-Tos → Reference → Architecture
2. **Quick win first** — 2-minute install + Hello World before any explanation
3. **Tutorials are goal-oriented** — Build something real (not toy examples)
4. **API docs from code** — Auto-generate from docstrings (single source of truth)
5. **Test documentation** — CI should run all code examples
6. **Decision records** — Capture WHY (alternatives, trade-offs, consequences)

**Documentation Formula:**
```
Quick Win (2 min) → Tutorial (30 min) → How-Tos (10 min) → Reference (lookup) → Architecture (deep dive)
```

**Time Investment:**
- Quickstart: 2 hours
- Tutorial: 4-6 hours per tutorial
- How-Tos: 1-2 hours each
- API reference: Auto-generated (5 hours setup)
- Architecture docs: 2-4 hours per ADR

**Tools:** Sphinx, MkDocs, Docusaurus, Algolia DocSearch, Read the Docs
