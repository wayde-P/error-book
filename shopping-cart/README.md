# 购物车 - AWS 无服务器示例应用

基于 AWS 无服务器架构构建的全栈购物车应用，用于 Claude Code 工作坊演示智能编码工作流。

## 架构概览

```
┌─────────────┐        ┌──────────────┐        ┌───────────┐
│   React     │  HTTP  │ API Gateway  │  代理   │  Lambda   │
│   前端      │───────▶│   (REST)     │────────▶│  (Flask)  │
│   (S3)      │        │              │         │           │
└─────────────┘        └──────────────┘         └─────┬─────┘
                                                      │
                                                      ▼
                                                ┌───────────┐
                                                │ DynamoDB  │
                                                │  (4张表)  │
                                                └───────────┘
```

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React 18 + Vite，托管于 S3 | 静态网站托管 |
| API 层 | Amazon API Gateway (REST) | 启用 CORS |
| 后端 | AWS Lambda 运行 Flask | 通过 serverless-wsgi 适配 |
| 数据库 | DynamoDB（按需计费） | products / cart / orders / discounts 四张表 |
| 基础设施 | AWS SAM | CloudFormation 模板 |

## 项目结构

```
shopping-cart/
├── backend/
│   ├── app.py                  # Flask 应用入口，注册三个 Blueprint
│   ├── lambda_handler.py       # Lambda 适配器（API Gateway → Flask）
│   ├── requirements.txt        # Python 依赖
│   ├── routes/
│   │   ├── products.py         # 商品相关接口
│   │   ├── cart.py             # 购物车相关接口（支持 ?code=X 折扣参数）
│   │   ├── orders.py           # 订单相关接口
│   │   ├── discounts.py        # 折扣码验证接口
│   │   └── wishlist.py         # 愿望清单接口
│   ├── services/
│   │   ├── product_service.py  # 商品业务逻辑（含自动种子数据）
│   │   ├── cart_service.py     # 购物车业务逻辑（含折扣计算）
│   │   ├── order_service.py    # 订单创建逻辑（含折扣记录）
│   │   ├── discount_service.py # 折扣码验证、计算、应用逻辑
│   │   └── wishlist_service.py # 愿望清单业务逻辑
│   ├── models/
│   │   ├── product.py          # DynamoDB 商品数据模型
│   │   ├── cart.py             # DynamoDB 购物车数据模型
│   │   ├── order.py            # DynamoDB 订单数据模型
│   │   └── discount.py         # DynamoDB 折扣码数据模型
│   └── tests/
│       ├── test_cart_service.py       # 购物车服务单元测试（19 个：添加/删除/更新/合计）
│       ├── test_cart_service_discount.py # 购物车折扣集成测试（3 个）
│       ├── test_discount_service.py   # 折扣服务单元测试（18 个）
│       └── test_discount_routes.py    # 折扣路由测试（4 个）
├── frontend/
│   ├── index.html              # HTML 入口
│   ├── package.json            # Node 依赖（React 18、React Router、Vite）
│   ├── vite.config.js          # Vite 配置（开发时代理 /api 到 localhost:5000）
│   └── src/
│       ├── main.jsx            # React 入口
│       ├── App.jsx             # 根组件，包含客户端路由
│       ├── styles.css          # 全局样式
│       ├── components/
│       │   ├── Header.jsx      # 导航栏（含购物车数量徽标）
│       │   ├── ProductCard.jsx # 商品卡片（含数量步进器 − n +）
│       │   └── CartItem.jsx    # 购物车条目（含数量调整控件）
│       ├── pages/
│       │   ├── ProductList.jsx # 商品列表（支持分类筛选）
│       │   ├── CartPage.jsx    # 购物车页（含结算功能）
│       │   └── OrdersPage.jsx  # 订单历史
│       ├── context/
│       │   └── CartContext.jsx # 购物车全局状态（React Context）
│       └── services/
│           └── api.js          # 统一 HTTP 客户端（所有接口调用）
├── template.yaml               # SAM/CloudFormation 模板
├── deploy.sh                   # 一键部署脚本
└── docs/
    └── api-standards.md        # API 设计规范
```

## API 接口

### 商品

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/products` | 获取商品列表（支持 `?category=X` 过滤） |
| GET | `/api/products/:id` | 获取单个商品详情 |
| GET | `/api/products/categories` | 获取所有分类 |
| GET | `/api/products/search?q=X` | 搜索商品 |

### 购物车

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/cart` | 获取购物车（含小计、税额、合计） |
| GET | `/api/cart?code=X` | 获取购物车（含折扣后合计） |
| POST | `/api/cart/items` | 添加商品（支持指定数量） |
| PUT | `/api/cart/items/:id` | 更新商品数量 |
| DELETE | `/api/cart/items/:id` | 删除单个商品 |
| DELETE | `/api/cart` | 清空购物车 |

### 愿望清单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/wishlist` | 获取愿望清单 |
| POST | `/api/wishlist/items` | 收藏商品（body: `{ "productId": "..." }`） |
| DELETE | `/api/wishlist/items/:id` | 从愿望清单移除 |
| POST | `/api/wishlist/items/:id/move-to-cart` | 移入购物车（body: `{ "keepInWishlist": true/false }`） |

### 折扣码

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/discounts/validate` | 验证折扣码，返回折扣详情 |

### 订单

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/orders` | 提交订单（结算，自动清空购物车） |
| GET | `/api/orders` | 获取订单历史 |
| GET | `/api/orders/:id` | 获取单个订单详情 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 服务健康检查 |

## 部署

```bash
./deploy.sh
```

一条命令完成全部部署流程：
1. SAM 构建 Lambda 包
2. 部署后端基础设施（API Gateway + Lambda + DynamoDB）
3. 注入 API URL 并构建 React 前端
4. 将前端静态文件同步到 S3

## 本地开发

```bash
# 启动后端（终端 1）
cd backend
pip install -r requirements.txt
python app.py

# 启动前端（终端 2）
cd frontend
npm install
npm run dev
```

Vite 开发服务器会将 `/api` 请求自动代理到 `localhost:5000`，无需修改任何代码。

## 修改代码后重新部署

Claude 完成代码修改后，执行：

```bash
./deploy.sh
```

刷新浏览器即可看到最新效果。

## 关键设计说明

- **会话隔离**：购物车和订单通过 `sessionId` 区分用户。当前版本硬编码为 `"workshop-user"`，生产环境需替换为真实的认证 ID。
- **商品价格快照**：商品加入购物车时会快照 `name`、`price`、`image`，商品信息后续变更不影响已在购物车中的条目价格。
- **税率**：固定 8%，税基为折后金额（先折扣后计税）。
- **折扣码**：支持百分比（`percent`）和固定金额（`fixed`）两种类型，可设置过期时间和最大使用次数。结算时后端重新验证，防止码在浏览购物车到提交订单之间失效。折扣信息随订单一起写入 DynamoDB。
- **自动种子数据**：首次访问商品列表时，若 DynamoDB 为空，`ProductService` 会自动写入 10 条演示商品。
- **愿望清单**：复用 CartTable，通过 `listType` 字段区分购物车条目（`"cart"`）和愿望清单条目（`"wishlist"`）。同一商品不能同时存在于两个列表。移入购物车时用户可选择是否保留收藏。
