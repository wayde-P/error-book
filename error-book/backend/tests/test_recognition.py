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

def _make_bedrock_tool_response_string_questions(questions_json_str: str) -> dict:
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps({
        "content": [{
            "type": "tool_use",
            "name": "save_questions",
            "input": {"questions": questions_json_str}
        }]
    }).encode()
    return {"body": body_mock}


def test_recognize_handles_questions_as_json_string():
    """Bedrock sometimes returns questions as a serialized JSON string."""
    questions_str = json.dumps([
        {"subject": "数学", "content": "1+1=?", "analysis": "加法"},
    ])
    with patch("services.recognition.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_bedrock = MagicMock()
        mock_boto.side_effect = lambda service, **kw: mock_s3 if service == "s3" else mock_bedrock
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-image-bytes"),
            "ContentType": "image/jpeg",
        }
        mock_bedrock.invoke_model.return_value = _make_bedrock_tool_response_string_questions(questions_str)

        from services.recognition import RecognitionService
        svc = RecognitionService()
        result = svc.recognize("user1/q1/photo.jpg")
        assert len(result) == 1
        assert result[0]["subject"] == "数学"


def test_recognize_repairs_malformed_json_string():
    """Bedrock may return questions as JSON string with unescaped quotes (e.g. math problem choices)."""
    # Simulate unescaped double quotes inside string values, as seen in real Bedrock responses
    malformed = '[{"subject": "数学", "content": "选 "A" 还是 "B"?", "analysis": "选项分析"}]'
    with patch("services.recognition.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_bedrock = MagicMock()
        mock_boto.side_effect = lambda service, **kw: mock_s3 if service == "s3" else mock_bedrock
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-image-bytes"),
            "ContentType": "image/jpeg",
        }
        mock_bedrock.invoke_model.return_value = _make_bedrock_tool_response_string_questions(malformed)

        from services.recognition import RecognitionService
        svc = RecognitionService()
        result = svc.recognize("user1/q1/photo.jpg")
        assert len(result) == 1
        assert result[0]["subject"] == "数学"


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
