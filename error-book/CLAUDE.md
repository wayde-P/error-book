# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

错题本（Error Book）——面向家长和学生的错题管理系统。上传题目照片，AI 自动识别并归档。

## 常用命令

### 后端

```bash
cd backend
pip install -r requirements.txt

# 运行全部测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_recognition.py -v

# 运行单个测试函数
python -m pytest tests/test_recognition.py::test_recognize_success -v
```

### 前端

```bash
cd frontend
npm install
npm run dev       # 本地开发服务器
npm run build     # 构建到 dist/
```

### 部署

```bash
# 设置 Anthropic API Key（首次部署前）
aws ssm put-parameter \
  --name /error-book/anthropic-api-key \
  --value "your-api-key" \
  --type SecureString

# 一键部署（SAM build + deploy + 前端上传 + CloudFront 刷新）
./deploy.sh
```

## 架构概览

### 整体架构

```
前端 (React SPA)
  → CloudFront → S3 (静态文件)
  → API Gateway → Lambda (FastAPI + Mangum)
                      ↓
              DynamoDB (数据)  S3 (图片)
              Bedrock Claude Vision (AI 识别)
              Cognito (认证)
```

### 后端

- **`handler.py`**：Lambda 入口，用 `Mangum` 将 FastAPI 适配为 Lambda handler
- **`app.py`**：FastAPI 应用，挂载三个路由：`/upload`、`/questions`、`/tags`
- **`auth.py`**：从 Lambda event 的 `requestContext.authorizer.claims.sub` 提取 Cognito 用户 ID；本地测试时无法直接调用
- **`config.py`**：所有配置从环境变量读取（`TABLE_NAME`、`IMAGES_BUCKET`、`COGNITO_USER_POOL_ID`），全部使用 camelCase
- **`services/recognition.py`**：通过 Bedrock 调用 `claude-sonnet-4-6`，从 S3 下载图片后进行 Vision 识别，返回 `{subject, content, analysis}` JSON
- **`services/questionService.py`**：DynamoDB 操作，Key 格式为 `PK=USER#{userId}` / `SK=QUESTION#{questionId}`

### DynamoDB 数据模型

单表设计，`PK`/`SK` 复合主键：

| 实体 | PK | SK |
|------|----|----|
| 题目 | `USER#{userId}` | `QUESTION#{questionId}` |
| 标签 | `USER#{userId}` | `TAG#{tagId}` |

### 前端

- **`AuthContext.jsx`**：用 AWS Amplify 管理 Cognito 会话；`getToken()` 返回 Cognito ID Token，通过 `setTokenGetter` 注入到 API client
- **`api/client`**：axios 实例，自动在请求头附加 Bearer token
- **`UploadContext`**：跨页面共享上传状态（进度、结果列表）

### 前端环境变量

复制 `frontend/.env.local.example` 为 `frontend/.env.local`，填入：

```
VITE_USER_POOL_ID=
VITE_USER_POOL_CLIENT_ID=
VITE_API_BASE_URL=
```

部署后从 SAM 输出（`UserPoolId`、`UserPoolClientId`、`ApiEndpoint`）获取这些值。

## 代码规范

### Python（后端）

- 变量、参数、字段名使用 **camelCase**（如 `questionId`、`imageKey`、`userId`）
- Pydantic 模型字段同样使用 camelCase

### React（前端）

- 只使用函数式组件，props 在函数签名中解构
- 组件不超过 100 行，复杂 UI 提取子组件
- 不使用内联样式，使用 Tailwind class

## 测试注意事项

后端测试通过 `tests/conftest.py` 注入环境变量（`TABLE_NAME=test-table` 等），AWS 服务依赖需 mock。`recognition.py` 的测试需 mock `boto3` 的 S3 和 Bedrock 客户端。
