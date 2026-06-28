# 错题本系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建面向家长和学生的错题本系统，支持照片上传、Claude Vision 识别题目、标签分类和搜索管理。

**Architecture:** AWS SAM 管理全部基础设施（Cognito、API Gateway、Lambda、DynamoDB、S3、CloudFront）。后端为 FastAPI+Mangum 部署到单个 Lambda 函数，前端为 React 19+Tailwind 静态站点托管在 S3+CloudFront。图片由前端直传 S3（presigned URL），后端仅处理元数据和 Claude Vision 识别调用。

**Tech Stack:**
- 前端：React 19, Tailwind CSS, aws-amplify v6, Axios, Vite
- 后端：Python 3.12, FastAPI, Mangum, boto3, anthropic SDK
- 基础设施：AWS SAM, Cognito, API Gateway REST, Lambda, DynamoDB, S3, CloudFront

## Global Constraints

- Python 版本：3.12
- Node 版本：18+
- 前端框架：React 19（functional components only，无 class components）
- 样式：Tailwind CSS only，无 inline styles
- 组件最大行数：100 行，超出拆分子组件
- DynamoDB 表名：`ErrorBook`
- S3 图片 Bucket 名：`error-book-images-{accountId}-{region}`（通过 SAM 参数注入）
- 文件上传限制：`image/jpeg`, `image/png`, `image/webp`，单文件最大 10MB
- Claude 模型：`claude-sonnet-4-6`
- API 路径前缀：`/api/v1`（API Gateway stage 变量）
- 所有 API 须 JWT 鉴权，`userId` 从 JWT claims `sub` 字段提取
- 变量命名：Python 使用 camelCase（项目约定）

---

## 文件结构

```
error-book/
├── template.yaml                          # SAM 模板（所有 AWS 资源）
├── samconfig.toml                         # SAM 部署配置
├── backend/
│   ├── requirements.txt
│   ├── handler.py                         # Mangum 入口
│   ├── app.py                             # FastAPI app + CORS + 路由注册
│   ├── config.py                          # 环境变量读取
│   ├── auth.py                            # JWT claims 提取依赖
│   ├── routes/
│   │   ├── upload.py                      # GET /upload/presigned-url
│   │   ├── questions.py                   # 错题 CRUD
│   │   └── tags.py                        # 标签 CRUD
│   ├── services/
│   │   ├── recognition.py                 # Claude Vision 调用
│   │   ├── questionService.py             # DynamoDB 错题操作
│   │   └── tagService.py                  # DynamoDB 标签操作
│   ├── models/
│   │   ├── question.py                    # Pydantic 模型
│   │   └── tag.py                         # Pydantic 模型
│   └── tests/
│       ├── test_recognition.py
│       ├── test_question_service.py
│       ├── test_tag_service.py
│       └── test_routes.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/
        │   └── client.js                  # Axios 实例，自动带 JWT header
        ├── contexts/
        │   ├── AuthContext.jsx            # Cognito JWT 状态
        │   └── UploadContext.jsx          # 上传队列状态
        ├── components/
        │   ├── NavBar.jsx
        │   ├── SearchBar.jsx
        │   ├── TagBadge.jsx
        │   ├── ErrorCard.jsx
        │   ├── UploadDropzone.jsx
        │   └── UploadProgressCard.jsx
        └── pages/
            ├── LoginPage.jsx
            ├── DashboardPage.jsx
            ├── UploadPage.jsx
            ├── ErrorBankPage.jsx
            ├── ErrorDetailPage.jsx
            └── TagsPage.jsx
```

---

## Task 1: SAM 基础设施 — Cognito + DynamoDB + S3

**Files:**
- Create: `template.yaml`
- Create: `samconfig.toml`

**Interfaces:**
- Produces:
  - `UserPoolId` output（Task 6 前端 amplify 配置使用）
  - `UserPoolClientId` output（Task 6 前端 amplify 配置使用）
  - `ImagesBucketName` output（Task 3 后端 config 使用）
  - `TableName` output = `ErrorBook`

- [ ] **Step 1: 创建 template.yaml，定义 Cognito User Pool**

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Error Book - Mistake Tracking System

Globals:
  Function:
    Timeout: 30
    MemorySize: 512
    Runtime: python3.12
    Environment:
      Variables:
        TABLE_NAME: !Ref ErrorBookTable
        IMAGES_BUCKET: !Ref ImagesBucket
        COGNITO_USER_POOL_ID: !Ref UserPool
        ANTHROPIC_API_KEY: !Sub '{{resolve:ssm:/error-book/anthropic-api-key}}'

Resources:
  UserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      UserPoolName: error-book-user-pool
      AutoVerifiedAttributes:
        - email
      Policies:
        PasswordPolicy:
          MinimumLength: 8
          RequireUppercase: true
          RequireLowercase: true
          RequireNumbers: true
          RequireSymbols: false
      Schema:
        - AttributeDataType: String
          Name: email
          Required: true

  UserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties:
      ClientName: error-book-client
      UserPoolId: !Ref UserPool
      GenerateSecret: false
      ExplicitAuthFlows:
        - ALLOW_USER_PASSWORD_AUTH
        - ALLOW_REFRESH_TOKEN_AUTH
        - ALLOW_USER_SRP_AUTH
      AccessTokenValidity: 1
      RefreshTokenValidity: 30
      TokenValidityUnits:
        AccessToken: hours
        RefreshToken: days
```

- [ ] **Step 2: 添加 DynamoDB 表（含 GSI）**

```yaml
  ErrorBookTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: ErrorBook
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: tagPK
          AttributeType: S
        - AttributeName: createdAt
          AttributeType: S
        - AttributeName: content
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: TagIndex
          KeySchema:
            - AttributeName: tagPK
              KeyType: HASH
            - AttributeName: createdAt
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
        - IndexName: ContentIndex
          KeySchema:
            - AttributeName: PK
              KeyType: HASH
            - AttributeName: content
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
```

- [ ] **Step 3: 添加 S3 Bucket（图片存储）**

```yaml
  ImagesBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'error-book-images-${AWS::AccountId}-${AWS::Region}'
      CorsConfiguration:
        CorsRules:
          - AllowedHeaders: ['*']
            AllowedMethods: [GET, PUT, POST]
            AllowedOrigins: ['*']
            MaxAge: 3600
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
```

- [ ] **Step 4: 添加 Outputs**

```yaml
Outputs:
  UserPoolId:
    Value: !Ref UserPool
    Export:
      Name: ErrorBook-UserPoolId
  UserPoolClientId:
    Value: !Ref UserPoolClient
    Export:
      Name: ErrorBook-UserPoolClientId
  ImagesBucketName:
    Value: !Ref ImagesBucket
    Export:
      Name: ErrorBook-ImagesBucketName
```

- [ ] **Step 5: 创建 samconfig.toml**

```toml
version = 0.1

[default.deploy.parameters]
stack_name = "error-book"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
```

- [ ] **Step 6: 验证模板语法**

```bash
cd /workshop/error-book
sam validate --lint
```

期望输出：`template.yaml is a valid SAM Template`

- [ ] **Step 7: Commit**

```bash
git add template.yaml samconfig.toml
git commit -m "feat: add SAM infrastructure — Cognito, DynamoDB, S3"
```

---

## Task 2: 后端脚手架 — FastAPI + Mangum + 配置

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/auth.py`
- Create: `backend/app.py`
- Create: `backend/handler.py`
- Create: `backend/tests/__init__.py`

**Interfaces:**
- Produces:
  - `get_current_user_id(request: Request) -> str` — FastAPI 依赖，从 `requestContext.authorizer.claims.sub` 提取 userId
  - `app` — FastAPI 实例，供 handler.py 的 Mangum 包装

- [ ] **Step 1: 创建 requirements.txt**

```text
fastapi==0.115.0
mangum==0.19.0
boto3==1.35.0
anthropic==0.34.0
pydantic==2.9.0
python-multipart==0.0.12
```

- [ ] **Step 2: 创建 config.py**

