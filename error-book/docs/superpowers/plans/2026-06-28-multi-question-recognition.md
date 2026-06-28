# 多题目识别 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一张图片识别出所有题目，每道题独立存储为 DynamoDB 记录，前端上传进度卡片展开显示所有识别结果。

**Architecture:** `recognition.py` 用 tool use 返回 `questions` 数组；`questionService.py` 批量写 DynamoDB；`POST /questions/recognize` 返回 `List[Question]`；前端 UploadContext 存数组，UploadProgressCard 展开列出各题。

**Tech Stack:** Python 3.12, FastAPI, boto3 Bedrock Runtime, React 19, Tailwind CSS

## Global Constraints

- Python 变量命名使用 camelCase（如 `imageKey`、`questionId`、`userId`）
- React 只使用函数式组件，props 在函数签名中解构
- React 组件不超过 100 行，不使用内联样式，使用 Tailwind class
- 后端测试文件在 `backend/tests/`，运行命令：`cd backend && python3 -m pytest tests/ -v`

---

## File Map

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/services/recognition.py` | Modify | TOOL 改为 questions 数组，返回 `List[dict]` |
| `backend/services/questionService.py` | Modify | `create_question` → `create_questions_from_image`，返回 `List[Question]` |
| `backend/routes/questions.py` | Modify | recognize 端点返回 `List[Question]` |
| `backend/tests/test_recognition.py` | Modify | 更新 mock 和断言匹配新接口 |
| `backend/tests/test_question_service.py` | Modify | 更新测试匹配新接口 |
| `frontend/src/contexts/UploadContext.jsx` | Modify | `question` → `questions: []` |
| `frontend/src/components/UploadProgressCard.jsx` | Modify | 展开显示多道题目列表 |

---

## Task 1: 更新 recognition.py — 返回题目列表

**Files:**
- Modify: `backend/services/recognition.py`
- Test: `backend/tests/test_recognition.py`

**Interfaces:**
- Produces: `RecognitionService.recognize(imageKey: str) -> List[dict]`，每个 dict 含 `subject`、`content`、`analysis`

- [ ] **Step 1: 更新测试，验证返回列表**

将 `backend/tests/test_recognition.py` 全部替换为：

```python
import json
import pytest
from unittest.mock import MagicMock, patch

def _make_bedrock_tool_response(questions: list) -> dict:
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps({
        "content": [{
            "type": "tool_use",
            "name": "save_questions",
            "input": {"questions": questions}
        }]
    }).encode()
    return {"body": body_mock}

def _make_bedrock_empty_response() -> dict:
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps({"content": []}).encode()
    return {"body": body_mock}

def test_recognize_returns_list_of_questions():
    with patch("services.recognition.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_bedrock = MagicMock()
        mock_boto.side_effect = lambda service, **kw: mock_s3 if service == "s3" else mock_bedrock

        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-image-bytes"),
            "ContentType": "image/jpeg",
        }
        mock_bedrock.invoke_model.return_value = _make_bedrock_tool_response([
            {"subject": "数学", "content": "1+1=?", "analysis": "加法运算"},
            {"subject": "数学", "content": "2×3=?", "analysis": "乘法运算"},
        ])

        from services.recognition import RecognitionService
        svc = RecognitionService()
        result = svc.recognize("user1/q1/photo.jpg")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["subject"] == "数学"
        assert result[0]["content"] == "1+1=?"
        assert result[1]["content"] == "2×3=?"

def test_recognize_raises_when_no_tool_call():
    with patch("services.recognition.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_bedrock = MagicMock()
        mock_boto.side_effect = lambda service, **kw: mock_s3 if service == "s3" else mock_bedrock

        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-image-bytes"),
            "ContentType": "image/jpeg",
        }
        mock_bedrock.invoke_model.return_value = _make_bedrock_empty_response()

        from services.recognition import RecognitionService
        svc = RecognitionService()
        with pytest.raises(ValueError, match="未收到工具调用响应"):
            svc.recognize("user1/q1/photo.jpg")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /workshop/error-book/backend && python3 -m pytest tests/test_recognition.py -v
```

预期：FAIL（现有实现返回 dict 而非 list）

- [ ] **Step 3: 更新 recognition.py**

将 `backend/services/recognition.py` 全部替换为：

```python
import base64
import json
from typing import List
import boto3
from config import imagesBucket, awsRegion

BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

PROMPT = "请识别图中所有题目，每道题分别提供科目、完整文字内容和考点分析。"

TOOL = {
    "name": "save_questions",
    "description": "保存识别出的所有题目",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "科目：数学/语文/英语/物理/化学/生物/历史/地理/政治/其他",
                        },
                        "content": {
                            "type": "string",
                            "description": "题目完整文字内容",
                        },
                        "analysis": {
                            "type": "string",
                            "description": "这道题的考点分析和解题思路",
                        },
                    },
                    "required": ["subject", "content", "analysis"],
                },
            }
        },
        "required": ["questions"],
    },
}

class RecognitionService:
    def __init__(self):
        self.s3 = boto3.client("s3", region_name=awsRegion)
        self.bedrock = boto3.client("bedrock-runtime", region_name=awsRegion)

    def recognize(self, imageKey: str) -> List[dict]:
        obj = self.s3.get_object(Bucket=imagesBucket, Key=imageKey)
        imageBytes = obj["Body"].read()
        contentType = obj.get("ContentType", "image/jpeg")
        imageB64 = base64.standard_b64encode(imageBytes).decode("utf-8")

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "tools": [TOOL],
            "tool_choice": {"type": "tool", "name": "save_questions"},
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": contentType, "data": imageB64}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        })

        response = self.bedrock.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
        result = json.loads(response["body"].read())
        for block in result.get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "save_questions":
                return block["input"]["questions"]
        raise ValueError(f"未收到工具调用响应: {str(result)[:200]}")
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd /workshop/error-book/backend && python3 -m pytest tests/test_recognition.py -v
```

预期：2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/recognition.py backend/tests/test_recognition.py
git commit -m "feat: recognition returns list of questions"
```

---

## Task 2: 更新 questionService.py — 批量创建题目

**Files:**
- Modify: `backend/services/questionService.py`
- Test: `backend/tests/test_question_service.py`

**Interfaces:**
- Consumes: `RecognitionService.recognize(imageKey) -> List[dict]`（Task 1）
- Produces: `QuestionService.create_questions_from_image(userId: str, data: QuestionCreate) -> List[Question]`

- [ ] **Step 1: 更新测试**

将 `backend/tests/test_question_service.py` 全部替换为：

```python
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
        recog.recognize.return_value = [
            {"subject": "数学", "content": "1+1=?", "analysis": "加法"},
            {"subject": "数学", "content": "2×3=?", "analysis": "乘法"},
        ]
        MockRecog.return_value = recog
        s3 = MagicMock()
        s3.generate_presigned_url.return_value = "https://s3.example.com/img.jpg"
        mock_s3_client.return_value = s3
        yield table, recog, s3

def test_create_questions_from_image_returns_list(mock_deps):
    table, recog, s3 = mock_deps
    table.put_item.return_value = {}
    svc = QuestionService()
    questions = svc.create_questions_from_image("user1", QuestionCreate(imageKey="user1/q1/photo.jpg"))
    assert isinstance(questions, list)
    assert len(questions) == 2
    assert all(q.status == "done" for q in questions)
    assert questions[0].subject == "数学"
    assert questions[0].content == "1+1=?"
    assert questions[1].content == "2×3=?"
    assert all(q.userId == "user1" for q in questions)
    assert all(q.imageKey == "user1/q1/photo.jpg" for q in questions)

def test_create_questions_failed_recognition_returns_failed_record(mock_deps):
    table, recog, s3 = mock_deps
    recog.recognize.side_effect = ValueError("识别结果解析失败")
    table.put_item.return_value = {}
    svc = QuestionService()
    questions = svc.create_questions_from_image("user1", QuestionCreate(imageKey="user1/q1/photo.jpg"))
    assert isinstance(questions, list)
    assert len(questions) == 1
    assert questions[0].status == "failed"

def test_create_questions_empty_result_returns_failed_record(mock_deps):
    table, recog, s3 = mock_deps
    recog.recognize.return_value = []
    table.put_item.return_value = {}
    svc = QuestionService()
    questions = svc.create_questions_from_image("user1", QuestionCreate(imageKey="user1/q1/photo.jpg"))
    assert len(questions) == 1
    assert questions[0].status == "failed"

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

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /workshop/error-book/backend && python3 -m pytest tests/test_question_service.py -v
```

