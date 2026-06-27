# Workshop Repo — Code Commit Report

**Repository:** `workshop-repo` (shopping-cart)
**Report Date:** 2026-06-27
**Branch:** `main`

---

## Commit History

| Hash | Author | Date | Message |
|------|--------|------|---------|
| `14e93e0` | Workshop Participant | 2026-06-26 | Initial commit |

**Total commits:** 1
**Files added:** 33
**Lines inserted:** 1,617

---

## Initial Commit Breakdown

The single initial commit introduced the complete shopping cart application across three layers:

### Backend (Python / Flask) — 16 files, ~453 lines

| File | Role |
|------|------|
| `backend/app.py` | Flask application entry point; registers three blueprints |
| `backend/lambda_handler.py` | Bridges API Gateway events to Flask via `serverless-wsgi` |
| `backend/requirements.txt` | Python deps: Flask 3.1, flask-cors, boto3 1.35, serverless-wsgi 3.0 |
| `backend/routes/products.py` | Product endpoints (list, detail, categories, search) |
| `backend/routes/cart.py` | Cart endpoints (get, add, update quantity, remove, clear) |
| `backend/routes/orders.py` | Order endpoints (place order / checkout, list, detail) |
| `backend/services/product_service.py` | DynamoDB product CRUD logic |
| `backend/services/cart_service.py` | DynamoDB cart CRUD + totals calculation |
| `backend/services/order_service.py` | DynamoDB order creation logic |
| `backend/models/product.py` | Product data model |
| `backend/models/cart.py` | Cart item data model |
| `backend/models/order.py` | Order data model |

### Frontend (React / Vite) — 11 source files, ~624 lines

| File | Role |
|------|------|
| `frontend/src/main.jsx` | React entry point |
| `frontend/src/App.jsx` | Root component with client-side routing |
| `frontend/src/styles.css` | Global stylesheet (~203 lines) |
| `frontend/src/context/CartContext.jsx` | Cart state via React Context API |
| `frontend/src/services/api.js` | Centralised HTTP client for all API calls |
| `frontend/src/pages/ProductList.jsx` | Product browsing with category filtering |
| `frontend/src/pages/CartPage.jsx` | Cart view with quantity controls and checkout |
| `frontend/src/pages/OrdersPage.jsx` | Order history display |
| `frontend/src/components/Header.jsx` | Navigation bar with cart badge |
| `frontend/src/components/ProductCard.jsx` | Product tile component |
| `frontend/src/components/CartItem.jsx` | Cart row with +/− quantity controls |
| `frontend/index.html` | HTML shell |
| `frontend/vite.config.js` | Vite config; proxies `/api` to `localhost:5000` in dev |
| `frontend/package.json` | Node deps: React 18, React Router, Vite |

### Infrastructure / Deployment — 4 files, ~233 lines

| File | Role |
|------|------|
| `template.yaml` | AWS SAM template: Lambda, API Gateway, 3 DynamoDB tables, S3 bucket |
| `deploy.sh` | One-command deploy: `sam build` → `sam deploy` → Vite build → S3 sync |
| `README.md` | Architecture diagram, project structure, API reference, dev guide |
| `docs/api-standards.md` | API design conventions for the project |

---

## Architecture Summary

```
React (S3) → API Gateway (REST) → Lambda (Flask/serverless-wsgi) → DynamoDB
```

| Layer | Technology |
|-------|-----------|
| Frontend hosting | Amazon S3 (static website) |
| API layer | Amazon API Gateway (REST, CORS enabled) |
| Compute | AWS Lambda (Python 3.12, arm64, 256 MB) |
| Framework | Flask 3.1 + serverless-wsgi adapter |
| Database | DynamoDB (on-demand); 3 tables: products, cart, orders |
| IaC | AWS SAM (CloudFormation transform) |

---

## API Surface (12 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/products` | List products (optional `?category=X`) |
| GET | `/api/products/:id` | Get product detail |
| GET | `/api/products/categories` | List all categories |
| GET | `/api/products/search?q=X` | Search products |
| GET | `/api/cart` | Get cart with totals |
| POST | `/api/cart/items` | Add item to cart |
| PUT | `/api/cart/items/:id` | Update item quantity |
| DELETE | `/api/cart/items/:id` | Remove item |
| DELETE | `/api/cart` | Clear cart |
| POST | `/api/orders` | Place order (checkout) |
| GET | `/api/orders` | List order history |
| GET | `/api/orders/:id` | Get order detail |

---

## Key Observations

- **Session-based cart**: Cart and orders are keyed by `sessionId` (DynamoDB composite key: `sessionId` + `productId`/`orderId`). No authentication layer exists yet.
- **No tests committed**: The README references `backend/tests/test_cart_service.py` but the file was not included in the initial commit.
- **Built dist included**: `frontend/dist/` (pre-built assets) is untracked but present on disk — it was not committed, indicating a local build artifact.
- **Single Lambda proxy**: All routes are handled by one Lambda function via `/{proxy+}` catch-all, keeping deployment simple at the cost of cold-start scope.
