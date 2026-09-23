import os
import pytest
from app.core.storage import LocalStorage, S3Storage
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch

@pytest.fixture
def local_storage(tmp_path):
    storage_dir = tmp_path / "storage"
    return LocalStorage(base_dir=str(storage_dir))

def test_local_storage_put_get(local_storage):
    content = b"test file content"
    file_name = "test.txt"
    
    storage_key = local_storage.put(content, file_name)
    assert storage_key.endswith(".txt")
    
    retrieved = local_storage.get(storage_key)
    assert retrieved == content

def test_local_storage_exists(local_storage):
    content = b"test"
    key = local_storage.put(content, "test.txt")
    
    assert local_storage.exists(key) is True
    assert local_storage.exists("nonexistent.txt") is False

def test_local_storage_delete(local_storage):
    content = b"test"
    key = local_storage.put(content, "test.txt")
    
    assert local_storage.delete(key) is True
    assert local_storage.exists(key) is False
    assert local_storage.delete("nonexistent.txt") is False

def test_local_storage_get_not_found(local_storage):
    with pytest.raises(FileNotFoundError):
        local_storage.get("nonexistent.txt")

@patch("app.core.storage.boto3.client")
def test_s3_storage_put(mock_boto3_client):
    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3
    
    storage = S3Storage(bucket="test-bucket", region="us-east-1")
    key = storage.put(b"content", "test.csv")
    
    assert key.startswith("uploads/")
    assert key.endswith(".csv")
    mock_s3.put_object.assert_called_once()

@patch("app.core.storage.boto3.client")
def test_s3_storage_get(mock_boto3_client):
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"content")}
    mock_boto3_client.return_value = mock_s3
    
    storage = S3Storage(bucket="test-bucket", region="us-east-1")
    retrieved = storage.get("uploads/test.csv")
    
    assert retrieved == b"content"
    mock_s3.get_object.assert_called_once_with(Bucket="test-bucket", Key="uploads/test.csv")
