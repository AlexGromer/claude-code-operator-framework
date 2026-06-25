# Example: Error Debugging

**Task Type:** Debug runtime error
**Complexity:** Medium
**Model:** Sonnet

---

## User Request

> Getting this error when running my Flask app:
>
> ```
> TypeError: 'NoneType' object is not subscriptable
> File "app.py", line 45, in process_order
>   total = cart['items'][0]['price'] * quantity
> ```

---

## Claude's Reasoning Process

### 1. Error Analysis
- **Error Type:** TypeError
- **Root Cause:** Attempting to subscript `None` (likely `cart` is None)
- **Location:** `app.py:45` in `process_order` function

### 2. Probable Causes
1. `cart` is None → database query returned no result
2. `cart['items']` is empty list → index out of range
3. Function called before cart initialized

### 3. Debugging Strategy
- Add defensive checks
- Log intermediate values
- Handle edge cases

---

## Claude's Response

This error indicates that `cart` is `None` when you try to access `cart['items']`. Here's how to fix it:

### Root Cause

The `cart` variable is likely `None` because:
- Database query returned no results
- Session/user has no cart
- Cart was deleted/expired

### Quick Fix (Defensive Programming)

```python
def process_order(user_id, quantity):
    cart = get_user_cart(user_id)  # Returns None if cart doesn't exist

    # Fix: Check if cart exists
    if cart is None:
        logger.warning(f"No cart found for user {user_id}")
        return {"error": "Cart not found"}, 404

    # Fix: Check if items exist
    if not cart.get('items') or len(cart['items']) == 0:
        logger.warning(f"Empty cart for user {user_id}")
        return {"error": "Cart is empty"}, 400

    # Fix: Safe access with validation
    first_item = cart['items'][0]
    if 'price' not in first_item:
        logger.error(f"Invalid item structure: {first_item}")
        return {"error": "Invalid cart data"}, 500

    total = first_item['price'] * quantity

    return {"total": total}, 200
```

### Better: Use Optional Type Hints

```python
from typing import Optional, Dict, List

def process_order(user_id: int, quantity: int) -> tuple[Dict, int]:
    cart: Optional[Dict] = get_user_cart(user_id)

    if cart is None:
        return {"error": "Cart not found"}, 404

    items: List[Dict] = cart.get('items', [])
    if not items:
        return {"error": "Cart is empty"}, 400

    first_item = items[0]
    price = first_item.get('price')

    if price is None:
        return {"error": "Invalid item data"}, 500

    total = price * quantity
    return {"total": total}, 200
```

### Debug Checklist

1. **Add Logging:**
   ```python
   logger.debug(f"Cart data: {cart}")
   logger.debug(f"Items: {cart.get('items') if cart else None}")
   ```

2. **Verify Database:**
   ```python
   # Check if cart exists in DB
   cart_exists = db.query(Cart).filter_by(user_id=user_id).count() > 0
   ```

3. **Test Edge Cases:**
   - User with no cart
   - Empty cart
   - Cart with invalid item structure

### Prevention (Unit Tests)

```python
def test_process_order_no_cart():
    result, status = process_order(user_id=999, quantity=1)
    assert status == 404
    assert "Cart not found" in result['error']

def test_process_order_empty_cart():
    # Mock empty cart
    result, status = process_order(user_id=1, quantity=1)
    assert status == 400
    assert "Cart is empty" in result['error']
```

---

## Key Takeaways

**This example demonstrates:**

1. **Error Interpretation** — Identify root cause from stack trace
2. **Defensive Coding** — Check for None/empty before access
3. **Type Hints** — Use Optional to signal nullable values
4. **Logging** — Add debug statements for troubleshooting
5. **Testing** — Prevent regression with edge case tests

**Complexity Routing:** Medium → **Sonnet**