```python
# backend/config.py
import os

tableName = os.environ["TABLE_NAME"]
imagesBucket = os.environ["IMAGES_BUCKET"]
cognitoUserPoolId = os.environ["COGNITO_USER_POOL_ID"]
anthropicApiKey = os.environ["ANTHROPIC_API_KEY"]
awsRegion = os.environ.get("AWS_REGION", "us-east-1")
```

- [ ] **Step 3: 创建 auth.py（JWT claims 提取）**

```python
# backend/auth.py
from fastapi import Request, HTTPException

def get_current_user_id(request: Request) -> str:
    # API Gateway JWT Authorizer 将 claims 注入 requestContext
    ctx = request.scope.get("aws.event", {})
    try:
        userId = ctx["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    except (KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return userId
```

- [ ] **Step 4: 创建 app.py**

```python
# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, questions, tags

app = FastAPI(title="Error Book API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(tags.router, prefix="/tags", tags=["tags"])
```

- [ ] **Step 5: 创建 handler.py（Mangum 入口）**

```python
# backend/handler.py
from mangum import Mangum
from app import app

handler = Mangum(app, lifespan="off")
```

- [ ] **Step 6: 创建测试目录**

```bash
mkdir -p /workshop/error-book/backend/tests
touch /workshop/error-book/backend/tests/__init__.py
touch /workshop/error-book/backend/routes/__init__.py
touch /workshop/error-book/backend/services/__init__.py
touch /workshop/error-book/backend/models/__init__.py
```

- [ ] **Step 7: 安装依赖并验证导入**

```bash
cd /workshop/error-book/backend
pip install -r requirements.txt -q
python -c "from app import app; print('OK')"
```

期望输出：`OK`

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: add FastAPI + Mangum backend scaffold"
```

---

## Task 3: 后端 — Pydantic 模型

**Files:**
- Create: `backend/models/question.py`
- Create: `backend/models/tag.py`

**Interfaces:**
- Produces:
  - `Question` — DynamoDB 记录的完整模型
  - `QuestionCreate` — 识别请求输入模型
  - `QuestionUpdate` — 编辑请求输入模型
  - `Tag` — 标签完整模型
  - `TagCreate` — 创建标签输入模型
  - `TagUpdate` — 编辑标签输入模型

- [ ] **Step 1: 创建 question.py**

```python
# backend/models/question.py
from pydantic import BaseModel
from typing import List, Optional

class QuestionCreate(BaseModel):
    imageKey: str          # S3 object key，格式 {userId}/{questionId}/{filename}
    subject: Optional[str] = None

class QuestionUpdate(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    analysis: Optional[str] = None
    tags: Optional[List[str]] = None

class Question(BaseModel):
    questionId: str
    userId: str
    imageKey: str
    imageUrl: str          # S3 presigned GET URL，供前端展示
    subject: str
    content: str
    analysis: str
    tags: List[str]
    status: str            # pending / done / failed
    createdAt: str
```

- [ ] **Step 2: 创建 tag.py**

```python
# backend/models/tag.py
from pydantic import BaseModel
from typing import Optional

class TagCreate(BaseModel):
    name: str
    color: str             # hex 颜色，如 "#FF5733"

class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class Tag(BaseModel):
    tagId: str
    userId: str
    name: str
    color: str
    createdAt: str
```

- [ ] **Step 3: 验证模型**

```bash
cd /workshop/error-book/backend
python -c "
from models.question import Question, QuestionCreate, QuestionUpdate
from models.tag import Tag, TagCreate, TagUpdate
print('models OK')
"
```

期望输出：`models OK`

- [ ] **Step 4: Commit**

```bash
git add backend/models/
git commit -m "feat: add Pydantic models for Question and Tag"
```

---

## Task 4: 后端 — TagService（DynamoDB 标签 CRUD）

**Files:**
- Create: `backend/services/tagService.py`
- Create: `backend/tests/test_tag_service.py`

**Interfaces:**
- Consumes: `Tag`, `TagCreate`, `TagUpdate`（Task 3）
- Produces:
  - `TagService.create_tag(userId: str, data: TagCreate) -> Tag`
  - `TagService.list_tags(userId: str) -> List[Tag]`
  - `TagService.update_tag(userId: str, tagId: str, data: TagUpdate) -> Tag`
  - `TagService.delete_tag(userId: str, tagId: str) -> None`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_tag_service.py
import pytest
from unittest.mock import MagicMock, patch
from models.tag import TagCreate, TagUpdate
from services.tagService import TagService

@pytest.fixture
def mock_table():
    with patch("services.tagService.boto3.resource") as mock_resource:
        table = MagicMock()
        mock_resource.return_value.Table.return_value = table
        yield table

def test_create_tag(mock_table):
    mock_table.put_item.return_value = {}
    svc = TagService()
    tag = svc.create_tag("user1", TagCreate(name="数学", color="#FF5733"))
    assert tag.name == "数学"
    assert tag.color == "#FF5733"
    assert tag.userId == "user1"
    assert tag.tagId is not None
    mock_table.put_item.assert_called_once()

def test_list_tags(mock_table):
    mock_table.query.return_value = {"Items": [
        {"PK": "USER#user1", "SK": "TAG#tag1", "tagId": "tag1",
         "userId": "user1", "name": "数学", "color": "#FF5733", "createdAt": "2026-06-28T00:00:00Z"}
    ]}
    svc = TagService()
    tags = svc.list_tags("user1")
    assert len(tags) == 1
    assert tags[0].name == "数学"

def test_delete_tag(mock_table):
    mock_table.delete_item.return_value = {}
    svc = TagService()
    svc.delete_tag("user1", "tag1")
    mock_table.delete_item.assert_called_once_with(
        Key={"PK": "USER#user1", "SK": "TAG#tag1"}
    )
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /workshop/error-book/backend
python -m pytest tests/test_tag_service.py -v 2>&1 | head -20
```

期望：`ImportError` 或 `ModuleNotFoundError`（TagService 尚未实现）

- [ ] **Step 3: 实现 TagService**

```python
# backend/services/tagService.py
import boto3
import uuid
from datetime import datetime, timezone
from typing import List
from models.tag import Tag, TagCreate, TagUpdate
from config import tableName, awsRegion

class TagService:
    def __init__(self):
        self.table = boto3.resource("dynamodb", region_name=awsRegion).Table(tableName)

    def create_tag(self, userId: str, data: TagCreate) -> Tag:
        tagId = str(uuid.uuid4())
        createdAt = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": f"USER#{userId}",
            "SK": f"TAG#{tagId}",
            "tagId": tagId,
            "userId": userId,
            "name": data.name,
            "color": data.color,
            "createdAt": createdAt,
        }
        self.table.put_item(Item=item)
        return Tag(**{k: v for k, v in item.items() if k in Tag.model_fields})

    def list_tags(self, userId: str) -> List[Tag]:
        resp = self.table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
            ExpressionAttributeValues={":pk": f"USER#{userId}", ":prefix": "TAG#"},
        )
        return [Tag(**{k: v for k, v in item.items() if k in Tag.model_fields})
                for item in resp["Items"]]

    def update_tag(self, userId: str, tagId: str, data: TagUpdate) -> Tag:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
        names = {f"#{k}": k for k in updates}
        values = {f":{k}": v for k, v in updates.items()}
        resp = self.table.update_item(
            Key={"PK": f"USER#{userId}", "SK": f"TAG#{tagId}"},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        item = resp["Attributes"]
        return Tag(**{k: v for k, v in item.items() if k in Tag.model_fields})

    def delete_tag(self, userId: str, tagId: str) -> None:
        self.table.delete_item(Key={"PK": f"USER#{userId}", "SK": f"TAG#{tagId}"})
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /workshop/error-book/backend
python -m pytest tests/test_tag_service.py -v
```

期望：`3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/services/tagService.py backend/tests/test_tag_service.py
git commit -m "feat: add TagService with DynamoDB CRUD"
```

---

## Task 5: 后端 — Recognition Service（Claude Vision）

**Files:**
- Create: `backend/services/recognition.py`
- Create: `backend/tests/test_recognition.py`

**Interfaces:**
- Produces:
  - `RecognitionService.recognize(imageKey: str) -> dict` — 返回 `{subject, content, analysis}`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_recognition.py
import pytest
from unittest.mock import MagicMock, patch

def test_recognize_returns_structured_data():
    with patch("services.recognition.anthropic.Anthropic") as MockClient, \
         patch("services.recognition.boto3.client") as mock_s3:
        # mock S3 get_object
        mock_s3.return_value.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-image-bytes"),
            "ContentType": "image/jpeg",
        }
        # mock Claude response
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"subject":"数学","content":"1+1=?","analysis":"加法运算"}')]
        MockClient.return_value.messages.create.return_value = mock_msg

        from services.recognition import RecognitionService
        svc = RecognitionService()
        result = svc.recognize("user1/q1/photo.jpg")

        assert result["subject"] == "数学"
        assert result["content"] == "1+1=?"
        assert result["analysis"] == "加法运算"

