
import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

def get_drive_service(service_account_file: str):
    SCOPES = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def upload_file(file_path: str, folder_id: str, service_account_file: str) -> str:
    """
    Uploads a file to Google Drive into the specified folder.
    
    Args:
        file_path: The local path to the file.
        folder_id: The target folder ID in Google Drive.
        service_account_file: Path to the service account JSON file.
    
    Returns:
        The uploaded file's ID (or None if upload fails).
    """
    service = get_drive_service(service_account_file)
    file_name = os.path.basename(file_path)
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    
    try:
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        logging.info(f"Uploaded file '{file_name}' to Drive with ID: {uploaded_file.get('id')}")
        return uploaded_file.get('id')
    except Exception as e:
        logging.error(f"Failed to upload {file_name} to Google Drive: {e}")
        return None
