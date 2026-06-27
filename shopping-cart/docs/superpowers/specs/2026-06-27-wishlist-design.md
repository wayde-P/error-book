# 愿望清单功能设计文档

**日期：** 2026-06-27  
**状态：** 已批准

---

## 概述

用户可以将商品收藏到愿望清单，以便后续查看或加入购物车。愿望清单复用现有 `CartTable`，通过 `listType` 字段区分购物车条目和愿望清单条目，不增加新的 DynamoDB 表。

---

## 数据层

### 存储方案

复用 `CartTable`（`sessionId HASH + productId RANGE`），不修改 `template.yaml`。

每条记录新增 `listType` 字段：

| 值 | 含义 |
|----|------|
| `"cart"` | 购物车条目（默认） |
| `"wishlist"` | 愿望清单条目 |

现有购物车的所有 `put_item` 写入补写 `listType: "cart"`，保持向后兼容。

### CartModel 变更

- `get_items(session_id, list_type="cart")` — 加 `list_type` 过滤参数，默认值 `"cart"`，现有调用行为不变
- `get_wishlist_items(session_id)` — 语义糖，等价于 `get_items(session_id, "wishlist")`

商品数据在加入愿望清单时快照 `name / price / image`，与购物车行为一致，防止商品后续变更影响已收藏条目。

---

## 后端

### 新增文件

**`services/wishlist_service.py`**

| 方法 | 说明 |
|------|------|
| `get_wishlist(session_id)` | 返回愿望清单商品列表 |
| `add_item(session_id, product_id)` | 快照商品信息，写入 `listType="wishlist"` |
| `remove_item(session_id, product_id)` | 删除愿望清单条目 |
| `move_to_cart(session_id, product_id, keep_in_wishlist)` | 调用 CartService 加入购物车，按参数决定是否保留愿望清单条目 |

**`models/wishlist.py`** — 薄包装，调用 `CartModel` 并固定 `list_type="wishlist"`

**`routes/wishlist.py`** — 注册到 `/api/wishlist`

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/wishlist` | 获取愿望清单 |
| POST | `/api/wishlist/items` | 添加商品（body: `{ "productId": "..." }`） |
| DELETE | `/api/wishlist/items/:id` | 移除商品 |
| POST | `/api/wishlist/items/:id/move-to-cart` | 移入购物车（body: `{ "keepInWishlist": true/false }`） |

### app.py

注册 `wishlist_bp` 到 `/api/wishlist`。

---

## 前端

### 新增文件

| 文件 | 说明 |
|------|------|
| `pages/WishlistPage.jsx` | 愿望清单独立页面 |
| `context/WishlistContext.jsx` | 状态管理，模式与 CartContext 一致 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `services/api.js` | 新增 `getWishlist`、`addToWishlist`、`removeFromWishlist`、`moveToCart` |
| `components/ProductCard.jsx` | 新增收藏按钮（♡/♥），已收藏时高亮 |
| `App.jsx` | 注册 `/wishlist` 路由，`WishlistProvider` 包裹应用 |
| `Header.jsx` | 导航栏新增"愿望清单"链接 |

### WishlistPage 交互

- 展示收藏商品列表（name / price / image 快照）
- 每个商品有"加入购物车"按钮
- 点击后弹出确认对话框："是否从愿望清单中移除？"，用户选择保留或移除
- 空状态展示提示文案，引导用户去商品页收藏

### WishlistContext

```
state: { items: [], loading: false }
actions: addToWishlist(productId), removeFromWishlist(productId),
         moveToCart(productId, keepInWishlist), isInWishlist(productId)
```

`isInWishlist` 供 `ProductCard` 判断当前商品是否已收藏，控制图标高亮。

---

## 测试

**`tests/test_wishlist_service.py`**（TDD，先写测试）

| 测试场景 |
|----------|
| 添加商品到愿望清单，快照 name/price/image |
| 添加不存在的商品返回错误 |
| 移除已收藏商品 |
| 移除不在愿望清单的商品返回错误 |
| 移入购物车且不保留（wishlist 条目被删除） |
| 移入购物车且保留（wishlist 条目保留） |

---

## 关键约束

- 同一商品可同时存在于购物车和愿望清单（`listType` 不同，DynamoDB 主键相同会冲突）— **解决方案：** 愿望清单和购物车使用独立 key 策略，`productId` 在愿望清单中存为原值，在购物车中不变，两者 `listType` 不同但主键 `(sessionId, productId)` 相同，因此**同一商品不能同时出现在两个列表**。加入购物车时若已在愿望清单，`move-to-cart` 会先加入购物车再按 `keepInWishlist` 决定是否删除愿望清单条目；直接从商品页"加入购物车"不影响愿望清单状态。
- 会话 ID 与购物车一致，硬编码为 `"workshop-user"`
- 愿望清单无数量字段（收藏的是商品，不是"几件"）
