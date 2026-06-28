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