def test_recognize_raises_on_invalid_json():
    with patch("services.recognition.anthropic.Anthropic") as MockClient, \
         patch("services.recognition.boto3.client") as mock_s3:
        mock_s3.return_value.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-image-bytes"),
            "ContentType": "image/jpeg",
        }
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="invalid json")]
        MockClient.return_value.messages.create.return_value = mock_msg

        from services.recognition import RecognitionService
        svc = RecognitionService()
        with pytest.raises(ValueError, match="识别结果解析失败"):
            svc.recognize("user1/q1/photo.jpg")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /workshop/error-book/backend
python -m pytest tests/test_recognition.py -v 2>&1 | head -20
```

期望：`ImportError`（RecognitionService 尚未实现）

- [ ] **Step 3: 实现 RecognitionService**

```python
# backend/services/recognition.py
import base64
import json
import boto3
import anthropic
from config import imagesBucket, anthropicApiKey, awsRegion

PROMPT = """请分析这道题目图片，以JSON格式返回以下字段：
{
  "subject": "科目（数学/语文/英语/物理/化学/生物/历史/地理/政治/其他）",
  "content": "题目完整文字内容",
  "analysis": "这道题的考点分析和解题思路"
}
只返回JSON，不要其他文字。"""

class RecognitionService:
    def __init__(self):
        self.s3 = boto3.client("s3", region_name=awsRegion)
        self.client = anthropic.Anthropic(api_key=anthropicApiKey)

    def recognize(self, imageKey: str) -> dict:
        obj = self.s3.get_object(Bucket=imagesBucket, Key=imageKey)
        imageBytes = obj["Body"].read()
        contentType = obj.get("ContentType", "image/jpeg")
        imageB64 = base64.standard_b64encode(imageBytes).decode("utf-8")

        msg = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": contentType, "data": imageB64}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        )
        rawText = msg.content[0].text.strip()
        try:
            return json.loads(rawText)
        except json.JSONDecodeError:
            raise ValueError(f"识别结果解析失败: {rawText[:200]}")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /workshop/error-book/backend
python -m pytest tests/test_recognition.py -v
```

期望：`2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/services/recognition.py backend/tests/test_recognition.py
git commit -m "feat: add RecognitionService using Claude Vision"
```

---

## Task 6: 后端 — QuestionService（DynamoDB 错题 CRUD）

**Files:**
- Create: `backend/services/questionService.py`
- Create: `backend/tests/test_question_service.py`

**Interfaces:**
- Consumes: `Question`, `QuestionCreate`, `QuestionUpdate`（Task 3）；`RecognitionService.recognize`（Task 5）
- Produces:
  - `QuestionService.create_question(userId: str, data: QuestionCreate) -> Question`
  - `QuestionService.list_questions(userId: str, tagId: str | None, keyword: str | None, lastKey: str | None) -> dict`（返回 `{items: List[Question], nextKey: str | None}`）
  - `QuestionService.get_question(userId: str, questionId: str) -> Question`
  - `QuestionService.update_question(userId: str, questionId: str, data: QuestionUpdate) -> Question`
  - `QuestionService.delete_question(userId: str, questionId: str) -> None`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_question_service.py
import pytest
from unittest.mock import MagicMock, patch
from models.question import QuestionCreate, QuestionUpdate
from services.questionService import QuestionService

@pytest.fixture
def mock_deps():
    with patch("services.questionService.boto3.resource") as mock_resource, \
         patch("services.questionService.RecognitionService") as MockRecog, \
         patch("services.questionService.boto3.client") as mock_s3_client:
        table = MagicMock()
        mock_resource.return_value.Table.return_value = table
        recog = MagicMock()
        recog.recognize.return_value = {"subject": "数学", "content": "1+1=?", "analysis": "加法"}
        MockRecog.return_value = recog
        s3 = MagicMock()
        s3.generate_presigned_url.return_value = "https://s3.example.com/img.jpg"
        mock_s3_client.return_value = s3
        yield table, recog, s3

def test_create_question(mock_deps):
    table, recog, s3 = mock_deps
    table.put_item.return_value = {}
    svc = QuestionService()
    q = svc.create_question("user1", QuestionCreate(imageKey="user1/q1/photo.jpg"))
    assert q.status == "done"
    assert q.subject == "数学"
    assert q.content == "1+1=?"
    assert q.userId == "user1"

def test_create_question_failed_recognition(mock_deps):
    table, recog, s3 = mock_deps
    recog.recognize.side_effect = ValueError("识别结果解析失败: ...")
    table.put_item.return_value = {}
    svc = QuestionService()
    q = svc.create_question("user1", QuestionCreate(imageKey="user1/q1/photo.jpg"))
    assert q.status == "failed"

def test_list_questions_no_filter(mock_deps):
    table, _, s3 = mock_deps
    table.query.return_value = {"Items": [
        {"PK": "USER#user1", "SK": "QUESTION#q1", "questionId": "q1",
         "userId": "user1", "imageKey": "user1/q1/p.jpg", "subject": "数学",
         "content": "1+1", "analysis": "加法", "tags": [], "status": "done",
         "createdAt": "2026-06-28T00:00:00Z"}
    ]}
    svc = QuestionService()
    result = svc.list_questions("user1", tagId=None, keyword=None, lastKey=None)
    assert len(result["items"]) == 1

def test_delete_question(mock_deps):
    table, _, _ = mock_deps
    table.delete_item.return_value = {}
    svc = QuestionService()
    svc.delete_question("user1", "q1")
    table.delete_item.assert_called_once_with(
        Key={"PK": "USER#user1", "SK": "QUESTION#q1"}
    )
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /workshop/error-book/backend
python -m pytest tests/test_question_service.py -v 2>&1 | head -20
```

期望：`ImportError`

- [ ] **Step 3: 实现 QuestionService**

