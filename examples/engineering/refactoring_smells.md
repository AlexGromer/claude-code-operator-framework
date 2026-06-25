# Few-Shot Example: Code Refactoring - Identifying & Fixing Code Smells

**Domain:** Engineering / Code Quality
**Skill Level:** Intermediate
**Pattern:** Identify smell → Explain problem → Refactor → Verify

---

## User Query

```
This code works but feels messy. Can you refactor it?

def process_order(order_id, user_id, items, payment_method, shipping_address):
    # Get user
    conn = psycopg2.connect("dbname=shop user=admin password=secret123")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {user_id}")
    user = cur.fetchone()

    # Calculate total
    total = 0
    for item in items:
        if item['type'] == 'book':
            if item['price'] > 50:
                total += item['price'] * 0.9
            else:
                total += item['price']
        elif item['type'] == 'electronics':
            if item['price'] > 100:
                total += item['price'] * 0.85
            else:
                total += item['price'] * 0.95
        else:
            total += item['price']

    # Process payment
    if payment_method == 'credit_card':
        # charge credit card
        print("Charging credit card...")
    elif payment_method == 'paypal':
        # charge paypal
        print("Charging PayPal...")

    # Save order
    cur.execute(f"INSERT INTO orders (user_id, total) VALUES ({user_id}, {total})")
    conn.commit()

    # Send email
    print(f"Sending email to {user[2]}")

    conn.close()
    return total
```

---

## Exemplary Response

### Identified Code Smells

#### 🚨 Critical Issues:
1. **SQL Injection** (CWE-89) — Using f-strings with user input
2. **Hardcoded credentials** — Password in source code
3. **Missing input validation** — No validation of parameters
4. **No error handling** — Database/network failures unhandled

#### ⚠️ Design Issues:
5. **Long method** — Violates Single Responsibility Principle
6. **Magic numbers** — Discount rates hardcoded without explanation
7. **Primitive obsession** — Using dicts instead of domain objects
8. **Duplicate logic** — Discount calculation repeated
9. **Poor separation of concerns** — DB, business logic, I/O mixed

---

### Refactored Solution

#### Step 1: Domain Models

```python
# models.py
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List

class ItemType(Enum):
    """Item type enumeration."""
    BOOK = "book"
    ELECTRONICS = "electronics"
    OTHER = "other"

class PaymentMethod(Enum):
    """Payment method enumeration."""
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"

@dataclass
class User:
    """User domain model."""
    id: int
    name: str
    email: str

@dataclass
class OrderItem:
    """Order item domain model."""
    product_id: int
    name: str
    type: ItemType
    price: Decimal
    quantity: int = 1

    def calculate_subtotal(self) -> Decimal:
        """Calculate item subtotal before discounts."""
        return self.price * self.quantity

@dataclass
class ShippingAddress:
    """Shipping address domain model."""
    street: str
    city: str
    country: str
    postal_code: str

@dataclass
class Order:
    """Order aggregate root."""
    id: int
    user_id: int
    items: List[OrderItem]
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    payment_method: PaymentMethod
    shipping_address: ShippingAddress
```

#### Step 2: Pricing Service (Business Logic)

```python
# services/pricing.py
from decimal import Decimal
from typing import List
from models import OrderItem, ItemType

class DiscountPolicy:
    """Discount calculation strategy."""

    # Discount tiers (documented!)
    BOOK_DISCOUNT_THRESHOLD = Decimal('50.00')
    BOOK_DISCOUNT_RATE = Decimal('0.10')  # 10% off

    ELECTRONICS_HIGH_THRESHOLD = Decimal('100.00')
    ELECTRONICS_HIGH_DISCOUNT = Decimal('0.15')  # 15% off
    ELECTRONICS_LOW_DISCOUNT = Decimal('0.05')   # 5% off

    @classmethod
    def calculate_item_discount(cls, item: OrderItem) -> Decimal:
        """
        Calculate discount for a single item.

        Returns:
            Discount amount (not rate)
        """
        subtotal = item.calculate_subtotal()

        if item.type == ItemType.BOOK:
            if subtotal >= cls.BOOK_DISCOUNT_THRESHOLD:
                return subtotal * cls.BOOK_DISCOUNT_RATE
            return Decimal('0')

        elif item.type == ItemType.ELECTRONICS:
            if subtotal >= cls.ELECTRONICS_HIGH_THRESHOLD:
                return subtotal * cls.ELECTRONICS_HIGH_DISCOUNT
            else:
                return subtotal * cls.ELECTRONICS_LOW_DISCOUNT

        else:
            return Decimal('0')  # No discount for other items


class PricingService:
    """Service for order pricing calculations."""

    def __init__(self, discount_policy: DiscountPolicy):
        self.discount_policy = discount_policy

    def calculate_order_total(self, items: List[OrderItem]) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate order totals.

        Returns:
            Tuple of (subtotal, total_discount, final_total)
        """
        subtotal = sum(item.calculate_subtotal() for item in items)
        total_discount = sum(
            self.discount_policy.calculate_item_discount(item)
            for item in items
        )
        final_total = subtotal - total_discount

        return subtotal, total_discount, final_total
```

