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