```python
# backend/services/questionService.py
import boto3
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from models.question import Question, QuestionCreate, QuestionUpdate
from services.recognition import RecognitionService
from config import tableName, imagesBucket, awsRegion

class QuestionService:
    def __init__(self):
        self.table = boto3.resource("dynamodb", region_name=awsRegion).Table(tableName)
        self.s3 = boto3.client("s3", region_name=awsRegion)
        self.recog = RecognitionService()

    def _presign(self, imageKey: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": imagesBucket, "Key": imageKey},
            ExpiresIn=3600,
        )

    def _item_to_question(self, item: dict) -> Question:
        return Question(
            questionId=item["questionId"],
            userId=item["userId"],
            imageKey=item["imageKey"],
            imageUrl=self._presign(item["imageKey"]),
            subject=item.get("subject", ""),
            content=item.get("content", ""),
            analysis=item.get("analysis", ""),
            tags=item.get("tags", []),
            status=item["status"],
            createdAt=item["createdAt"],
        )

    def create_question(self, userId: str, data: QuestionCreate) -> Question:
        questionId = str(uuid.uuid4())
        createdAt = datetime.now(timezone.utc).isoformat()
        status = "done"
        subject, content, analysis = data.subject or "", "", ""
        try:
            result = self.recog.recognize(data.imageKey)
            subject = result.get("subject", subject)
            content = result.get("content", "")
            analysis = result.get("analysis", "")
        except Exception:
            status = "failed"

        item = {
            "PK": f"USER#{userId}",
            "SK": f"QUESTION#{questionId}",
            "questionId": questionId,
            "userId": userId,
            "imageKey": data.imageKey,
            "subject": subject,
            "content": content,
            "analysis": analysis,
            "tags": [],
            "status": status,
            "createdAt": createdAt,
        }
        for attempt in range(3):
            try:
                self.table.put_item(Item=item)
                break
            except Exception:
                if attempt == 2:
                    raise
        return self._item_to_question(item)

    def list_questions(self, userId: str, tagId: Optional[str], keyword: Optional[str], lastKey: Optional[str]) -> dict:
        kwargs: dict = {}
        if lastKey:
            import json, base64
            kwargs["ExclusiveStartKey"] = json.loads(base64.b64decode(lastKey))

        if tagId:
            resp = self.table.query(
                IndexName="TagIndex",
                KeyConditionExpression="tagPK = :tagpk",
                ExpressionAttributeValues={":tagpk": f"USER#{userId}#TAG#{tagId}"},
                **kwargs,
            )
        elif keyword:
            resp = self.table.query(
                IndexName="ContentIndex",
                KeyConditionExpression="PK = :pk AND begins_with(content, :kw)",
                ExpressionAttributeValues={":pk": f"USER#{userId}", ":kw": keyword},
                **kwargs,
            )
        else:
            resp = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
                ExpressionAttributeValues={":pk": f"USER#{userId}", ":prefix": "QUESTION#"},
                ScanIndexForward=False,
                **kwargs,
            )

        nextKey = None
        if "LastEvaluatedKey" in resp:
            import json, base64
            nextKey = base64.b64encode(json.dumps(resp["LastEvaluatedKey"]).encode()).decode()

        return {"items": [self._item_to_question(i) for i in resp["Items"]], "nextKey": nextKey}

    def get_question(self, userId: str, questionId: str) -> Question:
        resp = self.table.get_item(Key={"PK": f"USER#{userId}", "SK": f"QUESTION#{questionId}"})
        item = resp.get("Item")
        if not item:
            raise KeyError(f"Question {questionId} not found")
        return self._item_to_question(item)

    def update_question(self, userId: str, questionId: str, data: QuestionUpdate) -> Question:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
        names = {f"#{k}": k for k in updates}
        values = {f":{k}": v for k, v in updates.items()}
        resp = self.table.update_item(
            Key={"PK": f"USER#{userId}", "SK": f"QUESTION#{questionId}"},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return self._item_to_question(resp["Attributes"])

    def delete_question(self, userId: str, questionId: str) -> None:
        self.table.delete_item(Key={"PK": f"USER#{userId}", "SK": f"QUESTION#{questionId}"})
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /workshop/error-book/backend
python -m pytest tests/test_question_service.py -v
```

期望：`4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/services/questionService.py backend/tests/test_question_service.py
git commit -m "feat: add QuestionService with DynamoDB CRUD and recognition"
```

---

## Task 7: 后端 — API 路由层

**Files:**
- Create: `backend/routes/upload.py`
- Create: `backend/routes/questions.py`
- Create: `backend/routes/tags.py`
- Create: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: `get_current_user_id`（Task 2）；`QuestionService`（Task 6）；`TagService`（Task 4）

- [ ] **Step 1: 创建 upload.py（presigned URL 生成）**

```python
# backend/routes/upload.py
import boto3
import uuid
from fastapi import APIRouter, Depends, Request, Query
from auth import get_current_user_id
from config import imagesBucket, awsRegion

router = APIRouter()

@router.get("/presigned-url")
def get_presigned_url(
    request: Request,
    filename: str = Query(...),
    contentType: str = Query(...),
    userId: str = Depends(get_current_user_id),
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if contentType not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    questionId = str(uuid.uuid4())
    key = f"{userId}/{questionId}/{filename}"
    s3 = boto3.client("s3", region_name=awsRegion)
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": imagesBucket, "Key": key, "ContentType": contentType},
        ExpiresIn=900,
    )
    return {"url": url, "key": key, "questionId": questionId}
```

- [ ] **Step 2: 创建 questions.py（错题 CRUD）**

```python
# backend/routes/questions.py
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from typing import Optional
from auth import get_current_user_id
from services.questionService import QuestionService
from models.question import QuestionCreate, QuestionUpdate

router = APIRouter()

@router.post("/recognize")
def recognize_question(
    request: Request,
    data: QuestionCreate,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    return svc.create_question(userId, data)

@router.get("")
def list_questions(
    request: Request,
    tagId: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    lastKey: Optional[str] = Query(None),
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    return svc.list_questions(userId, tagId=tagId, keyword=keyword, lastKey=lastKey)

@router.get("/{questionId}")
def get_question(
    questionId: str,
    request: Request,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    try:
        return svc.get_question(userId, questionId)
    except KeyError:
        raise HTTPException(status_code=404, detail="题目不存在")

@router.put("/{questionId}")
def update_question(
    questionId: str,
    data: QuestionUpdate,
    request: Request,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    return svc.update_question(userId, questionId, data)

@router.delete("/{questionId}")
def delete_question(
    questionId: str,
    request: Request,
    userId: str = Depends(get_current_user_id),
):
    svc = QuestionService()
    svc.delete_question(userId, questionId)
    return {"message": "删除成功"}
```

- [ ] **Step 3: 创建 tags.py（标签 CRUD）**

```python
# backend/routes/tags.py
from fastapi import APIRouter, Depends, Request, HTTPException
from auth import get_current_user_id
from services.tagService import TagService
from models.tag import TagCreate, TagUpdate

router = APIRouter()

@router.get("")
def list_tags(request: Request, userId: str = Depends(get_current_user_id)):
    return TagService().list_tags(userId)

@router.post("")
def create_tag(data: TagCreate, request: Request, userId: str = Depends(get_current_user_id)):
    return TagService().create_tag(userId, data)

@router.put("/{tagId}")
def update_tag(tagId: str, data: TagUpdate, request: Request, userId: str = Depends(get_current_user_id)):
    return TagService().update_tag(userId, tagId, data)

@router.delete("/{tagId}")
def delete_tag(tagId: str, request: Request, userId: str = Depends(get_current_user_id)):
    TagService().delete_tag(userId, tagId)
    return {"message": "删除成功"}
```

- [ ] **Step 4: 写路由集成测试**

```python
# backend/tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    with patch("auth.get_current_user_id", return_value="user1"):
        from app import app
        return TestClient(app)

def test_list_tags_returns_200(client):
    with patch("routes.tags.TagService") as MockSvc:
        MockSvc.return_value.list_tags.return_value = []
        resp = client.get("/tags", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        assert resp.json() == []

def test_create_tag_returns_tag(client):
    from models.tag import Tag
    fake_tag = Tag(tagId="t1", userId="user1", name="数学", color="#FF0000", createdAt="2026-06-28T00:00:00Z")
    with patch("routes.tags.TagService") as MockSvc:
        MockSvc.return_value.create_tag.return_value = fake_tag
        resp = client.post("/tags", json={"name": "数学", "color": "#FF0000"},
                           headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "数学"

def test_get_question_404(client):
    with patch("routes.questions.QuestionService") as MockSvc:
        MockSvc.return_value.get_question.side_effect = KeyError("not found")
        resp = client.get("/questions/nonexistent", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 404
```

- [ ] **Step 5: 运行路由测试**

```bash
cd /workshop/error-book/backend
python -m pytest tests/test_routes.py -v
```

期望：`3 passed`

- [ ] **Step 6: 运行全部测试**

```bash
cd /workshop/error-book/backend
python -m pytest tests/ -v
```

期望：全部 pass

- [ ] **Step 7: Commit**

```bash
git add backend/routes/ backend/tests/test_routes.py
git commit -m "feat: add API routes for upload, questions, and tags"
```

---

## Task 8: SAM 模板 — Lambda + API Gateway

