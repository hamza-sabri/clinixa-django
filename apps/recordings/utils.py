
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from django.conf import settings

# B2 Configuration
B2_KEY_ID = '0030594f36420ad0000000001'
B2_APP_KEY = 'K003al8vB8bWOrBoDcgAG10kQYPoZig'
B2_BUCKET_NAME = 'Clinixa'

_b2_api = None
_bucket = None

def get_b2_api():
    global _b2_api
    if _b2_api is None:
        info = InMemoryAccountInfo()
        _b2_api = B2Api(info)
        _b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
    return _b2_api

def get_b2_bucket():
    global _bucket
    if _bucket is None:
        api = get_b2_api()
        _bucket = api.get_bucket_by_name(B2_BUCKET_NAME)
    return _bucket

def generate_presigned_url(file_name, duration_in_seconds=3600):
    """
    Generate a presigned URL for downloading a file from B2.
    valid for 1 hour by default.
    """
    if not file_name:
        return None
        
    try:
        bucket = get_b2_bucket()
        # This generates a token valid for the specific file prefix (exact match)
        auth_token = bucket.get_download_authorization(
            file_name_prefix=file_name,
            valid_duration_in_seconds=duration_in_seconds
        )
        
        # Base download URL
        # For B2, usually: https://f000.backblazeb2.com/file/{bucket_name}/{file_name}?Authorization={token}
        # We need the download URL from the API info
        download_url_base = get_b2_api().account_info.get_download_url()
        
        full_url = f"{download_url_base}/file/{B2_BUCKET_NAME}/{file_name}?Authorization={auth_token}"
        return full_url
    except Exception as e:
        print(f"Error generating B2 URL: {e}")
        return None

def upload_file_to_b2(file_obj, file_name):
    """
    Upload a file object to B2.
    Returns the B2 stored file info (id, name).
    """
    bucket = get_b2_bucket()
    
    # Read/Reset file pointer if needed
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
    
    # Content type
    content_type = getattr(file_obj, 'content_type', 'application/octet-stream')
    
    # Upload
    uploaded_file = bucket.upload_bytes(
        data_bytes=file_obj.read(),
        file_name=file_name,
        content_type=content_type
    )
    
    return uploaded_file


def delete_file_from_b2(file_id, file_name):
    """
    Delete a file from B2 by file_id and file_name.
    
    Args:
        file_id: The B2 file ID (stored in attachment records)
        file_name: The B2 file name/key (stored in attachment records)
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        bucket = get_b2_bucket()
        bucket.delete_file_version(file_id, file_name)
        return True
    except Exception as e:
        print(f"Error deleting file from B2: {e}")
        return False
