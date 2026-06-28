# 错题本

面向家长和学生的错题管理系统。上传题目照片，AI 自动识别并归档。

## 功能

- 照片上传（支持多张，实时显示识别进度）
- Claude Vision 自动识别题目内容和科目
- 标签分类管理
- 关键词搜索和标签筛选
- 题目详情编辑

## 技术栈

- 前端：React 19 + Tailwind CSS + Vite
- 后端：FastAPI + Mangum（AWS Lambda）
- 认证：AWS Cognito
- 数据库：DynamoDB
- 图片存储：S3
- AI：Claude Vision（claude-sonnet-4-6）
- 基础设施：AWS SAM

## 快速部署

### 前置条件

- AWS CLI 已配置
- SAM CLI 已安装
- Node 18+, Python 3.12

### 设置 Anthropic API Key

```bash
aws ssm put-parameter \
  --name /error-book/anthropic-api-key \
  --value "your-api-key" \
  --type SecureString
```

### 一键部署

```bash
./deploy.sh
```

## 本地开发

```bash
# 后端测试
cd backend && pip install -r requirements.txt && python -m pytest tests/ -v

# 前端开发
cd frontend && npm install && npm run dev
```