**Files:**
- Modify: `template.yaml`（添加 Lambda Function、API Gateway、IAM Role）

**Interfaces:**
- Consumes: Cognito UserPool（Task 1）；DynamoDB Table（Task 1）；S3 ImagesBucket（Task 1）
- Produces:
  - `ApiEndpoint` output（Task 11 前端 client.js 使用）

- [ ] **Step 1: 在 template.yaml 添加 Lambda Function 和 IAM Role**

```yaml
  # 在 Resources 下添加：

  BackendFunctionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: ErrorBookPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:GetItem
                  - dynamodb:PutItem
                  - dynamodb:UpdateItem
                  - dynamodb:DeleteItem
                  - dynamodb:Query
                Resource:
                  - !GetAtt ErrorBookTable.Arn
                  - !Sub '${ErrorBookTable.Arn}/index/*'
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub '${ImagesBucket.Arn}/*'
              - Effect: Allow
                Action: s3:GeneratePresignedUrl
                Resource: '*'

  BackendFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: backend/
      Handler: handler.handler
      Role: !GetAtt BackendFunctionRole.Arn
      Events:
        ApiProxy:
          Type: Api
          Properties:
            RestApiId: !Ref ErrorBookApi
            Path: /{proxy+}
            Method: ANY
            Auth:
              Authorizer: CognitoAuthorizer
```

- [ ] **Step 2: 添加 API Gateway（REST API + JWT Authorizer）**

```yaml
  ErrorBookApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Cors:
        AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
        AllowHeaders: "'Content-Type,Authorization'"
        AllowOrigin: "'*'"
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt UserPool.Arn
            AuthorizationScopes:
              - openid
```

- [ ] **Step 3: 添加 ApiEndpoint 到 Outputs**

```yaml
  ApiEndpoint:
    Value: !Sub 'https://${ErrorBookApi}.execute-api.${AWS::Region}.amazonaws.com/prod'
    Export:
      Name: ErrorBook-ApiEndpoint
```

- [ ] **Step 4: 验证模板**

```bash
sam validate --lint
```

期望：`template.yaml is a valid SAM Template`

- [ ] **Step 5: Commit**

```bash
git add template.yaml
git commit -m "feat: add Lambda function and API Gateway to SAM template"
```

---

## Task 9: 前端脚手架 — Vite + React 19 + Tailwind

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/index.css`

**Interfaces:**
- Produces: 可运行的 Vite 开发服务器，访问 `http://localhost:5173` 显示骨架页面

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "error-book-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^6.26.0",
    "aws-amplify": "^6.6.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

- [ ] **Step 2: 创建 vite.config.js**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
})
```

- [ ] **Step 3: 创建 tailwind.config.js**

```js
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 4: 创建 postcss.config.js**

```js
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
```

- [ ] **Step 5: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>错题本</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 6: 创建 src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 7: 创建 src/main.jsx**

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 8: 创建 src/App.jsx（骨架）**

```jsx
export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <h1 className="text-3xl font-bold text-indigo-600">错题本</h1>
    </div>
  )
}
```

- [ ] **Step 9: 安装依赖**

```bash
cd /workshop/error-book/frontend
npm install
```

- [ ] **Step 10: 验证构建**

```bash
cd /workshop/error-book/frontend
npm run build 2>&1 | tail -5
```

