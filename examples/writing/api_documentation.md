# Example: API Documentation Writing

## User Request

```
Напиши методологию создания API documentation (REST API reference, OpenAPI spec, code examples, SDK docs).
```

## Reasoning

**Domain:** Writing (API documentation, developer experience)
**Complexity:** Medium
**Model:** Sonnet

## Response

---

# API Documentation Framework

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  API DOCUMENTATION HIERARCHY (Developer-First Approach)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Tier 1: QUICKSTART (5 minutes to first API call)                          │
│  ├─► Authentication setup (get API key)                                     │
│  ├─► First request (curl + response)                                        │
│  └─► SDK installation (Python, Node.js, etc.)                               │
│                                                                              │
│  Tier 2: GUIDES (30 minutes, use-case driven)                              │
│  ├─► Common workflows (authentication, pagination, webhooks)                │
│  ├─► Best practices (rate limiting, error handling)                         │
│  └─► Security (OAuth, JWT, API key rotation)                                │
│                                                                              │
│  Tier 3: API REFERENCE (exhaustive, auto-generated)                        │
│  ├─► Endpoints (all HTTP methods, parameters)                               │
│  ├─► Request/response schemas (JSON examples)                               │
│  └─► Status codes and error messages                                        │
│                                                                              │
│  Tier 4: SDK DOCS (language-specific)                                      │
│  ├─► Installation (pip, npm, gem, etc.)                                     │
│  ├─► Code examples (idiomatic per language)                                 │
│  └─► Auto-generated from docstrings                                         │
│                                                                              │
│  Tier 5: CHANGELOG & MIGRATION (versioning)                                │
│  ├─► Version history (semantic versioning)                                  │
│  ├─► Breaking changes (migration guides)                                    │
│  └─► Deprecation notices (sunset timeline)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## OpenAPI 3.0 Specification (Complete Example)

### File: openapi.yaml

