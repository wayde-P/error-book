# 错题本项目设计文档

**日期**：2026-06-28  
**状态**：已确认  
**目标用户**：家长和中小学生

---

## 1. 项目概述

用户通过手机或电脑上传题目照片，系统自动用 Claude Vision 识别题目内容，将识别结果保存到该用户的错题库。用户可以给错题打标签分类，并通过搜索和标签筛选快速找到题目。

---

## 2. 整体架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│              React 19 + Tailwind CSS                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────┐
│         CloudFront (CDN)             │
│  静态资源缓存 + HTTPS 终止            │
└──────┬───────────────────────────────┘
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────────────────────────────────┐
│  S3 Bucket  │  │         API Gateway (REST API)           │
│ (前端静态   │  │  JWT Authorizer → AWS Cognito User Pool  │
│  资源托管)  │  └──────────────────┬──────────────────────┘
└─────────────┘                     │
                                    ▼
                      ┌─────────────────────────┐
                      │   AWS Lambda Function    │
                      │   FastAPI + Mangum       │
                      └──────┬──────────┬────────┘
                             │          │
              ┌──────────────┘          └──────────────┐
              ▼                                        ▼
┌─────────────────────┐              ┌─────────────────────────┐
│     DynamoDB        │              │        S3 Bucket        │
│  错题库 + 标签数据   │              │   用户上传图片存储        │
└─────────────────────┘              └──────────┬──────────────┘
                                                │
                                                ▼
                                  ┌─────────────────────────┐
                                  │   Claude Vision API     │
                                  │  (claude-sonnet-4-6)    │
                                  │  图片 → 结构化题目数据   │
                                  └─────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   AWS Cognito User Pool                      │
│         注册 / 登录 / JWT Token 签发 / 用户管理              │
└─────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | React 19 + Tailwind CSS | SPA，部署到 S3+CloudFront |
| 认证 | AWS Cognito User Pool | JWT 签发，API Gateway JWT Authorizer |
| API 层 | API Gateway REST API | JWT 鉴权，CORS 限制 CloudFront 域名 |
| 后端 | FastAPI + Mangum | 单 Lambda 函数，Mangum 适配 ASGI |
| AI 识别 | Claude Vision（claude-sonnet-4-6） | 图片直接识别，返回结构化题目数据 |
| 数据库 | DynamoDB | 单表设计，GSI 支持标签查询和搜索 |
| 图片存储 | S3 | Presigned URL 前端直传，路径按用户隔离 |

---

## 3. 关键业务流程

### 图片上传 & 识别流程

```
1. 用户选择多张图片
2. 前端为每张图片独立显示进度卡片（待上传）
3. 逐张处理：
   a. 请求 GET /upload/presigned-url → 获取 S3 presigned URL
   b. 前端直传图片到 S3（进度：上传中）
   c. 调用 POST /questions/recognize（传入 S3 key）
   d. Lambda 读取 S3 图片 → 调用 Claude Vision → 解析结构化题目
   e. 写入 DynamoDB（进度：识别完成 ✓ / 识别失败 ✗）
4. 全部完成后，前端跳转到错题库
```

### 认证流程

```
1. 用户通过 Cognito Hosted UI 或自定义表单登录
2. Cognito 返回 Access Token（JWT）+ Refresh Token
3. 前端将 Token 存入内存（Access）+ localStorage（Refresh）
4. Axios 拦截器自动在每次请求加 Authorization: Bearer <token>
5. API Gateway JWT Authorizer 验证 Token，提取 userId（sub claim）
6. Token 过期（401）时，拦截器自动用 Refresh Token 换新 Token
```

---

## 4. 前端结构

### 页面

| 页面 | 路由 | 说明 |
|------|------|------|
| LoginPage | `/login` | Cognito 登录/注册 |
| DashboardPage | `/` | 错题统计概览 |
| UploadPage | `/upload` | 图片上传 + 实时进度 |
| ErrorBankPage | `/errors` | 错题库列表 + 搜索 + 标签筛选 |
| ErrorDetailPage | `/errors/:id` | 单题详情 + 编辑标签 |
| TagsPage | `/tags` | 标签管理 |

### 目录结构

```
src/
├── pages/
│   ├── LoginPage.jsx
│   ├── DashboardPage.jsx
│   ├── UploadPage.jsx
│   ├── ErrorBankPage.jsx
│   ├── ErrorDetailPage.jsx
│   └── TagsPage.jsx
├── components/
│   ├── UploadDropzone.jsx      # 拖拽/多选上传区域
│   ├── UploadProgressCard.jsx  # 单张图片识别进度卡片
│   ├── ErrorCard.jsx           # 错题卡片（列表展示）
│   ├── TagBadge.jsx            # 标签徽章
│   ├── SearchBar.jsx           # 全局搜索框
│   └── NavBar.jsx              # 顶部导航
├── contexts/
│   ├── AuthContext.jsx         # Cognito JWT 状态管理
│   └── UploadContext.jsx       # 上传队列状态
└── api/
    └── client.js               # Axios 实例，自动带 JWT header
```

### 上传进度 UI

每张图片独立显示状态：

