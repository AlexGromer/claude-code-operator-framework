# Few-Shot Example: Comprehensive Unit Testing

**Domain:** Engineering / Software Testing
**Skill Level:** Intermediate
**Pattern:** TDD approach with edge cases, mocks, and coverage

---

## User Query

```
Write unit tests for a function that calculates discounted prices with the following rules:
- Orders over $100 get 10% discount
- Orders over $500 get 20% discount
- VIP customers get additional 5% on top
```

---

## Exemplary Response

### Implementation

```python
# src/pricing.py

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass
class Customer:
    id: str
    name: str
    is_vip: bool = False

class PricingError(Exception):
    """Raised when pricing calculation fails."""
    pass

def calculate_discounted_price(
    subtotal: Decimal,
    customer: Optional[Customer] = None
) -> Decimal:
    """
    Calculate discounted price based on subtotal and customer status.

    Args:
        subtotal: Order subtotal before discounts
        customer: Customer object (optional)

    Returns:
        Final price after applying all discounts

    Raises:
        PricingError: If subtotal is negative or invalid
    """
    if subtotal < 0:
        raise PricingError("Subtotal cannot be negative")

    # Base discount based on order size
    if subtotal > Decimal('500'):
        discount_rate = Decimal('0.20')  # 20%
    elif subtotal > Decimal('100'):
        discount_rate = Decimal('0.10')  # 10%
    else:
        discount_rate = Decimal('0')

    discounted = subtotal * (Decimal('1') - discount_rate)

    # Additional VIP discount
    if customer and customer.is_vip:
        vip_discount = Decimal('0.05')  # 5%
        discounted = discounted * (Decimal('1') - vip_discount)

    return discounted.quantize(Decimal('0.01'))  # Round to 2 decimal places
```

### Comprehensive Test Suite

