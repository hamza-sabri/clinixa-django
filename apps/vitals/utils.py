"""Utility functions for vitals app - including Cloudinary file uploads."""

import cloudinary.uploader
from django.conf import settings


def upload_files_to_cloudinary(files):
    """
    Upload multiple files to Cloudinary and return their URLs.
    
    Args:
        files: List of file objects to upload
        
    Returns:
        List of Cloudinary secure URLs
    """
    urls = []
    
    for file in files:
        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file,
                folder='clinixa/vitals',  # Organize uploads in a folder
                resource_type='auto',  # Auto-detect file type (image, video, raw)
            )
            urls.append(result.get('secure_url'))
        except Exception as e:
            # Log error but continue with other files
            print(f"Error uploading file to Cloudinary: {e}")
            continue
    
    return urls


def upload_single_file_to_cloudinary(file, folder='clinixa/vitals'):
    """
    Upload a single file to Cloudinary and return its URL.
    
    Args:
        file: File object to upload
        folder: Cloudinary folder to store the file in
        
    Returns:
        Cloudinary secure URL or None if upload failed
    """
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type='auto',
        )
        return result.get('secure_url')
    except Exception as e:
        print(f"Error uploading file to Cloudinary: {e}")
        return None




