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
