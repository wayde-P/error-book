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
