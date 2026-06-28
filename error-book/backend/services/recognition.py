import base64
import json
from typing import List
import boto3
from json_repair import repair_json
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
                questions = block["input"]["questions"]
                if isinstance(questions, str):
                    try:
                        questions = json.loads(questions)
                    except json.JSONDecodeError:
                        questions = json.loads(repair_json(questions))
                return questions
        raise ValueError(f"未收到工具调用响应: {str(result)[:200]}")
