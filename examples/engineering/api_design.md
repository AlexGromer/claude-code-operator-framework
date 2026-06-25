# Few-Shot Example: REST API Design Best Practices

**Domain:** engineering
**Skill Level:** Intermediate
**Pattern:** Design → Implement → Document → Test

---

## User Query

We're building an e-commerce API. Need to design endpoints for:
- Products (CRUD, search, categories)
- Orders (create, status, history)
- Users (registration, profile, addresses)

What are the best practices for REST API design? Show me concrete examples.

---

## Exemplary Response

### 1. RESTful API Design Principles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      REST API DESIGN PRINCIPLES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. RESOURCE-ORIENTED                                                        │
│     URLs represent resources (nouns), not actions (verbs)                   │
│     ✅ GET /products/123                                                    │
│     ❌ GET /getProduct?id=123                                               │
│                                                                              │
│  2. HTTP METHODS FOR ACTIONS                                                 │
│     GET     → Read (idempotent, cacheable)                                  │
│     POST    → Create (not idempotent)                                       │
│     PUT     → Replace (idempotent)                                          │
│     PATCH   → Partial update (idempotent)                                   │
│     DELETE  → Remove (idempotent)                                           │
│                                                                              │
│  3. PROPER STATUS CODES                                                      │
│     2xx → Success (200 OK, 201 Created, 204 No Content)                     │
│     4xx → Client error (400 Bad Request, 404 Not Found)                     │
│     5xx → Server error (500 Internal Error)                                 │
│                                                                              │
│  4. CONSISTENT NAMING                                                        │
│     • Plural nouns: /products, /orders, /users                              │
│     • Lowercase with hyphens: /order-items                                  │
│     • Hierarchical: /users/123/addresses/456                                │
│                                                                              │
│  5. VERSIONING                                                               │
│     /api/v1/products (URL versioning - most common)                         │
│     Accept: application/vnd.api.v1+json (header versioning)                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Endpoint Design

#### 2.1 Products API

```yaml
# Products endpoints
endpoints:
  # ═══════════════════════════════════════════════════════════════════════════
  # PRODUCTS - Core CRUD
  # ═══════════════════════════════════════════════════════════════════════════

  list_products:
    method: GET
    path: /api/v1/products
    description: List products with filtering and pagination
    query_params:
      - name: page
        type: integer
        default: 1
      - name: per_page
        type: integer
        default: 20
        max: 100
      - name: category
        type: string
        description: Filter by category slug
      - name: min_price
        type: number
      - name: max_price
        type: number
      - name: sort
        type: string
        enum: [price_asc, price_desc, created_at, popularity]
        default: created_at
      - name: q
        type: string
        description: Search query
    response: 200 OK

  get_product:
    method: GET
    path: /api/v1/products/{product_id}
    response: 200 OK | 404 Not Found

  create_product:
    method: POST
    path: /api/v1/products
    auth: required (admin)
    response: 201 Created

  update_product:
    method: PUT
    path: /api/v1/products/{product_id}
    auth: required (admin)
    response: 200 OK | 404 Not Found

  patch_product:
    method: PATCH
    path: /api/v1/products/{product_id}
    auth: required (admin)
    description: Partial update
    response: 200 OK | 404 Not Found

  delete_product:
    method: DELETE
    path: /api/v1/products/{product_id}
    auth: required (admin)
    response: 204 No Content | 404 Not Found

  # ═══════════════════════════════════════════════════════════════════════════
  # PRODUCTS - Related resources
  # ═══════════════════════════════════════════════════════════════════════════

  get_product_reviews:
    method: GET
    path: /api/v1/products/{product_id}/reviews
    description: Nested resource - reviews for a product
    response: 200 OK

  create_product_review:
    method: POST
    path: /api/v1/products/{product_id}/reviews
    auth: required
    response: 201 Created

  # ═══════════════════════════════════════════════════════════════════════════
  # CATEGORIES
  # ═══════════════════════════════════════════════════════════════════════════

  list_categories:
    method: GET
    path: /api/v1/categories
    response: 200 OK

  get_category_products:
    method: GET
    path: /api/v1/categories/{category_slug}/products
    description: Products in category (alternative to query param)
    response: 200 OK
```

