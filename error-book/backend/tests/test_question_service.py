import pytest
from unittest.mock import MagicMock, patch
from models.question import QuestionCreate, QuestionUpdate, ManualQuestionCreate
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

def test_create_manual_question(mock_deps):
    table, _, s3 = mock_deps
    table.put_item.return_value = {}
    svc = QuestionService()
    q = svc.create_manual_question("user1", ManualQuestionCreate(subject="数学", content="1+1=?", analysis="加法"))
    assert q.status == "done"
    assert q.subject == "数学"
    assert q.content == "1+1=?"
    assert q.userId == "user1"
    assert q.imageKey is None


def test_delete_question(mock_deps):
    table, _, _ = mock_deps
    table.delete_item.return_value = {}
    svc = QuestionService()
    svc.delete_question("user1", "q1")
    table.delete_item.assert_called_once_with(
        Key={"PK": "USER#user1", "SK": "QUESTION#q1"}
    )