#### Step 3: Repository (Data Access)

```python
# repositories/order_repository.py
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from models import User, Order
from config import DATABASE_URL  # From environment variable

class UserRepository:
    """Repository for user data access."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found

        Raises:
            psycopg2.Error: Database error
        """
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # ✅ Using parameterized query (no SQL injection)
                cur.execute(
                    "SELECT id, name, email FROM users WHERE id = %s",
                    (user_id,)
                )
                row = cur.fetchone()

                if row:
                    return User(**row)
                return None


class OrderRepository:
    """Repository for order data access."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def save(self, order: Order) -> int:
        """
        Save order to database.

        Args:
            order: Order to save

        Returns:
            Order ID

        Raises:
            psycopg2.Error: Database error
        """
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                # ✅ Parameterized query
                cur.execute(
                    """
                    INSERT INTO orders
                        (user_id, subtotal, discount, total, payment_method, shipping_address)
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        order.user_id,
                        order.subtotal,
                        order.discount,
                        order.total,
                        order.payment_method.value,
                        order.shipping_address.street  # Simplified
                    )
                )
                order_id = cur.fetchone()[0]
                conn.commit()
                return order_id
```

#### Step 4: Payment Service

```python
# services/payment.py
from abc import ABC, abstractmethod
from decimal import Decimal
from models import PaymentMethod

class PaymentProcessor(ABC):
    """Abstract payment processor."""

    @abstractmethod
    def charge(self, amount: Decimal, user_id: int) -> str:
        """Charge payment and return transaction ID."""
        pass


class CreditCardProcessor(PaymentProcessor):
    """Credit card payment processor."""

    def charge(self, amount: Decimal, user_id: int) -> str:
        # Integration with payment gateway
        print(f"Charging credit card: ${amount}")
        return "cc_txn_12345"


class PayPalProcessor(PaymentProcessor):
    """PayPal payment processor."""

    def charge(self, amount: Decimal, user_id: int) -> str:
        # Integration with PayPal API
        print(f"Charging PayPal: ${amount}")
        return "pp_txn_67890"


class PaymentService:
    """Service for payment processing."""

    def __init__(self):
        self._processors = {
            PaymentMethod.CREDIT_CARD: CreditCardProcessor(),
            PaymentMethod.PAYPAL: PayPalProcessor(),
        }

    def process_payment(
        self,
        amount: Decimal,
        payment_method: PaymentMethod,
        user_id: int
    ) -> str:
        """
        Process payment.

        Args:
            amount: Amount to charge
            payment_method: Payment method
            user_id: User ID

        Returns:
            Transaction ID

        Raises:
            ValueError: Invalid payment method
        """
        processor = self._processors.get(payment_method)
        if not processor:
            raise ValueError(f"Unsupported payment method: {payment_method}")

        return processor.charge(amount, user_id)
```

#### Step 5: Notification Service

```python
# services/notification.py
from models import User, Order

class EmailService:
    """Service for email notifications."""

    def send_order_confirmation(self, user: User, order: Order) -> None:
        """
        Send order confirmation email.

        Args:
            user: User to email
            order: Confirmed order
        """
        subject = f"Order #{order.id} Confirmed"
        body = f"""
        Hello {user.name},

        Your order has been confirmed!

        Order ID: {order.id}
        Total: ${order.total}

        Thank you for your purchase!
        """

        # Email sending logic (SMTP, SendGrid, etc.)
        print(f"Sending email to {user.email}: {subject}")
```

