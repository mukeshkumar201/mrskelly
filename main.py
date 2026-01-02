import os
import json
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from instagrapi import Client

# --- SETUP CREDENTIALS ---
def get_google_service(service_name, version):
    # GitHub Secrets se data uthana
    client_secret_data = json.loads(os.environ['G_CLIENT_SECRET'])
    
    # JSON structure check (Web vs Installed)
    if 'installed' in client_secret_data:
        app_info = client_secret_data['installed']
    else:
        app_info = client_secret_data['web']

    creds = Credentials(
        None, # Access token (auto-refresh hoga)
        refresh_token=os.environ['G_REFRESH_TOKEN'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=app_info['client_id'],
        client_secret=app_info['client_secret']
    )
    return googleapiclient.discovery.build(service_name, version, credentials=creds)

# --- MAIN LOGIC ---
def main():
    print("🚀 Bot Started...")
    
    # 1. Google Drive Service Connect
    drive_service = get_google_service('drive', 'v3')
    queue_folder_id = os.environ['DRIVE_QUEUE_FOLDER']
    done_folder_id = os.environ['DRIVE_DONE_FOLDER']

    # 2. Check for Video in UploadQueue
    results = drive_service.files().list(
        q=f"'{queue_folder_id}' in parents and mimeType contains 'video/' and trashed=false",
        fields="nextPageToken, files(id, name)"
    ).execute()
    items = results.get('files', [])

    if not items:
        print("❌ Koi video nahi mili 'UploadQueue' folder mein.")
        return

    # Sirf pehli video process karenge (ek baar mein ek)
    video_file = items[0]
    print(f"📥 Video mili: {video_file['name']} (ID: {video_file['id']})")

    # 3. Download Video
    request = drive_service.files().get_media(fileId=video_file['id'])
    file_path = video_file['name']
    
    with open(file_path, "wb") as f:
        f.write(request.execute())
    print("✅ Video Downloaded successfully.")

    # Title set karna (Filename bina extension ke)
    title = os.path.splitext(video_file['name'])[0]
    description = f"{title} #shorts #video"

    # --- YOUTUBE UPLOAD ---
    try:
        print("🎥 YouTube par upload kar raha hoon...")
        youtube = get_google_service('youtube', 'v3')
        
        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['shorts', 'funny', 'viral'],
                'categoryId': '22' # People & Blogs
            },
            'status': {
                'privacyStatus': 'public', # 'private' karein testing ke liye
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        yt_upload = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        ).execute()

        print(f"✅ YouTube Upload Done! Video ID: {yt_upload.get('id')}")
    except Exception as e:
        print(f"❌ YouTube Upload Failed: {e}")

    # --- INSTAGRAM UPLOAD ---
    try:
        print("📸 Instagram par upload kar raha hoon...")
        cl = Client()
        cl.login_by_sessionid(os.environ['INSTA_SESSION_ID'])
        
        # Video Upload
        cl.video_upload(file_path, caption=description)
        print("✅ Instagram Upload Done!")
    except Exception as e:
        print(f"❌ Instagram Upload Failed: {e}")

    # --- CLEANUP (Move to Done Folder) ---
    print("🧹 File ko 'UploadedDone' folder mein move kar raha hoon...")
    drive_service.files().update(
        fileId=video_file['id'],
        addParents=done_folder_id,
        removeParents=queue_folder_id,
        fields='id, parents'
    ).execute()
    
    # Local file delete karein
    os.remove(file_path)
    print("🎉 Mission Complete! Bot so raha hai.")

if __name__ == "__main__":
    main()