预期：FAIL（`create_questions_from_image` 方法不存在）

- [ ] **Step 3: 更新 questionService.py**

在 `backend/services/questionService.py` 中，将 `create_question` 方法替换为 `create_questions_from_image`：

```python
    def create_questions_from_image(self, userId: str, data: QuestionCreate) -> List[Question]:
        try:
            recognized = self.recog.recognize(data.imageKey)
        except Exception:
            recognized = []

        if not recognized:
            questionId = str(uuid.uuid4())
            createdAt = datetime.now(timezone.utc).isoformat()
            item = {
                "PK": f"USER#{userId}",
                "SK": f"QUESTION#{questionId}",
                "questionId": questionId,
                "userId": userId,
                "imageKey": data.imageKey,
                "subject": data.subject or "",
                "content": "",
                "analysis": "",
                "tags": [],
                "status": "failed",
                "createdAt": createdAt,
            }
            self.table.put_item(Item=item)
            return [self._item_to_question(item)]

        questions = []
        createdAt = datetime.now(timezone.utc).isoformat()
        for r in recognized:
            questionId = str(uuid.uuid4())
            item = {
                "PK": f"USER#{userId}",
                "SK": f"QUESTION#{questionId}",
                "questionId": questionId,
                "userId": userId,
                "imageKey": data.imageKey,
                "subject": r.get("subject", ""),
                "content": r.get("content", ""),
                "analysis": r.get("analysis", ""),
                "tags": [],
                "status": "done",
                "createdAt": createdAt,
            }
            for attempt in range(3):
                try:
                    self.table.put_item(Item=item)
                    break
                except Exception:
                    if attempt == 2:
                        raise
            questions.append(self._item_to_question(item))
        return questions
```

同时在文件顶部 import 中补上 `List`：
```python
from typing import List, Optional
```

（`Optional` 已存在，只需确认 `List` 也在）

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd /workshop/error-book/backend && python3 -m pytest tests/test_question_service.py -v
```

预期：5 passed

- [ ] **Step 5: 运行全部测试，确认无回归**

```bash
cd /workshop/error-book/backend && python3 -m pytest tests/ -v
```

预期：全部 passed

- [ ] **Step 6: Commit**

```bash
git add backend/services/questionService.py backend/tests/test_question_service.py
git commit -m "feat: batch create questions from single image"
```

---

## Task 3: 更新 routes/questions.py — 端点返回列表

**Files:**
- Modify: `backend/routes/questions.py`

**Interfaces:**
- Consumes: `QuestionService.create_questions_from_image(userId, data) -> List[Question]`（Task 2）
- Produces: `POST /questions/recognize` → `List[Question]`（JSON 数组）

- [ ] **Step 1: 更新 recognize 端点**

在 `backend/routes/questions.py` 中，将 recognize 路由改为：

```python
from typing import List

@router.post("/recognize")
def recognize_question(
    request: Request,
    data: QuestionCreate,
    userId: str = Depends(get_current_user_id),
) -> List[Question]:
    svc = QuestionService()
    return svc.create_questions_from_image(userId, data)
