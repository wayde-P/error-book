# 折扣码功能实现计划

## 功能概述

用户在购物车页面输入折扣码，验证通过后自动计算折扣金额，并在结算时将折扣信息写入订单。

---

## 需要新增的文件

### `backend/models/discount.py`
DynamoDB `discounts` 表的数据模型，负责按 code 查询折扣记录。

### `backend/services/discount_service.py`
折扣业务逻辑：验证码是否存在、是否过期、是否超过使用次数上限，并返回折扣类型和金额。

### `backend/routes/discounts.py`
暴露验证接口 `POST /api/discounts/validate`，接收 `{ "code": "SAVE10" }` 返回折扣详情或错误。

---

## 需要修改的文件

### 后端

| 文件 | 改动 |
|------|------|
| `backend/app.py` | 注册 `discounts_bp`，挂载到 `/api/discounts` |
| `backend/services/cart_service.py` | `get_cart()` 接受可选 `discount` 参数，计算折后小计、税额、合计 |
| `backend/routes/cart.py` | `get_cart` 路由支持可选 query param `?code=X` |
| `backend/services/order_service.py` | `create_order()` 接受 `discount` 字段，写入订单记录 |
| `backend/routes/orders.py` | `create_order` 路由从请求体读取 `discountCode` 并传给 service |
| `template.yaml` | 新增 `DiscountsTable` DynamoDB 表；给 Lambda 添加该表的 `DynamoDBCrudPolicy` 和环境变量 `DISCOUNTS_TABLE` |

### 前端

| 文件 | 改动 |
|------|------|
| `frontend/src/services/api.js` | 新增 `validateDiscount(code)` 函数，调用 `POST /api/discounts/validate` |
| `frontend/src/context/CartContext.jsx` | 新增 `discount` state 和 `applyDiscount(code)` / `removeDiscount()` 方法；`cart` 对象携带折扣后的合计 |
| `frontend/src/pages/CartPage.jsx` | 新增折扣码输入框和"应用"按钮；展示折扣行（如 `-$5.00 (SAVE10)`）；结算时将 `discountCode` 传给 `api.createOrder()` |
| `frontend/src/services/api.js` | `createOrder()` 增加 `discountCode` 参数 |

---

## DynamoDB 表结构

**表名：** `{StackName}-discounts`
**主键：** `code`（String，Hash Key）

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | String | 折扣码（大写，如 `SAVE10`） |
| `type` | String | `"percent"` 或 `"fixed"` |
| `value` | Number | 折扣值（百分比或固定金额） |
| `expiresAt` | String | ISO 8601 过期时间（可选） |
| `maxUses` | Number | 最大使用次数（可选，0 = 不限） |
| `usedCount` | Number | 已使用次数 |

---

## API 接口

### `POST /api/discounts/validate`

请求体：
```json
{ "code": "SAVE10" }
```

成功响应（200）：
```json
{
  "code": "SAVE10",
  "type": "percent",
  "value": 10,
  "discountAmount": 5.00
}
```

失败响应（404）：
```json
{ "error": "Invalid or expired discount code" }
```

---

## 购物车金额计算逻辑

```
小计    = sum(price × quantity)
折扣额  = type == "percent" ? subtotal × value/100 : min(value, subtotal)
折后小计 = subtotal - 折扣额
税额    = 折后小计 × 0.08
合计    = 折后小计 + 税额
```

税基为折后金额（先折扣后计税）。

---

## 实现顺序

1. `template.yaml` — 新增 DynamoDB 表和 Lambda 权限
2. `backend/models/discount.py` — 数据层
3. `backend/services/discount_service.py` — 业务逻辑
4. `backend/routes/discounts.py` — 路由
5. `backend/app.py` — 注册 Blueprint
6. `backend/services/cart_service.py` — 加入折扣计算
7. `backend/routes/cart.py` — 传递 code 参数
8. `backend/services/order_service.py` + `backend/routes/orders.py` — 订单记录折扣
9. `frontend/src/services/api.js` — 新增 validateDiscount
10. `frontend/src/context/CartContext.jsx` — 折扣状态管理
11. `frontend/src/pages/CartPage.jsx` — 输入框和折扣展示

---

## 边界情况

- 码不存在 → 404
- 码已过期 → 404（同一错误，不泄露码是否存在）
- 折扣额超过小计 → 折后小计为 0，不出现负数
- 结算时重新验证折扣码（防止从前端验证到结算之间码失效）
- 折扣码大小写不敏感（后端统一转大写）