```yaml
openapi: 3.0.3
info:
  title: E-Commerce API
  description: |
    REST API for managing products, orders, and customers.

    ## Features
    - Product catalog management
    - Order processing
    - Customer authentication
    - Webhook notifications

    ## Rate Limiting
    - 1000 requests/hour for authenticated users
    - 100 requests/hour for unauthenticated users

    ## Support
    - Email: api-support@example.com
    - Slack: https://slack.example.com
  version: 2.1.0
  contact:
    name: API Support Team
    email: api-support@example.com
    url: https://api.example.com/support
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.example.com/v2
    description: Production server
  - url: https://sandbox-api.example.com/v2
    description: Sandbox server (test data)
  - url: http://localhost:8080/v2
    description: Local development

tags:
  - name: Products
    description: Product catalog operations
  - name: Orders
    description: Order management
  - name: Auth
    description: Authentication and authorization

# ============================================================================
# SECURITY SCHEMES
# ============================================================================

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: |
        API key for authentication. Get your key at https://dashboard.example.com/api-keys

        Example:
        ```
        curl -H "X-API-Key: sk_live_abc123..." https://api.example.com/v2/products
        ```

    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT token for authenticated users. Obtain via `/auth/login` endpoint.

        Example:
        ```
        curl -H "Authorization: Bearer eyJhbGc..." https://api.example.com/v2/orders
        ```

# ============================================================================
# REUSABLE SCHEMAS
# ============================================================================

  schemas:
    Product:
      type: object
      required:
        - id
        - name
        - price
      properties:
        id:
          type: string
          format: uuid
          example: "550e8400-e29b-41d4-a716-446655440000"
          description: Unique product identifier
        name:
          type: string
          minLength: 1
          maxLength: 200
          example: "Wireless Headphones"
          description: Product display name
        description:
          type: string
          maxLength: 2000
          example: "High-quality Bluetooth headphones with active noise cancellation"
        price:
          type: number
          format: float
          minimum: 0
          example: 149.99
          description: Price in USD
        currency:
          type: string
          enum: [USD, EUR, GBP]
          default: USD
          example: "USD"
        stock:
          type: integer
          minimum: 0
          example: 250
          description: Current inventory count
        category:
          type: string
          enum: [Electronics, Clothing, Books, Home, Sports]
          example: "Electronics"
        tags:
          type: array
          items:
            type: string
          example: ["wireless", "audio", "bluetooth"]
        image_url:
          type: string
          format: uri
          example: "https://cdn.example.com/products/headphones.jpg"
        created_at:
          type: string
          format: date-time
          example: "2024-01-15T10:30:00Z"
          readOnly: true
        updated_at:
          type: string
          format: date-time
          example: "2024-01-20T14:22:00Z"
          readOnly: true

    Order:
      type: object
      required:
        - id
        - customer_id
        - items
        - total
      properties:
        id:
          type: string
          format: uuid
          example: "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        customer_id:
          type: string
          format: uuid
          example: "123e4567-e89b-12d3-a456-426614174000"
        items:
          type: array
          items:
            $ref: '#/components/schemas/OrderItem'
          minItems: 1
        total:
          type: number
          format: float
          example: 299.98
        status:
          type: string
          enum: [pending, processing, shipped, delivered, cancelled]
          default: pending
          example: "processing"
        created_at:
          type: string
          format: date-time
          example: "2024-01-15T10:30:00Z"

    OrderItem:
      type: object
      required:
        - product_id
        - quantity
        - price
      properties:
        product_id:
          type: string
          format: uuid
          example: "550e8400-e29b-41d4-a716-446655440000"
        quantity:
          type: integer
          minimum: 1
          example: 2
        price:
          type: number
          format: float
          example: 149.99

    Error:
      type: object
      required:
        - error
        - message
      properties:
        error:
          type: string
          example: "invalid_request"
          description: Machine-readable error code
        message:
          type: string
          example: "Product with ID '123' not found"
          description: Human-readable error message
        details:
          type: object
          additionalProperties: true
          example:
            field: "product_id"
            issue: "not_found"
        request_id:
          type: string
          example: "req_abc123xyz"
          description: Unique request identifier for debugging

    PaginationMeta:
      type: object
      properties:
        total:
          type: integer
          example: 1523
          description: Total number of items
        page:
          type: integer
          example: 1
          description: Current page number
        per_page:
          type: integer
          example: 50
          description: Items per page
        total_pages:
          type: integer
          example: 31
          description: Total number of pages

# ============================================================================
# API ENDPOINTS
# ============================================================================

paths:
  /products:
    get:
      summary: List products
      description: |
        Retrieve a paginated list of products. Supports filtering by category,
        price range, and search query.

        ## Pagination
        Use `page` and `per_page` parameters. Maximum `per_page` is 100.

        ## Filtering
        - `category`: Filter by product category
        - `min_price`, `max_price`: Price range filter
        - `search`: Full-text search in name and description

        ## Sorting
        - `sort_by`: Field to sort by (name, price, created_at)
        - `order`: Sort order (asc, desc)
      operationId: listProducts
      tags:
        - Products
      security:
        - ApiKeyAuth: []
      parameters:
        - name: page
          in: query
          description: Page number (starts at 1)
          required: false
          schema:
            type: integer
            minimum: 1
            default: 1
            example: 1
        - name: per_page
          in: query
          description: Items per page (max 100)
          required: false
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 50
            example: 50
        - name: category
          in: query
          description: Filter by category
          required: false
          schema:
            type: string
            enum: [Electronics, Clothing, Books, Home, Sports]
            example: "Electronics"
        - name: min_price
          in: query
          description: Minimum price (inclusive)
          required: false
          schema:
            type: number
            format: float
            minimum: 0
            example: 50.00
        - name: max_price
          in: query
          description: Maximum price (inclusive)
          required: false
          schema:
            type: number
            format: float
            minimum: 0
            example: 200.00
        - name: search
          in: query
          description: Search query (name, description)
          required: false
          schema:
            type: string
            example: "wireless headphones"
        - name: sort_by
          in: query
          description: Field to sort by
          required: false
          schema:
            type: string
            enum: [name, price, created_at]
            default: created_at
            example: "price"
        - name: order
          in: query
          description: Sort order
          required: false
          schema:
            type: string
            enum: [asc, desc]
            default: desc
            example: "asc"
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Product'
                  meta:
                    $ref: '#/components/schemas/PaginationMeta'
              examples:
                success:
                  summary: Successful product listing
                  value:
                    data:
                      - id: "550e8400-e29b-41d4-a716-446655440000"
                        name: "Wireless Headphones"
                        description: "High-quality Bluetooth headphones"
                        price: 149.99
                        currency: "USD"
                        stock: 250
                        category: "Electronics"
                        tags: ["wireless", "audio"]
                        image_url: "https://cdn.example.com/products/headphones.jpg"
                        created_at: "2024-01-15T10:30:00Z"
                        updated_at: "2024-01-20T14:22:00Z"
                    meta:
                      total: 1523
                      page: 1
                      per_page: 50
                      total_pages: 31
        '400':
          description: Invalid request parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
              examples:
                invalid_page:
                  summary: Invalid page number
                  value:
                    error: "invalid_request"
                    message: "Page must be greater than 0"
                    details:
                      field: "page"
                      issue: "out_of_range"
                    request_id: "req_abc123"
        '401':
          description: Missing or invalid API key
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
              examples:
                missing_key:
                  value:
                    error: "authentication_failed"
                    message: "API key is required. Include X-API-Key header."
                    request_id: "req_xyz789"
        '429':
          description: Rate limit exceeded
          headers:
            X-RateLimit-Limit:
              description: Request limit per hour
              schema:
                type: integer
                example: 1000
            X-RateLimit-Remaining:
              description: Requests remaining
              schema:
                type: integer
                example: 0
            X-RateLimit-Reset:
              description: Unix timestamp when limit resets
              schema:
                type: integer
                example: 1642345678
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
              examples:
                rate_limit:
                  value:
                    error: "rate_limit_exceeded"
                    message: "Rate limit of 1000 requests/hour exceeded. Try again at 2024-01-15T11:00:00Z"
                    request_id: "req_limit123"

    post:
      summary: Create product
      description: |
        Create a new product in the catalog. Requires admin API key.

        ## Validation
        - `name`: Required, 1-200 characters
        - `price`: Required, must be ≥ 0
        - `stock`: Optional, defaults to 0
      operationId: createProduct
      tags:
        - Products
      security:
        - ApiKeyAuth: []
      requestBody:
        description: Product data
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - name
                - price
              properties:
                name:
                  type: string
                  minLength: 1
                  maxLength: 200
                  example: "Mechanical Keyboard"
                description:
                  type: string
                  maxLength: 2000
                  example: "RGB backlit mechanical keyboard"
                price:
                  type: number
                  format: float
                  minimum: 0
                  example: 89.99
                currency:
                  type: string
                  enum: [USD, EUR, GBP]
                  default: USD
                stock:
                  type: integer
                  minimum: 0
                  default: 0
                  example: 100
                category:
                  type: string
                  enum: [Electronics, Clothing, Books, Home, Sports]
                  example: "Electronics"
                tags:
                  type: array
                  items:
                    type: string
                  example: ["mechanical", "keyboard", "rgb"]
                image_url:
                  type: string
                  format: uri
                  example: "https://cdn.example.com/products/keyboard.jpg"
            examples:
              keyboard:
                summary: Create mechanical keyboard
                value:
                  name: "Mechanical Keyboard"
                  description: "RGB backlit mechanical keyboard with Cherry MX switches"
                  price: 89.99
                  stock: 100
                  category: "Electronics"
                  tags: ["mechanical", "keyboard", "rgb"]
      responses:
        '201':
          description: Product created successfully
          headers:
            Location:
              description: URL of the created product
              schema:
                type: string
                example: "/v2/products/550e8400-e29b-41d4-a716-446655440000"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
        '400':
          description: Invalid input
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '401':
          description: Unauthorized (admin key required)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /products/{product_id}:
    get:
      summary: Get product by ID
      description: Retrieve details of a single product
      operationId: getProduct
      tags:
        - Products
      security:
        - ApiKeyAuth: []
      parameters:
        - name: product_id
          in: path
          description: Product UUID
          required: true
          schema:
            type: string
            format: uuid
            example: "550e8400-e29b-41d4-a716-446655440000"
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
        '404':
          description: Product not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
              examples:
                not_found:
                  value:
                    error: "resource_not_found"
                    message: "Product with ID '550e8400-e29b-41d4-a716-446655440000' not found"
                    request_id: "req_notfound123"

  /orders:
    post:
      summary: Create order
      description: |
        Place a new order. Requires authenticated user (JWT token).

        ## Workflow
        1. Validate items (check stock availability)
        2. Calculate total (price * quantity for each item)
        3. Process payment (via webhook callback)
        4. Create order record
        5. Send confirmation email
      operationId: createOrder
      tags:
        - Orders
      security:
        - BearerAuth: []
      requestBody:
        description: Order data
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - items
              properties:
                items:
                  type: array
                  items:
                    type: object
                    required:
                      - product_id
                      - quantity
                    properties:
                      product_id:
                        type: string
                        format: uuid
                      quantity:
                        type: integer
                        minimum: 1
                  minItems: 1
            examples:
              simple_order:
                summary: Order with 2 items
                value:
                  items:
                    - product_id: "550e8400-e29b-41d4-a716-446655440000"
                      quantity: 2
                    - product_id: "f47ac10b-58cc-4372-a567-0e02b2c3d479"
                      quantity: 1
      responses:
        '201':
          description: Order created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
        '400':
          description: Invalid order data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '409':
          description: Insufficient stock
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
              examples:
                out_of_stock:
                  value:
                    error: "insufficient_stock"
                    message: "Product '550e8400-e29b-41d4-a716-446655440000' has only 1 item in stock, but 2 requested"
                    details:
                      product_id: "550e8400-e29b-41d4-a716-446655440000"
                      available: 1
                      requested: 2
                    request_id: "req_stock_err"
```