```

删除原来的 `from models.question import QuestionCreate, ManualQuestionCreate, QuestionUpdate` 中的导入没有变化，只需在文件顶部确认 `from typing import List` 存在（若无则添加）。

- [ ] **Step 2: 运行全部后端测试**

```bash
cd /workshop/error-book/backend && python3 -m pytest tests/ -v
```

预期：全部 passed

- [ ] **Step 3: Commit**

```bash
git add backend/routes/questions.py
git commit -m "feat: recognize endpoint returns list of questions"
```

---

## Task 4: 更新前端 UploadContext — 存储题目数组

**Files:**
- Modify: `frontend/src/contexts/UploadContext.jsx`

**Interfaces:**
- Produces: queue item 结构 `{ id, file, status, questions: Question[] }`

- [ ] **Step 1: 更新 UploadContext.jsx**

将 `frontend/src/contexts/UploadContext.jsx` 全部替换为：

```jsx
// frontend/src/contexts/UploadContext.jsx
import { createContext, useContext, useState, useCallback } from 'react'
import axios from 'axios'
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
      const { data: { url, key } } = await apiClient.get('/upload/presigned-url', {
        params: { filename: file.name, contentType: file.type },
      })
      await axios.put(url, file, { headers: { 'Content-Type': file.type } })
      updateItem(id, { status: 'recognizing' })
      const { data: questions } = await apiClient.post('/questions/recognize', { imageKey: key })
      const allFailed = questions.every(q => q.status === 'failed')
      updateItem(id, { status: allFailed ? 'failed' : 'done', questions })
    } catch {
      updateItem(id, { status: 'failed', questions: [] })
    }
  }

  const addFiles = useCallback((files) => {
    const newItems = Array.from(files).map(file => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      questions: [],
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

- [ ] **Step 2: Commit**

```bash
git add frontend/src/contexts/UploadContext.jsx
git commit -m "feat: upload queue stores questions array"
```

---

## Task 5: 更新 UploadProgressCard — 展开显示题目列表

**Files:**
- Modify: `frontend/src/components/UploadProgressCard.jsx`

**Interfaces:**
- Consumes: `item.questions: Array<{ questionId, subject, content, status }>`（Task 4）

- [ ] **Step 1: 更新 UploadProgressCard.jsx**

将 `frontend/src/components/UploadProgressCard.jsx` 全部替换为：

```jsx
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
  const { file, status, questions = [] } = item
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
            {isDone ? `识别完成，共 ${questions.length} 道题目` : STATUS_LABEL[status]}
          </p>
        </div>
        {isFailed && (
          <button onClick={() => onRetry(item.id)}
            className="text-xs text-indigo-600 hover:underline flex-shrink-0">重试</button>
        )}
      </div>
      <div className="w-full bg-gray-100 rounded-full h-1.5 mb-2">
        <div className={`h-1.5 rounded-full transition-all duration-500 ${STATUS_COLOR[status]}`}
          style={{ width: `${progress}%` }} />
      </div>
      {isDone && questions.length > 0 && (
        <ul className="mt-2 space-y-1">
          {questions.map(q => (
            <li key={q.questionId} className="text-xs text-gray-600 flex gap-1.5">
              <span className="text-gray-400 flex-shrink-0">{q.subject}</span>
              <span className="truncate">{q.content?.slice(0, 30)}{q.content?.length > 30 ? '…' : ''}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/UploadProgressCard.jsx
git commit -m "feat: show recognized questions list in upload card"
```

---

## Task 6: 部署并验证

- [ ] **Step 1: 运行全部后端测试**

```bash
cd /workshop/error-book/backend && python3 -m pytest tests/ -v
```

预期：全部 passed

- [ ] **Step 2: 构建前端，确认无编译错误**

```bash
cd /workshop/error-book/frontend && npm run build
```

预期：build 成功，无 error

- [ ] **Step 3: 部署**

```bash
cd /workshop/error-book && ./deploy.sh
```

- [ ] **Step 4: 用包含多道题的图片测试**

直接用 API 验证：

```bash
# 获取 token（密码已在此会话中设置为 aA11111!）
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 52munlku56rl605us4lkce8lih \
  --auth-parameters USERNAME=w2341078@163.com,PASSWORD=aA11111! \
  --query "AuthenticationResult.IdToken" --output text)

# 获取 presigned URL 并上传图片
PRESIGN=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://g61h8cpzb9.execute-api.us-east-1.amazonaws.com/prod/upload/presigned-url?filename=test.jpg&contentType=image%2Fjpeg")
UPLOAD_URL=$(echo $PRESIGN | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])")
IMAGE_KEY=$(echo $PRESIGN | python3 -c "import sys,json; print(json.load(sys.stdin)['key'])")
curl -s -X PUT "$UPLOAD_URL" -H "Content-Type: image/jpeg" --data-binary @/path/to/multi-question.jpg

# 触发识别，断言返回数组
RESULT=$(curl -s -X POST "https://g61h8cpzb9.execute-api.us-east-1.amazonaws.com/prod/questions/recognize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"imageKey\": \"$IMAGE_KEY\"}")

echo $RESULT | python3 -c "
import sys, json
r = json.load(sys.stdin)
print('类型:', type(r).__name__)
print('题目数:', len(r))
for i, q in enumerate(r):
    print(f'  [{i+1}] {q[\"subject\"]} — {q[\"content\"][:40]}')
"
```

预期：输出 `类型: list`，`题目数: N`（N ≥ 1）
