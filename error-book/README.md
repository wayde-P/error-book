# 错题本 (Error Book)

面向家长和学生的错题管理系统。拍照上传题目，AI 自动识别题目内容、科目与考点分析，并按标签归档管理。

## 功能

- **AI 识别**：上传题目照片，Claude Vision 自动提取题目内容、科目和考点分析
- **批量上传**：支持同时上传多张图片，实时显示每张图片的识别进度
- **手动录入**：不上传图片也可手动填写题目内容
- **标签管理**：创建自定义彩色标签，对题目分类
- **搜索与筛选**：按关键词搜索、按标签筛选题库
- **题目编辑**：修改题目内容、分析和标签
- **Cognito 认证**：每位用户数据完全隔离

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19, Tailwind CSS, Vite, AWS Amplify |
| 后端 | FastAPI, Mangum (Lambda adapter) |
| 认证 | AWS Cognito |
| 数据库 | DynamoDB (单表设计) |
| 图片存储 | S3 + Presigned URL 直传 |
| AI | Claude claude-sonnet-4-6 via AWS Bedrock |
| 基础设施 | AWS SAM (CloudFormation) |

## 项目结构

```
error-book/
├── backend/
│   ├── app.py                  # FastAPI 应用，挂载路由
│   ├── handler.py              # Lambda 入口 (Mangum)
│   ├── auth.py                 # Cognito userId 提取
│   ├── config.py               # 环境变量配置
│   ├── models/
│   │   ├── question.py         # Question Pydantic 模型
│   │   └── tag.py              # Tag Pydantic 模型
│   ├── routes/
│   │   ├── upload.py           # 生成 S3 Presigned URL
│   │   ├── questions.py        # 题目 CRUD + AI 识别
│   │   └── tags.py             # 标签 CRUD
│   ├── services/
│   │   ├── recognition.py      # Bedrock Vision 调用
│   │   ├── questionService.py  # DynamoDB 题目操作
│   │   └── tagService.py       # DynamoDB 标签操作
│   ├── tests/                  # pytest 测试
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js       # axios 实例，自动附加 Bearer token
│   │   ├── contexts/
│   │   │   ├── AuthContext.jsx # Cognito 会话管理
│   │   │   └── UploadContext.jsx # 跨页面上传状态
│   │   ├── components/         # 可复用 UI 组件
│   │   └── pages/              # 页面组件
│   └── package.json
├── template.yaml               # SAM / CloudFormation 模板
├── samconfig.toml              # SAM 部署配置
└── deploy.sh                   # 一键部署脚本
```

## API 文档

所有接口均需在请求头携带 Cognito ID Token：

```
Authorization: Bearer <cognito-id-token>
```

### Upload

#### `GET /upload/presigned-url` — 获取 S3 直传 URL

| 参数 | 类型 | 说明 |
|---|---|---|
| `filename` | query string | 文件名 |
| `contentType` | query string | `image/jpeg` / `image/png` / `image/webp` |

**响应**

```json
{
  "url": "https://s3.amazonaws.com/...",
  "key": "userId/questionId/filename.jpg",
  "questionId": "uuid"
}
```

---

### Questions

#### `POST /questions/recognize` — AI 识别图片中的题目

```json
{
  "imageKey": "userId/questionId/photo.jpg",
  "subject": "数学"
}
```

`subject` 为可选的科目提示。**响应**为题目数组：

```json
[
  {
    "questionId": "uuid",
    "userId": "cognito-sub",
    "imageKey": "userId/questionId/photo.jpg",
    "imageUrl": "https://...",
    "subject": "数学",
    "content": "已知函数 f(x)=x²+2x，求 f'(x)。",
    "analysis": "本题考查导数基本求法，利用幂函数求导公式...",
    "tags": [],
    "status": "active",
    "createdAt": "2026-06-28T07:00:00Z"
  }
]
```

#### `POST /questions/manual` — 手动创建题目

