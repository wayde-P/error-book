# 错题本系统设计文档

**日期：** 2026-06-28
**状态：** 已确认

---

## 概述

面向家长和学生的错题管理系统。用户上传题目照片，系统通过 Claude Vision 自动识别题目内容并结构化存储，支持标签分类和搜索管理。

**技术选型：**
- 前端：React 19 + Tailwind CSS
- 后端：FastAPI + Mangum（AWS Lambda）
- 认证：AWS Cognito + API Gateway JWT Authorizer
- 数据库：DynamoDB（单表设计）
- 图片存储：S3（前端 presigned URL 直传）
- AI 识别：Claude Vision（claude-sonnet-4-6）
- 托管：CloudFront + S3 静态托管

---

## 整体架构

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

### 关键数据流

**图片上传 & 识别流程：**
1. 前端向 API 请求 S3 Presigned URL（GET `/upload/presigned-url`）
2. 前端直接上传图片到 S3（不经 Lambda，节省带宽费用）
3. 前端通知后端开始识别（POST `/questions/recognize`）
4. Lambda 从 S3 读取图片 → 调用 Claude Vision API → 解析结构化数据
5. 写入 DynamoDB，返回题目记录

**认证流程：**
1. Cognito 签发 JWT Token
2. 前端每次请求携带 `Authorization: Bearer <token>` header
3. API Gateway JWT Authorizer 验证 Token，提取 `userId` 写入请求上下文
4. Lambda 从请求上下文取 `userId`，所有查询强制隔离

---

## 前端结构

### 页面

| 页面 | 路径 | 说明 |
|------|------|------|
| LoginPage | `/login` | 自定义登录/注册表单（使用 aws-amplify Auth，React 19 + Tailwind 样式） |
| DashboardPage | `/` | 错题统计概览（总数、各标签分布） |
| UploadPage | `/upload` | 图片上传 + 实时进度展示 |
| ErrorBankPage | `/errors` | 错题库列表、搜索、标签筛选 |
| ErrorDetailPage | `/errors/:id` | 单题详情、编辑标签、查看原图 |
| TagsPage | `/tags` | 标签管理（增删改） |

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
│   ├── UploadDropzone.jsx     # 拖拽/多选上传区域
│   ├── UploadProgressCard.jsx # 单张图片识别进度卡片
│   ├── ErrorCard.jsx          # 错题卡片
│   ├── TagBadge.jsx           # 标签徽章
│   ├── SearchBar.jsx          # 搜索框
│   └── NavBar.jsx             # 顶部导航
├── contexts/
│   ├── AuthContext.jsx        # Cognito JWT 状态
│   └── UploadContext.jsx      # 上传队列状态
└── api/
    └── client.js              # Axios 实例，自动带 JWT header
```

### 上传进度 UI 交互

用户选择多张图片后，每张图片独立显示进度卡片：

```
[图片1] ████████░░  上传中...
[图片2] ████████████ 识别中...
[图片3] ████████████ 完成 ✓
[图片4] ░░░░░░░░░░  等待中...
```

每张图片有独立状态：`pending` → `uploading` → `recognizing` → `done` / `failed`

---

## 后端 API

### 路由设计

| Method | Path | JWT 鉴权 | 说明 |
|--------|------|---------|------|
| GET | `/upload/presigned-url` | 是 | 获取 S3 上传 presigned URL |
| POST | `/questions/recognize` | 是 | 触发 Claude Vision 识别 |
| GET | `/questions` | 是 | 错题列表（支持搜索+标签筛选+分页） |
| GET | `/questions/{id}` | 是 | 单题详情 |
| PUT | `/questions/{id}` | 是 | 编辑题目内容/标签 |
| DELETE | `/questions/{id}` | 是 | 删除错题 |
| GET | `/tags` | 是 | 用户标签列表 |
| POST | `/tags` | 是 | 创建标签 |
| PUT | `/tags/{id}` | 是 | 编辑标签 |
| DELETE | `/tags/{id}` | 是 | 删除标签 |

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

## 数据模型（DynamoDB 单表设计）

**表名：** `ErrorBook`

### 数据结构

```
# 错题记录
PK: USER#{userId}
SK: QUESTION#{questionId}
属性:
  - imageUrl: str          # S3 图片路径
  - subject: str           # 科目（数学/语文/英语等）
  - content: str           # 题目文字内容（Claude 识别）
  - analysis: str          # 错误分析（Claude 生成）
  - tags: List[str]        # 标签 ID 列表
  - status: str            # pending / done / failed
  - createdAt: str         # ISO8601 时间戳

# 标签
PK: USER#{userId}
SK: TAG#{tagId}
属性:
  - name: str              # 标签名称
  - color: str             # 标签颜色（hex）
  - createdAt: str

# GSI-1：按标签查询错题
GSI PK: USER#{userId}#TAG#{tagId}
GSI SK: createdAt（按时间排序）

# GSI-2：关键词搜索（content 前缀匹配）
GSI PK: USER#{userId}
GSI SK: content（begins_with 前缀搜索，仅支持内容开头匹配；如需全文搜索可后期接 OpenSearch）
```

---

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| Claude Vision 识别失败 | 题目 status 置为 `failed`，前端显示"识别失败，可手动输入"，支持单张重试 |
| S3 上传超时/失败 | 前端捕获错误，单张独立重试，不影响其他图片队列 |
| Presigned URL 过期 | URL 有效期 15 分钟，前端收到 403 后自动重新请求 URL 并重试 |
| DynamoDB 写入失败 | Lambda 内部 retry 3 次，失败返回 500，前端提示用户 |
| JWT 过期 | API Gateway 返回 401，Axios 拦截器自动用 Refresh Token 换新 Token |

---

## 安全设计

- **数据隔离**：所有 DynamoDB 查询强制带 `USER#{userId}`（从 JWT claims 提取），用户只能访问自己的数据
- **S3 路径隔离**：图片路径格式为 `{userId}/{questionId}/{filename}`，presigned URL 仅对该路径有效
- **IAM 最小权限**：Lambda 执行角色仅有 DynamoDB 指定表的读写权限 + S3 指定 Bucket 的读写权限
- **文件类型验证**：上传文件类型限制为 `image/jpeg`、`image/png`、`image/webp`，单文件最大 10MB
- **CORS**：API Gateway 仅允许 CloudFront 域名跨域访问

---

## 基础设施（AWS SAM）

| 资源 | 说明 |
|------|------|
| Cognito User Pool | 用户注册/登录，JWT 签发 |
| API Gateway REST API | JWT Authorizer，路由转发到 Lambda |
| Lambda Function | FastAPI + Mangum，Python 3.12 |
| DynamoDB Table | 单表，按需计费（PAY_PER_REQUEST） |
| S3 Bucket（图片） | 用户图片存储，私有，仅 Lambda 可读 |
| S3 Bucket（前端） | 静态资源托管，CloudFront 源站 |
| CloudFront Distribution | HTTPS + CDN，前端入口 |
