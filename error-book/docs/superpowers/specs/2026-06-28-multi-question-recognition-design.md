# 多题目识别设计文档

**日期：** 2026-06-28  
**范围：** 一张图片识别出多道题目并分别存储

## 背景

现有实现：1 张图片 → 1 次 Bedrock 调用 → 1 条 DynamoDB 记录。当图片包含多道题时，只保存第一道，其余丢失。

## 目标

一张图片无论包含几道题目，全部识别并分别存储为独立记录，每条记录保留原图 `imageKey`。

---

## 架构方案

选用**方案 A：单次工具调用，schema 改为 questions 数组**。

理由：单次 API 调用更快、费用更低；schema 约束明确；改动范围可控。放弃方案 B（agentic 多次调用 save_question），因为需要处理 stop_reason 循环，复杂度高且无收益。

---

## 各层改动

### 1. recognition.py

**TOOL schema** 改为包含 `questions` 数组：

```python
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
                        "subject": {"type": "string", "description": "科目"},
                        "content": {"type": "string", "description": "题目完整文字内容"},
                        "analysis": {"type": "string", "description": "考点分析和解题思路"},
                    },
                    "required": ["subject", "content", "analysis"],
                },
            }
        },
        "required": ["questions"],
    },
}
```

**Prompt** 改为：`"请识别图中所有题目，每道题分别提供科目、完整文字内容和考点分析。"`

**`recognize()` 返回类型**：`List[dict]`，从 `block["input"]["questions"]` 取值。

### 2. questionService.py

`create_question` 改名为 `create_questions_from_image`，返回 `List[Question]`：

- 调用 `self.recog.recognize()` 拿到题目列表
- 对每道题独立生成 `questionId`，共享同一 `imageKey`，批量 `put_item`
- 全部失败时返回含一条 `status="failed"` 占位记录的列表

### 3. routes/questions.py

`POST /questions/recognize` 返回类型从 `Question` 改为 `List[Question]`，调用 `create_questions_from_image`。其余路由不变。

### 4. 前端

**UploadContext.jsx**：queue item 的 `question` 字段改为 `questions: []`（数组）。识别成功后存 `questions: data`（API 返回的数组）。

**UploadProgressCard.jsx**：识别完成后展开列出所有题目，每行显示科目 + content 前 30 字。失败时保持现有"识别失败 + 重试"行为不变。

---

## 错误处理

| 场景 | 处理 |
|------|------|
| Bedrock 异常 | 返回一条 `status="failed"` 占位记录，前端显示重试 |
| 模型返回空数组 | 同上，避免静默丢失 |
| 部分题目写 DynamoDB 失败 | 3 次重试，超出则整批标记失败 |

---

## 测试更新

- `test_recognition.py`：mock 返回值改为 `{"questions": [{...}, {...}]}`，断言返回 list
- `test_question_service.py`：`test_create_question` 改为验证返回多条记录
