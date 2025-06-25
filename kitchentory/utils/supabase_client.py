from django.conf import settings
from supabase import create_client, Client
from functools import lru_cache


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Get a singleton Supabase client instance.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError("Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY in your environment.")
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """
    Get a singleton Supabase admin client instance using the service key.
    Use this only for administrative tasks that require elevated privileges.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("Supabase admin configuration is missing. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your environment.")
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def sync_user_to_supabase(user):
    """
    Sync a Django user to Supabase auth.
    This can be called after user creation or update.
    """
    try:
        client = get_supabase_admin_client()
        # Create or update user in Supabase
        supabase_user_data = {
            'email': user.email,
            'user_metadata': {
                'django_user_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }
        
        # Check if user exists in Supabase
        result = client.auth.admin.list_users()
        existing_user = next((u for u in result.users if u.email == user.email), None)
        
        if existing_user:
            # Update existing user
            client.auth.admin.update_user_by_id(
                uid=existing_user.id,
                attributes=supabase_user_data
            )
        else:
            # Create new user with a temporary password
            # In production, you'd want to send a password reset email
            client.auth.admin.create_user({
                **supabase_user_data,
                'password': f'temp_{user.username}_password',
                'email_confirm': True
            })
            
    except Exception as e:
        # Log the error but don't break the Django user creation
        print(f"Error syncing user to Supabase: {e}")


class SupabaseStorage:
    """
    Helper class for Supabase Storage operations.
    """
    def __init__(self, bucket_name='kitchentory'):
        self.client = get_supabase_client()
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists."""
        try:
            buckets = self.client.storage.list_buckets()
            if not any(b.name == self.bucket_name for b in buckets):
                self.client.storage.create_bucket(
                    self.bucket_name,
                    options={'public': False}
                )
        except Exception as e:
            print(f"Error ensuring bucket exists: {e}")
    
    def upload_file(self, file, path):
        """Upload a file to Supabase storage."""
        try:
            result = self.client.storage.from_(self.bucket_name).upload(
                path=path,
                file=file.read(),
                file_options={"content-type": file.content_type}
            )
            return result
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None
    
    def get_public_url(self, path):
        """Get a public URL for a file."""
        return self.client.storage.from_(self.bucket_name).get_public_url(path)
    
    def delete_file(self, path):
        """Delete a file from storage."""
        try:
            result = self.client.storage.from_(self.bucket_name).remove([path])
            return result
        except Exception as e:
            print(f"Error deleting file: {e}")
            return None