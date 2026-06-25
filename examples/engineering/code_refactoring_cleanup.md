# Example: Code Refactoring

**Task Type:** Refactor for readability and maintainability
**Complexity:** Complex
**Model:** Opus (architecture decisions)

---

## User Request

> Refactor this function — it works but is hard to understand:
>
> ```python
> def p(d, u):
>     r = []
>     for i in d:
>         if i['u'] == u and i['s'] == 'a' and i['p'] > 0:
>             r.append({'n': i['n'], 't': i['p'] * i['q']})
>     r.sort(key=lambda x: x['t'], reverse=True)
>     return r[:5]
> ```

---

## Claude's Reasoning Process

### 1. Code Analysis
- **Problem:** Cryptic variable names, unclear logic
- **Purpose:** (inferred) Filter and sort data by user, select top 5
- **Context Needed:** What are `d`, `u`, `i`, `s`, `a`, `p`, `n`, `q`?

### 2. Reverse Engineering Logic
```
1. Iterate over data (d)
2. Filter by: user (u), status ('a' = active?), positive price (p > 0)
3. Calculate total (price * quantity)
4. Sort by total descending
5. Return top 5
```

### 3. Refactoring Strategy
- **Descriptive names** → clarity
- **Extract logic** → functions
- **Type hints** → documentation
- **Comments** → explain "why"

---

## Claude's Response

### Refactored Version

I've refactored this into clean, self-documenting code:

```python
from typing import List, Dict

def get_top_active_purchases_for_user(
    purchases: List[Dict],
    user_id: int,
    limit: int = 5
) -> List[Dict]:
    """
    Get top N active purchases for a user, sorted by total value.

    Args:
        purchases: List of purchase records
        user_id: ID of the user to filter by
        limit: Maximum number of results (default: 5)

    Returns:
        List of dicts with 'product_name' and 'total_value' keys,
        sorted by total_value descending
    """
    # Filter: user's active purchases with positive price
    active_user_purchases = [
        purchase for purchase in purchases
        if (
            purchase['user_id'] == user_id and
            purchase['status'] == 'active' and
            purchase['price'] > 0
        )
    ]

    # Transform: calculate total value and extract relevant fields
    purchases_with_totals = [
        {
            'product_name': purchase['name'],
            'total_value': purchase['price'] * purchase['quantity']
        }
        for purchase in active_user_purchases
    ]

    # Sort by total value descending
    sorted_purchases = sorted(
        purchases_with_totals,
        key=lambda p: p['total_value'],
        reverse=True
    )

    # Return top N
    return sorted_purchases[:limit]
```

### Key Improvements

1. **Descriptive Function Name**
   - Before: `p(d, u)`
   - After: `get_top_active_purchases_for_user(purchases, user_id)`

2. **Clear Variable Names**
   - `d` → `purchases`
   - `u` → `user_id`
   - `i` → `purchase`
   - `s` → `status`
   - `p` → `price`
   - `n` → `name` (product_name)
   - `q` → `quantity`

3. **Type Hints**
   - Adds IDE autocomplete support
   - Catches type errors early
   - Self-documenting API

4. **Docstring**
   - Explains purpose, parameters, return value
   - Example usage clear without reading code

5. **Readable Logic**
   - Separate steps (filter → transform → sort → limit)
   - Each step has clear purpose
   - Can be debugged/tested independently

### Alternative: Functional Approach

For large datasets, use generator expressions:

```python
from typing import Iterator, Dict
from itertools import islice

def get_top_active_purchases_for_user(
    purchases: List[Dict],
    user_id: int,
    limit: int = 5
) -> List[Dict]:
    """Get top N active purchases (functional style, memory-efficient)."""

    # Generator: filter and transform in one pass
    active_purchases = (
        {
            'product_name': p['name'],
            'total_value': p['price'] * p['quantity']
        }
        for p in purchases
        if p['user_id'] == user_id and p['status'] == 'active' and p['price'] > 0
    )

    # Sort and take top N
    return list(islice(
        sorted(active_purchases, key=lambda x: x['total_value'], reverse=True),
        limit
    ))
```

### Testing

```python
def test_get_top_active_purchases():
    purchases = [
        {'user_id': 1, 'name': 'Product A', 'price': 10, 'quantity': 2, 'status': 'active'},
        {'user_id': 1, 'name': 'Product B', 'price': 5, 'quantity': 10, 'status': 'active'},
        {'user_id': 1, 'name': 'Product C', 'price': 20, 'quantity': 1, 'status': 'pending'},
        {'user_id': 2, 'name': 'Product D', 'price': 100, 'quantity': 1, 'status': 'active'},
    ]

    result = get_top_active_purchases_for_user(purchases, user_id=1, limit=2)

    assert len(result) == 2
    assert result[0]['product_name'] == 'Product B'  # 5 * 10 = 50
    assert result[0]['total_value'] == 50
    assert result[1]['product_name'] == 'Product A'  # 10 * 2 = 20
    assert result[1]['total_value'] == 20
```

---

## Key Takeaways

**This example demonstrates:**

1. **Reverse Engineering** — Infer logic from cryptic code
2. **Progressive Refactoring** — Clear steps (filter → transform → sort)
3. **Multiple Approaches** — Show alternatives (imperative vs functional)
4. **Type Safety** — Add type hints for clarity
5. **Testing** — Validate behavior doesn't change

**Complexity Routing:** Complex (architecture decision) → **Opus**
