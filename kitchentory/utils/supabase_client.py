import logging
from typing import Optional
from django.conf import settings
from supabase import create_client, Client
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Get a singleton Supabase client instance.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError(
            "Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY in your environment."
        )

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """
    Get a singleton Supabase admin client instance using the service key.
    Use this only for administrative tasks that require elevated privileges.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError(
            "Supabase admin configuration is missing. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your environment."
        )

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def sync_user_to_supabase(user) -> bool:
    """
    Sync a Django user to Supabase auth.
    This can be called after user creation or update.

    Args:
        user: Django User instance

    Returns:
        bool: True if sync was successful, False otherwise
    """
    try:
        logger.info(f"Syncing user {user.email} to Supabase")
        client = get_supabase_admin_client()

        # Create or update user in Supabase
        supabase_user_data = {
            "email": user.email,
            "user_metadata": {
                "django_user_id": user.id,
                "username": user.username if hasattr(user, "username") else "",
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        }

        # Check if user exists in Supabase
        try:
            result = client.auth.admin.list_users()
            existing_user = next(
                (u for u in result.users if u.email == user.email), None
            )
        except Exception as e:
            logger.error(f"Failed to list Supabase users: {e}")
            return False

        if existing_user:
            # Update existing user
            try:
                client.auth.admin.update_user_by_id(
                    uid=existing_user.id, attributes=supabase_user_data
                )
                logger.info(f"Successfully updated Supabase user {user.email}")
            except Exception as e:
                logger.error(f"Failed to update Supabase user {user.email}: {e}")
                return False
        else:
            # Create new user with a temporary password
            # In production, you'd want to send a password reset email
            try:
                client.auth.admin.create_user(
                    {
                        **supabase_user_data,
                        "password": f"temp_{user.id}_password",
                        "email_confirm": True,
                    }
                )
                logger.info(f"Successfully created Supabase user {user.email}")
            except Exception as e:
                logger.error(f"Failed to create Supabase user {user.email}: {e}")
                return False

        return True

    except Exception as e:
        logger.error(
            f"Unexpected error syncing user {user.email} to Supabase: {e}",
            exc_info=True,
        )
        return False


class SupabaseStorage:
    """
    Helper class for Supabase Storage operations.
    Provides error handling and logging for storage operations.
    """

    def __init__(self, bucket_name: str = "kitchentory"):
        self.client = get_supabase_client()
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> bool:
        """
        Ensure the storage bucket exists.

        Returns:
            bool: True if bucket exists or was created successfully
        """
        try:
            logger.debug(f"Checking if bucket '{self.bucket_name}' exists")
            buckets = self.client.storage.list_buckets()

            if not any(b.name == self.bucket_name for b in buckets):
                logger.info(f"Creating bucket '{self.bucket_name}'")
                self.client.storage.create_bucket(
                    self.bucket_name, options={"public": False}
                )
                logger.info(f"Successfully created bucket '{self.bucket_name}'")
            else:
                logger.debug(f"Bucket '{self.bucket_name}' already exists")

            return True

        except Exception as e:
            logger.error(
                f"Error ensuring bucket '{self.bucket_name}' exists: {e}", exc_info=True
            )
            return False

    def upload_file(self, file, path: str) -> Optional[dict]:
        """
        Upload a file to Supabase storage.

        Args:
            file: File object to upload
            path: Path where to store the file

        Returns:
            dict: Upload result or None if failed
        """
        try:
            logger.info(f"Uploading file to path: {path}")

            # Validate inputs
            if not file:
                logger.error("No file provided for upload")
                return None

            if not path:
                logger.error("No path provided for upload")
                return None

            result = self.client.storage.from_(self.bucket_name).upload(
                path=path,
                file=file.read(),
                file_options={
                    "content-type": getattr(
                        file, "content_type", "application/octet-stream"
                    )
                },
            )

            logger.info(f"Successfully uploaded file to {path}")
            return result

        except Exception as e:
            logger.error(f"Error uploading file to {path}: {e}", exc_info=True)
            return None

    def get_public_url(self, path: str) -> Optional[str]:
        """
        Get a public URL for a file.

        Args:
            path: Path to the file

        Returns:
            str: Public URL or None if failed
        """
        try:
            if not path:
                logger.error("No path provided for getting public URL")
                return None

            url = self.client.storage.from_(self.bucket_name).get_public_url(path)
            logger.debug(f"Generated public URL for {path}")
            return url

        except Exception as e:
            logger.error(f"Error getting public URL for {path}: {e}", exc_info=True)
            return None

    def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: Path to the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            if not path:
                logger.error("No path provided for file deletion")
                return False

            logger.info(f"Deleting file at path: {path}")
            result = self.client.storage.from_(self.bucket_name).remove([path])

            if result:
                logger.info(f"Successfully deleted file at {path}")
                return True
            else:
                logger.warning(f"Delete operation returned empty result for {path}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file at {path}: {e}", exc_info=True)
            return False

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            path: Path to check

        Returns:
            bool: True if file exists
        """
        try:
            if not path:
                return False

            files = self.client.storage.from_(self.bucket_name).list(
                path=path.rsplit("/", 1)[0] if "/" in path else ""
            )

            filename = path.rsplit("/", 1)[-1]
            return any(f.name == filename for f in files)

        except Exception as e:
            logger.error(f"Error checking if file exists at {path}: {e}")
            return False