---

## Code Examples (Multi-Language)

### Python SDK

```python
# ecommerce_api/__init__.py

import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Product:
    """
    Represents a product in the catalog.

    Attributes:
        id: Unique product identifier (UUID)
        name: Product display name
        description: Detailed product description
        price: Price in USD
        stock: Current inventory count
        category: Product category
        tags: List of searchable tags
        image_url: URL to product image
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    name: str
    description: str
    price: float
    stock: int
    category: str
    tags: List[str]
    image_url: str
    created_at: datetime
    updated_at: datetime

class ECommerceAPI:
    """
    Python client for E-Commerce API.

    Usage:
        >>> from ecommerce_api import ECommerceAPI
        >>> client = ECommerceAPI(api_key="sk_live_abc123...")
        >>> products = client.list_products(category="Electronics")
        >>> print(f"Found {len(products)} products")
    """

    BASE_URL = "https://api.example.com/v2"

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        Initialize API client.

        Args:
            api_key: Your API key (get from https://dashboard.example.com/api-keys)
            base_url: Optional custom base URL (for sandbox/local testing)

        Example:
            >>> client = ECommerceAPI(api_key="sk_test_xyz789...",
            ...                        base_url="https://sandbox-api.example.com/v2")
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": "ecommerce-python-sdk/2.1.0"
        })

    def list_products(
        self,
        page: int = 1,
        per_page: int = 50,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None
    ) -> List[Product]:
        """
        List products with optional filtering.

        Args:
            page: Page number (starts at 1)
            per_page: Items per page (max 100)
            category: Filter by category
            min_price: Minimum price filter
            max_price: Maximum price filter
            search: Full-text search query

        Returns:
            List of Product objects

        Raises:
            APIError: If request fails (4xx/5xx status)

        Examples:
            >>> # List all products
            >>> products = client.list_products()

            >>> # Filter by category and price range
            >>> headphones = client.list_products(
            ...     category="Electronics",
            ...     min_price=100.00,
            ...     max_price=200.00
            ... )

            >>> # Search for products
            >>> results = client.list_products(search="wireless headphones")
        """
        params = {
            "page": page,
            "per_page": per_page
        }

        if category:
            params["category"] = category
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if search:
            params["search"] = search

        response = self.session.get(
            f"{self.base_url}/products",
            params=params
        )

        if response.status_code != 200:
            raise APIError(response)

        data = response.json()
        return [Product(**item) for item in data["data"]]

    def get_product(self, product_id: str) -> Product:
        """
        Get product by ID.

        Args:
            product_id: Product UUID

        Returns:
            Product object

        Raises:
            NotFoundError: If product doesn't exist

        Example:
            >>> product = client.get_product("550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"{product.name}: ${product.price}")
        """
        response = self.session.get(f"{self.base_url}/products/{product_id}")

        if response.status_code == 404:
            raise NotFoundError(f"Product {product_id} not found")
        elif response.status_code != 200:
            raise APIError(response)

        return Product(**response.json())

    def create_product(
        self,
        name: str,
        price: float,
        description: str = "",
        stock: int = 0,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Product:
        """
        Create a new product (requires admin API key).

        Args:
            name: Product name (1-200 characters)
            price: Price in USD (must be ≥ 0)
            description: Product description (max 2000 characters)
            stock: Initial stock count (default: 0)
            category: Product category
            tags: List of tags

        Returns:
            Created Product object

        Raises:
            ValidationError: If input validation fails
            UnauthorizedError: If API key lacks admin permissions

        Example:
            >>> product = client.create_product(
            ...     name="Mechanical Keyboard",
            ...     price=89.99,
            ...     description="RGB backlit mechanical keyboard",
            ...     stock=100,
            ...     category="Electronics",
            ...     tags=["mechanical", "keyboard", "rgb"]
            ... )
            >>> print(f"Created product {product.id}")
        """
        payload = {
            "name": name,
            "price": price,
            "description": description,
            "stock": stock
        }

        if category:
            payload["category"] = category
        if tags:
            payload["tags"] = tags

        response = self.session.post(
            f"{self.base_url}/products",
            json=payload
        )

        if response.status_code == 400:
            raise ValidationError(response.json())
        elif response.status_code == 401:
            raise UnauthorizedError("Admin API key required")
        elif response.status_code != 201:
            raise APIError(response)

        return Product(**response.json())

class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, response: requests.Response):
        self.status_code = response.status_code
        self.response = response
        try:
            self.error_data = response.json()
            message = self.error_data.get("message", response.text)
        except:
            message = response.text
        super().__init__(f"API Error {self.status_code}: {message}")

class NotFoundError(APIError):
    """Raised when resource is not found (404)."""
    pass

class ValidationError(APIError):
    """Raised when input validation fails (400)."""
    pass

class UnauthorizedError(APIError):
    """Raised when authentication fails (401)."""
    pass
```

---

## Key Takeaways

1. **OpenAPI spec first** — Auto-generate docs from spec
2. **Examples everywhere** — Every endpoint needs request/response example
3. **Multi-language SDKs** — Provide Python, Node.js, Go, Ruby clients
4. **Interactive docs** — Swagger UI for try-it-out experience
5. **Versioning** — Semantic versioning + migration guides

**API Documentation Formula:**
```
OpenAPI Spec → Auto-Generate Docs → Add Examples → SDK Code → Interactive Playground
```

**Tools:** Swagger UI, Redoc, Postman, OpenAPI Generator, Stoplight
