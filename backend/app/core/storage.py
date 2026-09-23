import os
import uuid
import boto3
from abc import ABC, abstractmethod
from typing import Optional, Union, BinaryIO
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings

class StorageSettings(BaseSettings):
    storage_provider: str = "local" # local or s3
    local_storage_dir: str = "./storage"
    s3_bucket: str = "materials-platform-bucket"
    s3_region: str = "us-east-1"

settings = StorageSettings()

class FileStorage(ABC):
    @abstractmethod
    def put(self, file_content: bytes, file_name: str) -> str:
        """Stores the file and returns the storage_key."""
        pass

    @abstractmethod
    def get(self, storage_key: str) -> bytes:
        """Retrieves the file content by storage_key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Deletes the file by storage_key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Checks if the file exists."""
        pass

    @abstractmethod
    def generate_download_url(self, storage_key: str, expiration: int = 3600) -> Optional[str]:
        """Generates a temporary download URL if supported."""
        pass

class LocalStorage(FileStorage):
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, storage_key: str) -> str:
        return os.path.join(self.base_dir, storage_key)

    def put(self, file_content: bytes, file_name: str) -> str:
        ext = os.path.splitext(file_name)[1]
        storage_key = f"{uuid.uuid4()}{ext}"
        path = self._get_path(storage_key)
        
        with open(path, "wb") as f:
            f.write(file_content)
            
        return storage_key

    def get(self, storage_key: str) -> bytes:
        path = self._get_path(storage_key)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File {storage_key} not found in local storage.")
        with open(path, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        path = self._get_path(storage_key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        return os.path.exists(self._get_path(storage_key))

    def generate_download_url(self, storage_key: str, expiration: int = 3600) -> Optional[str]:
        # Local storage doesn't generate signed URLs natively like S3
        # In a real app, you'd point to a local proxy endpoint
        return f"/api/v1/files/download/{storage_key}"


class S3Storage(FileStorage):
    def __init__(self, bucket: str, region: str):
        self.bucket = bucket
        self.s3 = boto3.client('s3', region_name=region)

    def put(self, file_content: bytes, file_name: str) -> str:
        ext = os.path.splitext(file_name)[1]
        storage_key = f"uploads/{uuid.uuid4()}{ext}"
        self.s3.put_object(Bucket=self.bucket, Key=storage_key, Body=file_content)
        return storage_key

    def get(self, storage_key: str) -> bytes:
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=storage_key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File {storage_key} not found in S3.")
            raise

    def delete(self, storage_key: str) -> bool:
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=storage_key)
            return True
        except ClientError:
            return False

    def exists(self, storage_key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    def generate_download_url(self, storage_key: str, expiration: int = 3600) -> Optional[str]:
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': storage_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError:
            return None


def get_storage_provider() -> FileStorage:
    if settings.storage_provider.lower() == "s3":
        return S3Storage(bucket=settings.s3_bucket, region=settings.s3_region)
    else:
        return LocalStorage(base_dir=settings.local_storage_dir)
