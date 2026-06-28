# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend

# Run all tests
python3 -m pytest tests/ -q

# Run a single test file
python3 -m pytest tests/test_cart_service.py -v

# Run a single test
python3 -m pytest tests/test_cart_service.py::TestAddItem::test_adds_new_item -v

# Start local dev server (port 5000)
python3 app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # dev server on port 3000, proxies /api → localhost:5000
npm run build    # production build to dist/
```

### Deploy

```bash
./deploy.sh   # SAM build + deploy + frontend sync to S3 (one command)
```

## Architecture

**Runtime path:** React (S3) → API Gateway → Lambda (Flask via serverless-wsgi) → DynamoDB

**Backend layers** (`backend/`):
- `routes/` — Thin Flask Blueprints: validate input, call service, return JSON. Never touch DynamoDB directly.
- `services/` — Business logic: cart totals, discount calculation, wishlist guards.
- `models/` — DynamoDB access only. Each model owns one table.
- `config.py` — Shared config read from env vars (e.g. `TAX_RATE`, defaults to `0.08`).
- `app.py` — Registers all Blueprints; global error handlers.
- `lambda_handler.py` — Adapts API Gateway events to WSGI for Flask.

**DynamoDB tables** (names injected as env vars at runtime):
| Env var | Key(s) | Notes |
|---|---|---|
| `PRODUCTS_TABLE` | `productId` (hash) | Auto-seeded on first request if empty |
| `CART_TABLE` | `sessionId` (hash) + `productId` (range) | Shared with wishlist via `listType` field |
| `ORDERS_TABLE` | `sessionId` (hash) + `orderId` (range) | |
| `DISCOUNTS_TABLE` | `code` (hash) | |

**Cart vs. Wishlist:** Both live in `CART_TABLE`. Items are distinguished by `listType: "cart"` or `listType: "wishlist"`. A product can only exist in one list at a time — the same `(sessionId, productId)` primary key means a DynamoDB `put_item` would silently overwrite the other. `WishlistService` guards against this.

**Tax calculation:** Tax base is the post-discount subtotal (discount first, then tax). Rate is `config.TAX_RATE` (env var `TAX_RATE`, default `0.08`). The same rate is used in `CartService`, `OrderService`, and `DiscountService.apply_to_cart`.

**Discount flow:**
1. `/api/discounts/validate` — validates code, returns `discountAmount` (subtotal fetched server-side, never trusted from client).
2. `/api/cart?code=X` — applies discount to cart response for display.
3. `/api/orders` (POST) — re-validates code at checkout time, then calls `discount_service.consume()` after order is saved and cart is cleared to atomically increment `usedCount`.

**Frontend state:** `CartContext` and `WishlistContext` (React Context + `useReducer`/`useState`) hold global state. All API calls go through `src/services/api.js`.

**Session identity:** `SESSION_ID = "workshop-user"` is hardcoded in every route file. In production, replace with a JWT sub or Cognito user ID.

## Test Patterns

Tests set required env vars before importing any module:

```python
import os
os.environ.setdefault("PRODUCTS_TABLE", "test-products")
os.environ.setdefault("CART_TABLE", "test-cart")
# ...then import services
```

DynamoDB is mocked via `patch("boto3.resource")` + `MagicMock`. Services are built with `_make_service()` helpers that wire in-memory fakes to the model layer — tests never hit real AWS.

## Code Style

### Python
- All functions must have a docstring.
- Use `snake_case` for all function names.
- Always add type hints to function parameters and return values.

## API Standards

- Errors always return `{"error": "human-readable message"}` with an appropriate 4xx/5xx status.
- List responses use `{"items": [...], "count": N}` shape.
- Route handlers are kept thin — validate, call service, return response.