```json
{
  "subject": "语文",
  "content": "下列词语中，字形全部正确的一项是...",
  "analysis": "考查字形辨析，需注意形近字..."
}
```

#### `GET /questions` — 获取题目列表

| 参数 | 类型 | 说明 |
|---|---|---|
| `tagId` | query string (可选) | 按标签筛选 |
| `keyword` | query string (可选) | 关键词搜索 |
| `lastKey` | query string (可选) | 分页游标 |

**响应**

```json
{
  "items": [...],
  "lastKey": "base64-encoded-cursor"
}
```

#### `GET /questions/{questionId}` — 获取单道题目

#### `PUT /questions/{questionId}` — 更新题目

```json
{
  "subject": "物理",
  "content": "修改后的题目内容",
  "analysis": "修改后的考点分析",
  "tags": ["tag-id-1", "tag-id-2"]
}
```

所有字段均为可选，仅传入需修改的字段。

#### `DELETE /questions/{questionId}` — 删除题目

**响应** `{"message": "删除成功"}`

---

### Tags

#### `GET /tags` — 获取标签列表

**响应**

```json
[
  {
    "tagId": "uuid",
    "userId": "cognito-sub",
    "name": "易错题",
    "color": "#FF5733",
    "createdAt": "2026-06-28T07:00:00Z"
  }
]
```

#### `POST /tags` — 创建标签

```json
{
  "name": "重点题",
  "color": "#3B82F6"
}
```

#### `PUT /tags/{tagId}` — 更新标签

```json
{
  "name": "新名称",
  "color": "#10B981"
}
```

#### `DELETE /tags/{tagId}` — 删除标签

**响应** `{"message": "删除成功"}`

---

## 本地开发

### 前置条件

- Python 3.12
- Node 18+

### 后端

```bash
cd backend
pip install -r requirements.txt
```

后端依赖 Lambda 的 Cognito authorizer 提取 userId，本地无法直接运行完整服务，建议通过测试验证逻辑。

### 前端

```bash
cd frontend
npm install

# 复制环境变量模板并填入值
cp .env.local.example .env.local
# 编辑 .env.local，填入 VITE_USER_POOL_ID / VITE_USER_POOL_CLIENT_ID / VITE_API_BASE_URL

npm run dev   # http://localhost:5173
```

前端环境变量：

| 变量 | 说明 |
|---|---|
| `VITE_USER_POOL_ID` | Cognito User Pool ID |
| `VITE_USER_POOL_CLIENT_ID` | Cognito App Client ID |
| `VITE_API_BASE_URL` | API Gateway 端点 URL |

## 运行测试

```bash
cd backend

# 运行全部测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_recognition.py -v

# 运行单个测试函数
python -m pytest tests/test_recognition.py::test_recognize_success -v
```

测试通过 `tests/conftest.py` 注入环境变量，AWS 服务依赖全部使用 mock，无需真实 AWS 凭证。

## 部署

### 前置条件

- AWS CLI 已配置（具备 CloudFormation、Lambda、S3、DynamoDB、Cognito、CloudFront、Bedrock 权限）
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) 已安装
- Node 18+, Python 3.12

### 一键部署

```bash
./deploy.sh
```

脚本依次执行：

1. 构建前端（占位环境变量）
2. `sam build && sam deploy` 部署所有 AWS 资源
3. 从 CloudFormation 输出获取真实端点和 Cognito 信息
4. 注入真实环境变量，重新构建前端
5. 上传前端产物到 S3

部署完成后输出前端 CloudFront 地址和 API 地址。

### 部署配置

默认部署到 `us-east-1`，Stack 名称 `error-book`，可在 `samconfig.toml` 中修改。

### 架构图

```
用户浏览器
  │
  ├─ 静态资源 ──► CloudFront ──► S3 (前端文件)
  │
  └─ API 请求 ──► API Gateway (Cognito 认证)
                      │
                      └─► Lambda (FastAPI + Mangum)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
                DynamoDB     S3        Bedrock
               (题目/标签)  (图片)   (Claude Vision)
```