#### 2.2 Orders API

```yaml
endpoints:
  # ═══════════════════════════════════════════════════════════════════════════
  # ORDERS
  # ═══════════════════════════════════════════════════════════════════════════

  create_order:
    method: POST
    path: /api/v1/orders
    auth: required
    description: Create new order from cart
    response: 201 Created

  list_orders:
    method: GET
    path: /api/v1/orders
    auth: required
    description: Current user's orders
    query_params:
      - name: status
        type: string
        enum: [pending, paid, shipped, delivered, cancelled]
    response: 200 OK

  get_order:
    method: GET
    path: /api/v1/orders/{order_id}
    auth: required
    description: Get order details (only owner or admin)
    response: 200 OK | 403 Forbidden | 404 Not Found

  # State transitions - use verbs for actions on resources
  cancel_order:
    method: POST
    path: /api/v1/orders/{order_id}/cancel
    auth: required
    description: Cancel order (action, not CRUD)
    response: 200 OK | 400 Bad Request (already shipped)

  # Admin operations
  update_order_status:
    method: PATCH
    path: /api/v1/orders/{order_id}
    auth: required (admin)
    body:
      status: shipped
      tracking_number: ABC123
    response: 200 OK
```

#### 2.3 Users API

```yaml
endpoints:
  # ═══════════════════════════════════════════════════════════════════════════
  # USERS & AUTHENTICATION
  # ═══════════════════════════════════════════════════════════════════════════

  register:
    method: POST
    path: /api/v1/auth/register
    response: 201 Created | 400 Bad Request (validation)

  login:
    method: POST
    path: /api/v1/auth/login
    response: 200 OK (with tokens) | 401 Unauthorized

  refresh_token:
    method: POST
    path: /api/v1/auth/refresh
    response: 200 OK | 401 Unauthorized

  logout:
    method: POST
    path: /api/v1/auth/logout
    auth: required
    response: 204 No Content

  # Current user
  get_profile:
    method: GET
    path: /api/v1/users/me
    auth: required
    response: 200 OK

  update_profile:
    method: PATCH
    path: /api/v1/users/me
    auth: required
    response: 200 OK

  # Addresses (nested resource)
  list_addresses:
    method: GET
    path: /api/v1/users/me/addresses
    auth: required
    response: 200 OK

  create_address:
    method: POST
    path: /api/v1/users/me/addresses
    auth: required
    response: 201 Created

  update_address:
    method: PUT
    path: /api/v1/users/me/addresses/{address_id}
    auth: required
    response: 200 OK | 404 Not Found

  delete_address:
    method: DELETE
    path: /api/v1/users/me/addresses/{address_id}
    auth: required
    response: 204 No Content

  set_default_address:
    method: POST
    path: /api/v1/users/me/addresses/{address_id}/set-default
    auth: required
    response: 200 OK
```

### 3. Request/Response Formats

#### 3.1 Standard Response Structure

