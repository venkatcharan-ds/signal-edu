"""
Supabase Storage client for PDF artifact storage.
Bucket: signal-artifacts
"""
from supabase import create_client, Client
from app.config import get_settings
import structlog
import uuid

log = structlog.get_logger()
settings = get_settings()

BUCKET_NAME = "signal-artifacts"


class StorageService:
    def __init__(self):
        self.client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    async def upload_pdf(self, user_id: uuid.UUID, file_bytes: bytes, filename: str) -> str:
        """Upload a PDF and return its public URL."""
        path = f"{user_id}/{uuid.uuid4()}/{filename}"
        self.client.storage.from_(BUCKET_NAME).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"},
        )
        return self.client.storage.from_(BUCKET_NAME).get_public_url(path)

    async def delete_file(self, url: str) -> None:
        """Delete a file from storage by its public URL path."""
        # Extract path from URL
        path = url.split(f"{BUCKET_NAME}/")[1]
        self.client.storage.from_(BUCKET_NAME).remove([path])