#### Step 6: Orchestration (Application Service)

```python
# services/order_service.py
from typing import List
from decimal import Decimal
from models import Order, OrderItem, PaymentMethod, ShippingAddress
from repositories.order_repository import UserRepository, OrderRepository
from services.pricing import PricingService, DiscountPolicy
from services.payment import PaymentService
from services.notification import EmailService

class OrderProcessingError(Exception):
    """Raised when order processing fails."""
    pass


class OrderService:
    """Application service for order processing."""

    def __init__(
        self,
        user_repo: UserRepository,
        order_repo: OrderRepository,
        pricing_service: PricingService,
        payment_service: PaymentService,
        email_service: EmailService
    ):
        self.user_repo = user_repo
        self.order_repo = order_repo
        self.pricing_service = pricing_service
        self.payment_service = payment_service
        self.email_service = email_service

    def process_order(
        self,
        user_id: int,
        items: List[OrderItem],
        payment_method: PaymentMethod,
        shipping_address: ShippingAddress
    ) -> Order:
        """
        Process complete order workflow.

        Args:
            user_id: User ID
            items: List of order items
            payment_method: Payment method
            shipping_address: Shipping address

        Returns:
            Processed order

        Raises:
            OrderProcessingError: If order processing fails
        """
        try:
            # 1. Validate user exists
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise OrderProcessingError(f"User {user_id} not found")

            # 2. Calculate pricing
            subtotal, discount, total = self.pricing_service.calculate_order_total(items)

            # 3. Process payment
            transaction_id = self.payment_service.process_payment(
                amount=total,
                payment_method=payment_method,
                user_id=user_id
            )

            # 4. Create and save order
            order = Order(
                id=0,  # Will be set by database
                user_id=user_id,
                items=items,
                subtotal=subtotal,
                discount=discount,
                total=total,
                payment_method=payment_method,
                shipping_address=shipping_address
            )
            order.id = self.order_repo.save(order)

            # 5. Send confirmation
            self.email_service.send_order_confirmation(user, order)

            return order

        except Exception as e:
            raise OrderProcessingError(f"Order processing failed: {e}") from e
```

---

### Verification: Before vs After

```python
# tests/test_order_service.py
import pytest
from decimal import Decimal
from models import OrderItem, ItemType, PaymentMethod, ShippingAddress
from services.order_service import OrderService

def test_order_processing_end_to_end(order_service):
    """End-to-end test of order processing."""
    items = [
        OrderItem(
            product_id=1,
            name="Python Book",
            type=ItemType.BOOK,
            price=Decimal('60.00'),
            quantity=1
        ),
        OrderItem(
            product_id=2,
            name="Laptop",
            type=ItemType.ELECTRONICS,
            price=Decimal('150.00'),
            quantity=1
        )
    ]

    shipping_address = ShippingAddress(
        street="123 Main St",
        city="City",
        country="US",
        postal_code="12345"
    )

    order = order_service.process_order(
        user_id=1,
        items=items,
        payment_method=PaymentMethod.CREDIT_CARD,
        shipping_address=shipping_address
    )

    # Book: $60 - $6 (10% discount) = $54
    # Laptop: $150 - $7.50 (5% discount) = $142.50
    # Total: $196.50
    assert order.total == Decimal('196.50')
```

---

## Why This Is A Good Example

✅ **Identifies specific code smells** — Explains WHY code is problematic
✅ **Security-first** — Fixes SQL injection + credential exposure
✅ **SOLID principles** — Single responsibility, dependency injection
✅ **Domain-driven design** — Rich domain models, not anemic POJOs
✅ **Testability** — Services depend on abstractions, easy to mock
✅ **Error handling** — Proper exception handling added
✅ **Maintainability** — Small, focused classes with clear responsibilities

---

## Key Patterns

1. **Extract Method** — Long methods → multiple focused methods
2. **Replace Primitive with Object** — Dicts → domain models
3. **Strategy Pattern** — Polymorphism for payment processors
4. **Repository Pattern** — Separate data access from business logic
5. **Service Layer** — Orchestrate business operations
6. **Dependency Injection** — Testable, flexible design

---

**Tags:** #refactoring #code-smells #clean-code #solid #design-patterns
**Version:** 1.0.0
**Last Updated:** 2026-01-22