```python
# Successful response (single resource)
{
    "data": {
        "id": "prod_123",
        "type": "product",
        "attributes": {
            "name": "Wireless Headphones",
            "description": "High-quality wireless headphones",
            "price": 99.99,
            "currency": "USD",
            "stock": 150,
            "created_at": "2026-01-15T10:30:00Z",
            "updated_at": "2026-01-20T14:22:00Z"
        },
        "relationships": {
            "category": {
                "data": {"type": "category", "id": "cat_electronics"}
            },
            "brand": {
                "data": {"type": "brand", "id": "brand_sony"}
            }
        },
        "links": {
            "self": "/api/v1/products/prod_123",
            "reviews": "/api/v1/products/prod_123/reviews"
        }
    },
    "meta": {
        "request_id": "req_abc123"
    }
}

# Successful response (collection)
{
    "data": [
        {"id": "prod_123", "type": "product", "attributes": {...}},
        {"id": "prod_124", "type": "product", "attributes": {...}}
    ],
    "meta": {
        "total": 1250,
        "page": 1,
        "per_page": 20,
        "total_pages": 63,
        "request_id": "req_abc123"
    },
    "links": {
        "self": "/api/v1/products?page=1",
        "first": "/api/v1/products?page=1",
        "last": "/api/v1/products?page=63",
        "next": "/api/v1/products?page=2",
        "prev": null
    }
}

# Error response
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request data",
        "details": [
            {
                "field": "price",
                "message": "Price must be a positive number",
                "code": "invalid_value"
            },
            {
                "field": "name",
                "message": "Name is required",
                "code": "required"
            }
        ]
    },
    "meta": {
        "request_id": "req_abc123"
    }
}
```

#### 3.2 Request Examples

```python
# POST /api/v1/products
# Create product
{
    "name": "Wireless Headphones",
    "description": "High-quality wireless headphones with noise cancellation",
    "price": 99.99,
    "currency": "USD",
    "category_id": "cat_electronics",
    "brand_id": "brand_sony",
    "sku": "WH-1000XM5",
    "stock": 100,
    "images": [
        {"url": "https://cdn.example.com/img1.jpg", "is_primary": true},
        {"url": "https://cdn.example.com/img2.jpg", "is_primary": false}
    ],
    "attributes": {
        "color": "black",
        "weight": "250g",
        "battery_life": "30 hours"
    }
}

# PATCH /api/v1/products/prod_123
# Partial update (only fields being changed)
{
    "price": 89.99,
    "stock": 75
}

# POST /api/v1/orders
# Create order
{
    "shipping_address_id": "addr_123",
    "billing_address_id": "addr_123",
    "items": [
        {"product_id": "prod_123", "quantity": 2},
        {"product_id": "prod_456", "quantity": 1}
    ],
    "coupon_code": "SAVE10",
    "notes": "Please leave at door"
}
```

### 4. Implementation (FastAPI)

```python
# app/api/v1/products.py
from fastapi import APIRouter, Query, Path, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/api/v1/products", tags=["products"])


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class SortOrder(str, Enum):
    price_asc = "price_asc"
    price_desc = "price_desc"
    created_at = "created_at"
    popularity = "popularity"


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    price: float = Field(..., gt=0)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    category_id: str
    stock: int = Field(default=0, ge=0)


class ProductCreate(ProductBase):
    sku: str = Field(..., min_length=1, max_length=50)
    brand_id: Optional[str] = None


class ProductUpdate(BaseModel):
    """All fields optional for PATCH"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class ProductResponse(ProductBase):
    id: str
    sku: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    data: List[ProductResponse]
    meta: dict
    links: dict


class ErrorDetail(BaseModel):
    field: str
    message: str
    code: str


class ErrorResponse(BaseModel):
    error: dict


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("", response_model=PaginatedResponse)
async def list_products(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Category slug"),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    q: Optional[str] = Query(default=None, min_length=2, description="Search query"),
    sort: SortOrder = Query(default=SortOrder.created_at),
    db: Session = Depends(get_db)
):
    """
    List products with filtering, search, and pagination.

    - **page**: Page number (starts at 1)
    - **per_page**: Items per page (max 100)
    - **category**: Filter by category slug
    - **min_price/max_price**: Price range filter
    - **q**: Full-text search in name and description
    - **sort**: Sort order
    """
    query = db.query(Product)

    # Apply filters
    if category:
        query = query.join(Category).filter(Category.slug == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term)
            )
        )

    # Apply sorting
    sort_mapping = {
        SortOrder.price_asc: Product.price.asc(),
        SortOrder.price_desc: Product.price.desc(),
        SortOrder.created_at: Product.created_at.desc(),
        SortOrder.popularity: Product.sales_count.desc(),
    }
    query = query.order_by(sort_mapping[sort])

    # Pagination
    total = query.count()
    products = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    # Build response with HATEOAS links
    base_url = "/api/v1/products"
    return {
        "data": products,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        },
        "links": {
            "self": f"{base_url}?page={page}",
            "first": f"{base_url}?page=1",
            "last": f"{base_url}?page={total_pages}",
            "next": f"{base_url}?page={page + 1}" if page < total_pages else None,
            "prev": f"{base_url}?page={page - 1}" if page > 1 else None,
        }
    }


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str = Path(..., description="Product ID"),
    db: Session = Depends(get_db)
):
    """Get a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Product with id '{product_id}' not found"
                }
            }
        )

    return product


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new product (admin only)."""
    # Check for duplicate SKU
    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "DUPLICATE_SKU",
                    "message": f"Product with SKU '{product.sku}' already exists"
                }
            }
        )

    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Partially update a product (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Only update provided fields
    update_data = product_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)

    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a product (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return None  # 204 No Content
```