期望：`✓ built in` 相关输出，无 error

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React 19 + Tailwind frontend with Vite"
```

---

## Task 10: 前端 — AuthContext + LoginPage

**Files:**
- Create: `frontend/src/contexts/AuthContext.jsx`
- Create: `frontend/src/pages/LoginPage.jsx`

**Interfaces:**
- Produces:
  - `useAuth()` hook — 返回 `{ user, signIn, signUp, signOut, confirmSignUp, getToken }`
  - `LoginPage` — 登录/注册/验证码三状态表单

- [ ] **Step 1: 创建 AuthContext.jsx**

```jsx
// frontend/src/contexts/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react'
import { Amplify } from 'aws-amplify'
import { signIn, signUp, signOut, confirmSignUp, fetchAuthSession, getCurrentUser } from 'aws-amplify/auth'

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
      loginWith: { email: true },
    },
  },
})

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  async function getToken() {
    const session = await fetchAuthSession()
    return session.tokens?.accessToken?.toString()
  }

  const value = {
    user,
    loading,
    getToken,
    signIn: async (email, password) => {
      const result = await signIn({ username: email, password })
      const u = await getCurrentUser()
      setUser(u)
      return result
    },
    signUp: (email, password) => signUp({ username: email, password, options: { userAttributes: { email } } }),
    confirmSignUp: (email, code) => confirmSignUp({ username: email, confirmationCode: code }),
    signOut: async () => { await signOut(); setUser(null) },
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center"><span className="text-gray-500">加载中...</span></div>

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
```

- [ ] **Step 2: 创建 LoginPage.jsx**

```jsx
// frontend/src/pages/LoginPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { signIn, signUp, confirmSignUp } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')  // login | register | confirm
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await signIn(email, password)
        navigate('/')
      } else if (mode === 'register') {
        await signUp(email, password)
        setMode('confirm')
      } else {
        await confirmSignUp(email, code)
        setMode('login')
      }
    } catch (err) {
      setError(err.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-md p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-indigo-600 mb-6 text-center">错题本</h1>
        <h2 className="text-lg font-semibold text-gray-700 mb-4 text-center">
          {mode === 'login' ? '登录' : mode === 'register' ? '注册' : '验证邮箱'}
        </h2>
        {error && <p className="text-red-500 text-sm mb-4 text-center">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode !== 'confirm' && (
            <>
              <input type="email" placeholder="邮箱" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" required />
              <input type="password" placeholder="密码（8位以上，含大小写和数字）" value={password} onChange={e => setPassword(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" required />
            </>
          )}
          {mode === 'confirm' && (
            <input type="text" placeholder="请输入邮箱验证码" value={code} onChange={e => setCode(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" required />
          )}
          <button type="submit" disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50">
            {loading ? '处理中...' : mode === 'login' ? '登录' : mode === 'register' ? '注册' : '验证'}
          </button>
        </form>
        {mode !== 'confirm' && (
          <p className="text-center text-sm text-gray-500 mt-4">
            {mode === 'login' ? '没有账号？' : '已有账号？'}
            <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              className="text-indigo-600 font-medium ml-1 hover:underline">
              {mode === 'login' ? '注册' : '登录'}
            </button>
          </p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 创建 .env.local 模板**

```bash
cat > /workshop/error-book/frontend/.env.local.example << 'EOF'
VITE_USER_POOL_ID=us-east-1_XXXXXXXXX
VITE_USER_POOL_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
VITE_API_BASE_URL=https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod
EOF
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/contexts/AuthContext.jsx frontend/src/pages/LoginPage.jsx frontend/src/pages/ frontend/.env.local.example
git commit -m "feat: add AuthContext with Cognito and LoginPage"
```

---

## Task 11: 前端 — API Client + UploadContext

**Files:**
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/contexts/UploadContext.jsx`

**Interfaces:**
- Consumes: `useAuth().getToken()`（Task 10）
- Produces:
  - `apiClient` — Axios 实例，自动带 JWT header，401 时自动刷新
  - `useUpload()` hook — 返回 `{ queue, addFiles, retryFile }`，queue 为 `[{id, file, status, question}]`

- [ ] **Step 1: 创建 api/client.js**

```js
// frontend/src/api/client.js
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})

let getTokenFn = null

export function setTokenGetter(fn) {
  getTokenFn = fn
}

apiClient.interceptors.request.use(async config => {
  if (getTokenFn) {
    const token = await getTokenFn()
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default apiClient
```

- [ ] **Step 2: 创建 UploadContext.jsx**

```jsx
// frontend/src/contexts/UploadContext.jsx
import { createContext, useContext, useState, useCallback } from 'react'
import apiClient from '../api/client'

const UploadContext = createContext(null)

export function UploadProvider({ children }) {
  const [queue, setQueue] = useState([])

  function updateItem(id, patch) {
    setQueue(q => q.map(item => item.id === id ? { ...item, ...patch } : item))
  }

  async function processFile(id, file) {
    updateItem(id, { status: 'uploading' })
    try {
      // 1. 获取 presigned URL
      const { data: { url, key } } = await apiClient.get('/upload/presigned-url', {
        params: { filename: file.name, contentType: file.type },
      })
      // 2. 直传 S3
      await axios.put(url, file, { headers: { 'Content-Type': file.type } })
      updateItem(id, { status: 'recognizing' })
      // 3. 触发识别
      const { data: question } = await apiClient.post('/questions/recognize', { imageKey: key })
      updateItem(id, { status: question.status === 'failed' ? 'failed' : 'done', question })
    } catch {
      updateItem(id, { status: 'failed' })
    }
  }

  const addFiles = useCallback((files) => {
    const newItems = Array.from(files).map(file => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      question: null,
    }))
    setQueue(q => [...q, ...newItems])
    newItems.forEach(item => processFile(item.id, item.file))
  }, [])

  const retryFile = useCallback((id) => {
    const item = queue.find(i => i.id === id)
    if (item) processFile(id, item.file)
  }, [queue])

  return (
    <UploadContext.Provider value={{ queue, addFiles, retryFile }}>
      {children}
    </UploadContext.Provider>
  )
}

export function useUpload() {
  return useContext(UploadContext)
}
```

注意：在 processFile 中的 `axios.put` 需要从 axios 单独导入（非 apiClient），因为 S3 直传不需要 JWT header。在文件顶部添加：

```js
import axios from 'axios'
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/ frontend/src/contexts/UploadContext.jsx
git commit -m "feat: add API client with JWT interceptor and UploadContext"
```

---

## Task 12: 前端 — 基础组件

**Files:**
- Create: `frontend/src/components/NavBar.jsx`
- Create: `frontend/src/components/TagBadge.jsx`
- Create: `frontend/src/components/SearchBar.jsx`
- Create: `frontend/src/components/ErrorCard.jsx`
- Create: `frontend/src/components/UploadDropzone.jsx`
- Create: `frontend/src/components/UploadProgressCard.jsx`

**Interfaces:**
- Consumes: `useAuth().signOut()`（Task 10）；`useUpload()`（Task 11）
- Produces: 可复用 UI 组件，供各页面使用

- [ ] **Step 1: 创建 NavBar.jsx**

```jsx
// frontend/src/components/NavBar.jsx
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function NavBar() {
  const { signOut } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await signOut()
    navigate('/login')
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold text-indigo-600">错题本</Link>
      <div className="flex items-center gap-6">
        <Link to="/" className="text-sm text-gray-600 hover:text-indigo-600">概览</Link>
        <Link to="/upload" className="text-sm text-gray-600 hover:text-indigo-600">上传题目</Link>
        <Link to="/errors" className="text-sm text-gray-600 hover:text-indigo-600">错题库</Link>
        <Link to="/tags" className="text-sm text-gray-600 hover:text-indigo-600">标签管理</Link>
        <button onClick={handleSignOut} className="text-sm text-gray-400 hover:text-red-500">退出</button>
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: 创建 TagBadge.jsx**

```jsx
// frontend/src/components/TagBadge.jsx
export default function TagBadge({ name, color, onRemove }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white"
      style={{ backgroundColor: color }}>
      {name}
      {onRemove && (
        <button onClick={onRemove} className="hover:opacity-70 leading-none">&times;</button>
      )}
    </span>
  )
}
```

- [ ] **Step 3: 创建 SearchBar.jsx**

```jsx
// frontend/src/components/SearchBar.jsx
import { useState } from 'react'

export default function SearchBar({ onSearch, placeholder = '搜索题目内容...' }) {
  const [value, setValue] = useState('')

  function handleKeyDown(e) {
    if (e.key === 'Enter') onSearch(value.trim())
  }

  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full border border-gray-300 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <span className="absolute left-3 top-2.5 text-gray-400 text-sm">🔍</span>
    </div>
  )
}
```

- [ ] **Step 4: 创建 ErrorCard.jsx**

```jsx
// frontend/src/components/ErrorCard.jsx
import { Link } from 'react-router-dom'
import TagBadge from './TagBadge'

export default function ErrorCard({ question, tags = [] }) {
  const tagMap = Object.fromEntries(tags.map(t => [t.tagId, t]))

  return (
    <Link to={`/errors/${question.questionId}`}
      className="block bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
      <div className="flex gap-3">
        {question.imageUrl && (
          <img src={question.imageUrl} alt="题目图片"
            className="w-20 h-20 object-cover rounded-lg flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
              {question.subject || '未分类'}
            </span>
            <span className="text-xs text-gray-400">{question.createdAt?.slice(0, 10)}</span>
          </div>
          <p className="text-sm text-gray-700 line-clamp-2">{question.content || '识别失败'}</p>
          {question.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {question.tags.map(tagId => tagMap[tagId] && (
                <TagBadge key={tagId} name={tagMap[tagId].name} color={tagMap[tagId].color} />
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}
```

- [ ] **Step 5: 创建 UploadDropzone.jsx**

```jsx
// frontend/src/components/UploadDropzone.jsx
import { useRef, useState } from 'react'
import { useUpload } from '../contexts/UploadContext'

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp']
const MAX_SIZE = 10 * 1024 * 1024

export default function UploadDropzone() {
  const { addFiles } = useUpload()
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  function validate(files) {
    return Array.from(files).filter(f => ACCEPTED.includes(f.type) && f.size <= MAX_SIZE)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const valid = validate(e.dataTransfer.files)
    if (valid.length) addFiles(valid)
  }

  function handleChange(e) {
    const valid = validate(e.target.files)
    if (valid.length) addFiles(valid)
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors
        ${dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 hover:border-indigo-300'}`}>
      <p className="text-4xl mb-3">📷</p>
      <p className="text-gray-600 font-medium">点击或拖拽图片到此处上传</p>
      <p className="text-gray-400 text-sm mt-1">支持 JPG、PNG、WebP，单张最大 10MB</p>
      <input ref={inputRef} type="file" accept={ACCEPTED.join(',')} multiple onChange={handleChange} className="hidden" />
    </div>
  )
}
```

- [ ] **Step 6: 创建 UploadProgressCard.jsx**

```jsx
// frontend/src/components/UploadProgressCard.jsx
const STATUS_LABEL = {
  pending: '等待中...',
  uploading: '上传中...',
  recognizing: '识别中...',
  done: '完成 ✓',
  failed: '识别失败',
}

const STATUS_COLOR = {
  pending: 'bg-gray-200',
  uploading: 'bg-blue-400',
  recognizing: 'bg-yellow-400',
  done: 'bg-green-400',
  failed: 'bg-red-400',
}

export default function UploadProgressCard({ item, onRetry }) {
  const { file, status } = item
  const isDone = status === 'done'
  const isFailed = status === 'failed'
  const progress = { pending: 0, uploading: 40, recognizing: 75, done: 100, failed: 100 }[status]

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{isFailed ? '❌' : isDone ? '✅' : '🖼️'}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
          <p className={`text-xs mt-0.5 ${isFailed ? 'text-red-500' : 'text-gray-400'}`}>
            {STATUS_LABEL[status]}
          </p>
        </div>
        {isFailed && (
          <button onClick={() => onRetry(item.id)}
            className="text-xs text-indigo-600 hover:underline flex-shrink-0">重试</button>
        )}
      </div>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full transition-all duration-500 ${STATUS_COLOR[status]}`}
          style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add NavBar, TagBadge, SearchBar, ErrorCard, upload components"
```

---

## Task 13: 前端 — 页面实现

**Files:**
- Create: `frontend/src/pages/DashboardPage.jsx`
- Create: `frontend/src/pages/UploadPage.jsx`
- Create: `frontend/src/pages/ErrorBankPage.jsx`
- Create: `frontend/src/pages/ErrorDetailPage.jsx`
- Create: `frontend/src/pages/TagsPage.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: 所有 Task 12 组件；`useUpload()`（Task 11）；`apiClient`（Task 11）

- [ ] **Step 1: 创建 DashboardPage.jsx**

```jsx
// frontend/src/pages/DashboardPage.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../api/client'

export default function DashboardPage() {
  const [stats, setStats] = useState({ total: 0, tags: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiClient.get('/questions?lastKey='),
      apiClient.get('/tags'),
    ]).then(([qResp, tResp]) => {
      setStats({ total: qResp.data.items?.length ?? 0, tags: tResp.data })
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-center mt-20 text-gray-400">加载中...</p>

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">概览</h1>
      <div className="grid grid-cols-2 gap-4 mb-8">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
          <p className="text-4xl font-bold text-indigo-600">{stats.total}</p>
          <p className="text-gray-500 mt-1">总错题数</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
          <p className="text-4xl font-bold text-indigo-600">{stats.tags.length}</p>
          <p className="text-gray-500 mt-1">标签数</p>
        </div>
      </div>
      <Link to="/upload"
        className="block w-full bg-indigo-600 text-white text-center py-3 rounded-xl font-semibold hover:bg-indigo-700">
        + 上传新题目
      </Link>
    </div>
  )
}
```

- [ ] **Step 2: 创建 UploadPage.jsx**

```jsx
// frontend/src/pages/UploadPage.jsx
import { useNavigate } from 'react-router-dom'
import { useUpload } from '../contexts/UploadContext'
import UploadDropzone from '../components/UploadDropzone'
import UploadProgressCard from '../components/UploadProgressCard'

export default function UploadPage() {
  const { queue, retryFile } = useUpload()
  const navigate = useNavigate()
  const allDone = queue.length > 0 && queue.every(i => i.status === 'done' || i.status === 'failed')

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">上传题目</h1>
      <UploadDropzone />
      {queue.length > 0 && (
        <div className="mt-6 space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">识别进度</h2>
          {queue.map(item => (
            <UploadProgressCard key={item.id} item={item} onRetry={retryFile} />
          ))}
        </div>
      )}
      {allDone && (
        <button onClick={() => navigate('/errors')}
          className="mt-6 w-full bg-green-500 text-white py-3 rounded-xl font-semibold hover:bg-green-600">
          查看错题库 →
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 3: 创建 ErrorBankPage.jsx**

```jsx
// frontend/src/pages/ErrorBankPage.jsx
import { useState, useEffect } from 'react'
import apiClient from '../api/client'
import SearchBar from '../components/SearchBar'
import TagBadge from '../components/TagBadge'
import ErrorCard from '../components/ErrorCard'

export default function ErrorBankPage() {
  const [questions, setQuestions] = useState([])
  const [tags, setTags] = useState([])
  const [selectedTag, setSelectedTag] = useState(null)
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get('/tags').then(r => setTags(r.data))
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = {}
    if (selectedTag) params.tagId = selectedTag
    if (keyword) params.keyword = keyword
    apiClient.get('/questions', { params })
      .then(r => setQuestions(r.data.items ?? []))
      .finally(() => setLoading(false))
  }, [selectedTag, keyword])

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">错题库</h1>
      <SearchBar onSearch={setKeyword} />
      <div className="flex flex-wrap gap-2 my-4">
        <button onClick={() => setSelectedTag(null)}
          className={`px-3 py-1 rounded-full text-sm font-medium ${!selectedTag ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          全部
        </button>
        {tags.map(tag => (
          <button key={tag.tagId} onClick={() => setSelectedTag(tag.tagId === selectedTag ? null : tag.tagId)}
            className={`px-3 py-1 rounded-full text-sm font-medium ${selectedTag === tag.tagId ? 'text-white' : 'bg-gray-100 text-gray-600'}`}
            style={selectedTag === tag.tagId ? { backgroundColor: tag.color } : {}}>
            {tag.name}
          </button>
        ))}
      </div>
      {loading ? (
        <p className="text-center mt-10 text-gray-400">加载中...</p>
      ) : questions.length === 0 ? (
        <p className="text-center mt-10 text-gray-400">暂无错题</p>
      ) : (
        <div className="space-y-3">
          {questions.map(q => <ErrorCard key={q.questionId} question={q} tags={tags} />)}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: 创建 ErrorDetailPage.jsx**

```jsx
// frontend/src/pages/ErrorDetailPage.jsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import TagBadge from '../components/TagBadge'

export default function ErrorDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [question, setQuestion] = useState(null)
  const [tags, setTags] = useState([])
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})

  useEffect(() => {
    Promise.all([apiClient.get(`/questions/${id}`), apiClient.get('/tags')])
      .then(([qr, tr]) => {
        setQuestion(qr.data)
        setForm({ subject: qr.data.subject, content: qr.data.content, analysis: qr.data.analysis, tags: qr.data.tags })
        setTags(tr.data)
      })
  }, [id])

  async function handleSave() {
    const { data } = await apiClient.put(`/questions/${id}`, form)
    setQuestion(data)
    setEditing(false)
  }

  async function handleDelete() {
    if (!confirm('确认删除这道错题？')) return
    await apiClient.delete(`/questions/${id}`)
    navigate('/errors')
  }

  const tagMap = Object.fromEntries(tags.map(t => [t.tagId, t]))

  if (!question) return <p className="text-center mt-20 text-gray-400">加载中...</p>

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <button onClick={() => navigate(-1)} className="text-sm text-indigo-600 mb-4 hover:underline">← 返回</button>
      {question.imageUrl && (
        <img src={question.imageUrl} alt="题目原图" className="w-full rounded-xl mb-6 shadow" />
      )}
      {editing ? (
        <div className="space-y-4">
          <input className="w-full border rounded-lg px-3 py-2" placeholder="科目" value={form.subject}
            onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} />
          <textarea className="w-full border rounded-lg px-3 py-2 h-24" placeholder="题目内容" value={form.content}
            onChange={e => setForm(f => ({ ...f, content: e.target.value }))} />
          <textarea className="w-full border rounded-lg px-3 py-2 h-24" placeholder="错误分析" value={form.analysis}
            onChange={e => setForm(f => ({ ...f, analysis: e.target.value }))} />
          <div className="flex gap-3">
            <button onClick={handleSave} className="bg-indigo-600 text-white px-4 py-2 rounded-lg">保存</button>
            <button onClick={() => setEditing(false)} className="text-gray-500 px-4 py-2 rounded-lg border">取消</button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full">
              {question.subject || '未分类'}
            </span>
            <div className="flex gap-2">
              <button onClick={() => setEditing(true)} className="text-sm text-gray-500 hover:text-indigo-600">编辑</button>
              <button onClick={handleDelete} className="text-sm text-red-400 hover:text-red-600">删除</button>
            </div>
          </div>
          <div>
            <h2 className="text-xs text-gray-400 uppercase tracking-wide mb-1">题目内容</h2>
            <p className="text-gray-700 whitespace-pre-wrap">{question.content}</p>
          </div>
          <div>
            <h2 className="text-xs text-gray-400 uppercase tracking-wide mb-1">错误分析</h2>
            <p className="text-gray-600 whitespace-pre-wrap">{question.analysis}</p>
          </div>
          {question.tags?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {question.tags.map(tagId => tagMap[tagId] && (
                <TagBadge key={tagId} name={tagMap[tagId].name} color={tagMap[tagId].color} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: 创建 TagsPage.jsx**

```jsx
// frontend/src/pages/TagsPage.jsx
import { useState, useEffect } from 'react'
import apiClient from '../api/client'
import TagBadge from '../components/TagBadge'

const PRESET_COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#8B5CF6', '#EC4899']

export default function TagsPage() {
  const [tags, setTags] = useState([])
  const [name, setName] = useState('')
  const [color, setColor] = useState(PRESET_COLORS[0])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiClient.get('/tags').then(r => setTags(r.data))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    const { data } = await apiClient.post('/tags', { name: name.trim(), color })
    setTags(t => [...t, data])
    setName('')
    setLoading(false)
  }

  async function handleDelete(tagId) {
    await apiClient.delete(`/tags/${tagId}`)
    setTags(t => t.filter(tag => tag.tagId !== tagId))
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">标签管理</h1>
      <form onSubmit={handleCreate} className="bg-white rounded-xl border border-gray-100 p-4 mb-6 space-y-3">
        <input type="text" placeholder="标签名称（如：数学、易错）" value={name}
          onChange={e => setName(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">颜色：</span>
          {PRESET_COLORS.map(c => (
            <button key={c} type="button" onClick={() => setColor(c)}
              className={`w-6 h-6 rounded-full border-2 transition-transform ${color === c ? 'border-gray-800 scale-110' : 'border-transparent'}`}
              style={{ backgroundColor: c }} />
          ))}
        </div>
        <button type="submit" disabled={loading || !name.trim()}
          className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
          创建标签
        </button>
      </form>
      <div className="space-y-2">
        {tags.map(tag => (
          <div key={tag.tagId} className="flex items-center justify-between bg-white rounded-xl border border-gray-100 px-4 py-3">
            <TagBadge name={tag.name} color={tag.color} />
            <button onClick={() => handleDelete(tag.tagId)} className="text-xs text-red-400 hover:text-red-600">删除</button>
          </div>
        ))}
        {tags.length === 0 && <p className="text-center text-gray-400 text-sm">暂无标签，先创建一个吧</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: 更新 App.jsx（路由 + Context Provider）**

```jsx
// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { UploadProvider } from './contexts/UploadContext'
import { setTokenGetter } from './api/client'
import NavBar from './components/NavBar'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ErrorBankPage from './pages/ErrorBankPage'
import ErrorDetailPage from './pages/ErrorDetailPage'
import TagsPage from './pages/TagsPage'

function ProtectedLayout() {
  const { user, getToken } = useAuth()
  setTokenGetter(getToken)
  if (!user) return <Navigate to="/login" replace />
  return (
    <UploadProvider>
      <NavBar />
      <main className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/errors" element={<ErrorBankPage />} />
          <Route path="/errors/:id" element={<ErrorDetailPage />} />
          <Route path="/tags" element={<TagsPage />} />
        </Routes>
      </main>
    </UploadProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
```

- [ ] **Step 7: 构建验证**

```bash
cd /workshop/error-book/frontend
npm run build 2>&1 | tail -10
```

期望：无 error，显示 `✓ built in`

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/ frontend/src/App.jsx
git commit -m "feat: implement all pages — Dashboard, Upload, ErrorBank, Detail, Tags"
```

---

## Task 14: SAM 模板 — 前端 S3 + CloudFront

**Files:**
- Modify: `template.yaml`（添加前端 S3 Bucket 和 CloudFront）

**Interfaces:**
- Produces:
  - `FrontendUrl` output — CloudFront 访问地址

- [ ] **Step 1: 在 template.yaml 添加前端 S3 Bucket**

```yaml
  # 在 Resources 下添加：
  FrontendBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'error-book-frontend-${AWS::AccountId}-${AWS::Region}'
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  FrontendBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref FrontendBucket
      PolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: cloudfront.amazonaws.com
            Action: s3:GetObject
            Resource: !Sub '${FrontendBucket.Arn}/*'
            Condition:
              StringEquals:
                AWS:SourceArn: !Sub 'arn:aws:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}'
```

- [ ] **Step 2: 添加 CloudFront Origin Access Control 和 Distribution**

```yaml
  CloudFrontOAC:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: error-book-oac
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4

  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        DefaultRootObject: index.html
        Origins:
          - Id: S3Origin
            DomainName: !GetAtt FrontendBucket.RegionalDomainName
            OriginAccessControlId: !GetAtt CloudFrontOAC.Id
            S3OriginConfig: {}
        DefaultCacheBehavior:
          TargetOriginId: S3Origin
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6  # CachingOptimized
        CustomErrorResponses:
          - ErrorCode: 403
            ResponseCode: 200
            ResponsePagePath: /index.html
          - ErrorCode: 404
            ResponseCode: 200
            ResponsePagePath: /index.html
```

- [ ] **Step 3: 添加 FrontendUrl 到 Outputs**

```yaml
  FrontendUrl:
    Value: !Sub 'https://${CloudFrontDistribution.DomainName}'
    Export:
      Name: ErrorBook-FrontendUrl
```

- [ ] **Step 4: 验证模板**

```bash
sam validate --lint
```

期望：`template.yaml is a valid SAM Template`

- [ ] **Step 5: Commit**

```bash
git add template.yaml
git commit -m "feat: add CloudFront distribution and frontend S3 bucket to SAM"
```

---

## Task 15: 部署脚本 & 文档

**Files:**
- Create: `deploy.sh`（一键部署脚本）
- Create: `README.md`

- [ ] **Step 1: 创建 deploy.sh**

```bash
#!/bin/bash
set -e

echo "=== 1. 构建前端 ==="
cd frontend && npm install && npm run build && cd ..

echo "=== 2. 部署 SAM 后端 ==="
sam build
sam deploy --config-file samconfig.toml

echo "=== 3. 获取部署输出 ==="
STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name error-book --query 'Stacks[0].Outputs')
API_URL=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='ApiEndpoint'))")
FRONTEND_URL=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='FrontendUrl'))")
USER_POOL_ID=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='UserPoolId'))")
CLIENT_ID=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='UserPoolClientId'))")
BUCKET=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='ImagesBucketName' or x['OutputKey']=='FrontendBucketName' or True))" 2>/dev/null || true)

echo "=== 4. 写入前端环境变量 ==="
cat > frontend/.env.local << EOF
VITE_USER_POOL_ID=$USER_POOL_ID
VITE_USER_POOL_CLIENT_ID=$CLIENT_ID
VITE_API_BASE_URL=$API_URL
EOF

echo "=== 5. 重新构建前端（含真实环境变量） ==="
cd frontend && npm run build && cd ..

echo "=== 6. 上传前端资源到 S3 ==="
FRONTEND_BUCKET=$(aws cloudformation describe-stacks --stack-name error-book --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text 2>/dev/null || \
  aws s3 ls | grep error-book-frontend | awk '{print $3}')
aws s3 sync frontend/dist/ s3://$FRONTEND_BUCKET --delete

echo ""
echo "✅ 部署完成！"
echo "🌐 前端地址: $FRONTEND_URL"
echo "🔗 API 地址: $API_URL"
```

- [ ] **Step 2: 赋予执行权限**

```bash
chmod +x /workshop/error-book/deploy.sh
```

- [ ] **Step 3: 创建 README.md**

```markdown
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
```

- [ ] **Step 4: Commit**

```bash
git add deploy.sh README.md
git commit -m "feat: add deploy script and README"
```

---

## 自查结果

**Spec 覆盖检查：**
- ✅ 图片上传（多张，逐张进度）— Task 11, 12
- ✅ Claude Vision 识别 — Task 5
- ✅ 错题库保存 — Task 6
- ✅ 标签分类 — Task 4, 7, 12, 13
- ✅ 搜索功能 — Task 6, 12, 13
- ✅ React 19 + Tailwind — Task 9
- ✅ AWS Cognito 认证 — Task 1, 10
- ✅ API Gateway REST + JWT — Task 8
- ✅ FastAPI + Mangum — Task 2, 7
- ✅ DynamoDB 单表设计 — Task 1, 4, 6
- ✅ S3 presigned URL 直传 — Task 7, 11
- ✅ AWS SAM 基础设施 — Task 1, 8, 14
- ✅ CloudFront — Task 14
- ✅ 识别失败处理（status=failed，支持重试） — Task 6, 12
- ✅ 数据隔离（USER#{userId}） — Task 4, 6
- ✅ 文件类型验证 — Task 7, 12
- ✅ JWT 过期自动刷新 — Task 11

**类型一致性：** `QuestionCreate.imageKey`、`QuestionService.create_question`、`UploadContext` 中的 `imageKey` 字段名全部一致。`tagId`、`questionId` 命名全程统一。

**无占位符确认：** 所有步骤包含完整代码，无 TBD/TODO。