```
[图片1.jpg] ████████░░  上传中 (80%)
[图片2.jpg] ██████████  识别完成 ✓
[图片3.jpg] ░░░░░░░░░░  等待中...
[图片4.jpg] ██████████  识别失败 ✗ [重试]
```

---

## 5. 后端 API 设计

### 路由列表

| Method | Path | 说明 | 认证 |
|--------|------|------|------|
| POST | `/auth/refresh` | 刷新 Cognito Token | 否 |
| GET | `/upload/presigned-url` | 获取 S3 上传 presigned URL | JWT |
| POST | `/questions/recognize` | 触发 Claude Vision 识别 | JWT |
| GET | `/questions` | 错题列表（搜索+标签筛选） | JWT |
| GET | `/questions/{id}` | 单题详情 | JWT |
| PUT | `/questions/{id}` | 编辑题目内容/标签 | JWT |
| DELETE | `/questions/{id}` | 删除错题 | JWT |
| GET | `/tags` | 用户标签列表 | JWT |
| POST | `/tags` | 创建标签 | JWT |
| DELETE | `/tags/{id}` | 删除标签 | JWT |

### Lambda 目录结构

```
backend/
├── handler.py              # Mangum 入口
├── app.py                  # FastAPI app 初始化
├── routes/
│   ├── upload.py           # presigned URL 生成
│   ├── questions.py        # 错题 CRUD
│   └── tags.py             # 标签 CRUD
├── services/
│   ├── recognition.py      # Claude Vision 调用逻辑
│   ├── question_service.py
│   └── tag_service.py
└── models/
    ├── question.py         # Pydantic 模型
    └── tag.py
```

---

## 6. 数据模型

### DynamoDB 单表设计（表名：`ErrorBook`）

#### 错题记录

```
PK:  USER#{userId}
SK:  QUESTION#{questionId}
属性:
  imageUrl:   string        # S3 图片 URL
  subject:    string        # 学科（数学/语文/英语等）
  content:    string        # 题目文字内容（Claude 识别）
  analysis:   string        # 错误分析（Claude 生成）
  tags:       string[]      # 标签 ID 列表
  status:     string        # pending | done | failed
  createdAt:  string        # ISO8601
  updatedAt:  string        # ISO8601
```

#### 标签

```
PK:  USER#{userId}
SK:  TAG#{tagId}
属性:
  name:       string        # 标签名称
  color:      string        # 标签颜色（hex）
  createdAt:  string        # ISO8601
```

#### 查询策略

- **按标签筛选**：主表 Query `PK=USER#{userId}`，再用 `FilterExpression: contains(tags, tagId)`。错题本数据量小（单用户百~千条），FilterExpression 足够，无需额外 GSI。
- **关键词搜索**：同上，`FilterExpression: contains(content, keyword)`，前端搜索框触发。
- **GSI-ByDate**：`PK=USER#{userId}`，`SK=createdAt`，支持按时间排序分页查询。

---

## 7. 错误处理

| 场景 | 处理方式 |
|------|---------|
| Claude Vision 识别失败 | 题目状态置为 `failed`，前端显示"识别失败，可手动输入"，支持单张重试 |
| S3 上传超时/失败 | 前端捕获错误，单张独立显示失败状态，提供重试按钮 |
| Presigned URL 过期 | URL 有效期 15 分钟，过期返回 403，前端重新请求 URL 后自动重试 |
| DynamoDB 写入失败 | Lambda 内部 retry 3 次，失败后返回 500，前端提示用户 |
| JWT 过期 | API Gateway 返回 401，Axios 拦截器自动用 Refresh Token 换新 Token |
| 网络中断 | 上传队列保存在 UploadContext，页面刷新后提示用户重新上传 |

---

## 8. 安全设计

- **用户数据隔离**：所有 DynamoDB 查询强制带 `USER#{userId}`（从 JWT `sub` claim 提取），用户只能访问自己的数据，后端不信任前端传入的 userId
- **S3 路径隔离**：图片路径为 `{userId}/{questionId}/{filename}`，Presigned URL 仅限该路径，有效期 15 分钟
- **IAM 最小权限**：Lambda 执行角色仅有 DynamoDB 指定表读写权限 + S3 指定 Bucket 的 `GetObject`/`PutObject` 权限
- **文件类型限制**：上传只接受 `image/jpeg`、`image/png`、`image/webp`，单文件最大 10MB
- **CORS 限制**：API Gateway 仅允许 CloudFront 前端域名跨域访问
- **Cognito 密码策略**：最少 8 位，包含大小写字母和数字

---

## 9. 部署架构

| 资源 | 说明 |
|------|------|
| S3 Bucket（前端） | 静态网站托管，CloudFront OAC 访问 |
| S3 Bucket（图片） | 私有，仅 Lambda 和 Presigned URL 访问 |
| CloudFront Distribution | 前端 CDN，HTTPS，SPA 路由 fallback |
| Cognito User Pool | 用户注册/登录，JWT 签发 |
| API Gateway REST API | JWT Authorizer，所有受保护路由 |
| Lambda Function | FastAPI + Mangum，Python 3.12 |
| DynamoDB Table | 按需计费模式，单表设计 |
| SAM / CDK | 基础设施即代码部署 |