### 5. Error Handling

```python
# app/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Standard error codes
class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMITED = "RATE_LIMITED"


# HTTP status to error code mapping
STATUS_TO_CODE = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format validation errors consistently."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        errors.append({
            "field": field,
            "message": error["msg"],
            "code": error["type"]
        })

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": "Invalid request data",
                "details": errors
            },
            "meta": {
                "request_id": request.state.request_id
            }
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Format HTTP exceptions consistently."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": STATUS_TO_CODE.get(exc.status_code, "ERROR"),
                "message": exc.detail
            },
            "meta": {
                "request_id": request.state.request_id
            }
        }
    )
```

### 6. API Documentation (OpenAPI)

```python
# app/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="E-Commerce API",
    description="""
## Overview

E-commerce REST API for managing products, orders, and users.

## Authentication

Most endpoints require authentication via Bearer token:

```
Authorization: Bearer <access_token>
```

Get tokens via `/api/v1/auth/login`.

## Rate Limiting

- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- Admin: 10000 requests/hour

## Pagination

List endpoints support pagination:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

## Errors

All errors follow this format:
```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": [...]
    }
}
```
    """,
    version="1.0.0",
    terms_of_service="https://example.com/terms",
    contact={
        "name": "API Support",
        "email": "api@example.com"
    },
    license_info={
        "name": "MIT",
    }
)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### 7. Design Checklist

| Category | Practice | Example |
|----------|----------|---------|
| **URLs** | Use plural nouns | `/products`, `/orders` |
| **URLs** | Hierarchical nesting | `/users/123/addresses` |
| **URLs** | Max 2 levels nesting | Not `/a/1/b/2/c/3` |
| **Methods** | Use correct HTTP verbs | GET read, POST create |
| **Status** | Appropriate codes | 201 Created, 204 No Content |
| **Errors** | Consistent format | `{error: {code, message}}` |
| **Pagination** | Page-based or cursor | `?page=2&per_page=20` |
| **Filtering** | Query parameters | `?status=active&sort=name` |
| **Versioning** | URL prefix | `/api/v1/` |
| **Docs** | OpenAPI/Swagger | Auto-generated |

---

## Why This Is A Good Example

- Complete endpoint design for real use case
- Standard response formats (JSON:API inspired)
- Full implementation with FastAPI
- Proper error handling patterns
- OpenAPI documentation included

---

## Key Patterns

1. **Resource-Oriented** - URLs as nouns, HTTP verbs for actions
2. **Consistent Responses** - Same structure for success/error
3. **HATEOAS Links** - Self-describing API
4. **Proper Status Codes** - Semantically correct responses

---

**Tags:** #engineering #api #rest #fastapi #design #documentation
**Version:** 1.0.0
**Last Updated:** 2026-01-23