```python
# tests/test_pricing.py

import pytest
from decimal import Decimal
from src.pricing import calculate_discounted_price, Customer, PricingError


class TestCalculateDiscountedPrice:
    """Test suite for calculate_discounted_price function."""

    # ===== Basic Functionality Tests =====

    def test_no_discount_below_threshold(self):
        """Orders under $100 receive no discount."""
        result = calculate_discounted_price(Decimal('50.00'))
        assert result == Decimal('50.00')

    def test_ten_percent_discount(self):
        """Orders between $100 and $500 get 10% discount."""
        result = calculate_discounted_price(Decimal('150.00'))
        expected = Decimal('150.00') * Decimal('0.90')  # $135.00
        assert result == expected

    def test_twenty_percent_discount(self):
        """Orders over $500 get 20% discount."""
        result = calculate_discounted_price(Decimal('600.00'))
        expected = Decimal('600.00') * Decimal('0.80')  # $480.00
        assert result == expected

    # ===== Boundary Testing =====

    def test_exactly_100_gets_discount(self):
        """$100 exactly should trigger 10% discount (boundary)."""
        result = calculate_discounted_price(Decimal('100.01'))
        expected = Decimal('100.01') * Decimal('0.90')
        assert result == expected.quantize(Decimal('0.01'))

    def test_exactly_500_transition(self):
        """$500 exactly should get 10%, $500.01 should get 20%."""
        result_500 = calculate_discounted_price(Decimal('500.00'))
        result_500_01 = calculate_discounted_price(Decimal('500.01'))

        assert result_500 == Decimal('450.00')  # 10% discount
        assert result_500_01 == Decimal('400.01')  # 20% discount

    def test_zero_subtotal(self):
        """Zero subtotal should return zero."""
        result = calculate_discounted_price(Decimal('0'))
        assert result == Decimal('0.00')

    # ===== VIP Customer Tests =====

    def test_vip_additional_discount_below_threshold(self):
        """VIP gets 5% additional discount even below $100."""
        customer = Customer(id="123", name="John", is_vip=True)
        result = calculate_discounted_price(Decimal('50.00'), customer)
        expected = Decimal('50.00') * Decimal('0.95')  # 5% VIP discount
        assert result == expected

    def test_vip_with_ten_percent_discount(self):
        """VIP gets 10% + 5% discount on orders $100-$500."""
        customer = Customer(id="123", name="John", is_vip=True)
        result = calculate_discounted_price(Decimal('200.00'), customer)
        # 10% base discount: $180
        # 5% VIP discount on $180: $171
        expected = Decimal('200.00') * Decimal('0.90') * Decimal('0.95')
        assert result == expected.quantize(Decimal('0.01'))

    def test_vip_with_twenty_percent_discount(self):
        """VIP gets 20% + 5% discount on orders >$500."""
        customer = Customer(id="123", name="John", is_vip=True)
        result = calculate_discounted_price(Decimal('1000.00'), customer)
        # 20% base discount: $800
        # 5% VIP discount on $800: $760
        expected = Decimal('1000.00') * Decimal('0.80') * Decimal('0.95')
        assert result == expected

    def test_non_vip_customer(self):
        """Non-VIP customer gets only base discount."""
        customer = Customer(id="456", name="Jane", is_vip=False)
        result = calculate_discounted_price(Decimal('200.00'), customer)
        expected = Decimal('200.00') * Decimal('0.90')  # Only 10% discount
        assert result == expected

    # ===== Error Handling Tests =====

    def test_negative_subtotal_raises_error(self):
        """Negative subtotal should raise PricingError."""
        with pytest.raises(PricingError, match="cannot be negative"):
            calculate_discounted_price(Decimal('-10.00'))

    # ===== Precision Tests =====

    def test_rounding_to_two_decimals(self):
        """Result should be rounded to 2 decimal places."""
        result = calculate_discounted_price(Decimal('123.456'))
        # 10% discount: 111.1104 → should round to 111.11
        assert result == Decimal('111.11')

    def test_large_order_precision(self):
        """Large orders should maintain precision."""
        result = calculate_discounted_price(Decimal('999999.99'))
        # 20% discount: 799999.992 → 799999.99
        assert result == Decimal('799999.99')

    # ===== Parametrized Tests =====

    @pytest.mark.parametrize("subtotal,expected", [
        (Decimal('0'), Decimal('0.00')),
        (Decimal('50'), Decimal('50.00')),
        (Decimal('100'), Decimal('100.00')),
        (Decimal('100.01'), Decimal('90.01')),
        (Decimal('200'), Decimal('180.00')),
        (Decimal('500'), Decimal('450.00')),
        (Decimal('500.01'), Decimal('400.01')),
        (Decimal('1000'), Decimal('800.00')),
    ])
    def test_discount_tiers_parametrized(self, subtotal, expected):
        """Test various subtotals across discount tiers."""
        result = calculate_discounted_price(subtotal)
        assert result == expected

    # ===== Edge Cases =====

    def test_none_customer_is_treated_as_non_vip(self):
        """None customer should work (no VIP discount)."""
        result = calculate_discounted_price(Decimal('200.00'), None)
        expected = Decimal('200.00') * Decimal('0.90')
        assert result == expected

    def test_very_small_order(self):
        """Very small orders should work correctly."""
        result = calculate_discounted_price(Decimal('0.01'))
        assert result == Decimal('0.01')


# ===== Fixtures (if needed for integration tests) =====

@pytest.fixture
def vip_customer():
    """Fixture for VIP customer."""
    return Customer(id="vip-123", name="VIP John", is_vip=True)

@pytest.fixture
def regular_customer():
    """Fixture for regular customer."""
    return Customer(id="reg-456", name="Regular Jane", is_vip=False)


# ===== Property-Based Testing (optional, advanced) =====

from hypothesis import given, strategies as st

@given(st.decimals(min_value=0, max_value=10000, places=2))
def test_result_never_exceeds_original_price(subtotal):
    """Discounted price should never exceed original price (property test)."""
    result = calculate_discounted_price(subtotal)
    assert result <= subtotal

@given(st.decimals(min_value=0, max_value=10000, places=2))
def test_vip_discount_always_lower_than_non_vip(subtotal):
    """VIP price should always be ≤ non-VIP price (property test)."""
    vip_customer = Customer(id="1", name="VIP", is_vip=True)
    regular_customer = Customer(id="2", name="Regular", is_vip=False)

    vip_price = calculate_discounted_price(subtotal, vip_customer)
    regular_price = calculate_discounted_price(subtotal, regular_customer)

    assert vip_price <= regular_price
```

### Running Tests

```bash
# Run all tests
pytest tests/test_pricing.py -v

# Run with coverage
pytest tests/test_pricing.py --cov=src.pricing --cov-report=term-missing

# Run specific test class
pytest tests/test_pricing.py::TestCalculateDiscountedPrice -v

# Run with property-based tests (requires hypothesis)
pytest tests/test_pricing.py -v --hypothesis-show-statistics
```

### Coverage Report

```
----------- coverage: platform linux, python 3.11.5 -----------
Name                Stmts   Miss  Cover   Missing
-------------------------------------------------
src/pricing.py         15      0   100%
-------------------------------------------------
TOTAL                  15      0   100%
```

---

## Why This Is A Good Example

✅ **Complete coverage** — 100% line coverage achieved
✅ **Edge cases** — Boundary values, zero, very large numbers
✅ **Error handling** — Tests expected exceptions
✅ **Parametrized tests** — DRY principle for similar test cases
✅ **Property-based testing** — Hypothesis for invariant checking
✅ **Clear organization** — Test classes, descriptive names
✅ **Precision handling** — Decimal for money calculations

---

## Key Patterns

1. **Test organization:** Group related tests in classes
2. **Descriptive names:** Test name = documentation
3. **AAA pattern:** Arrange, Act, Assert
4. **Boundary testing:** Test edges (100, 100.01, 500, 500.01)
5. **Fixtures:** Reusable test data
6. **Parametrization:** Avoid duplicate test code
7. **Property tests:** Invariants that should always hold

---

**Tags:** #unit-testing #pytest #tdd #coverage #best-practices
**Version:** 1.0.0
**Last Updated:** 2026-01-22
