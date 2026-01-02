import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from instagrapi import Client

# --- 1. SETUP GOOGLE LOGIN ---
def get_google_service(service_name, version):
    client_secret_data = json.loads(os.environ['G_CLIENT_SECRET'])
    if 'installed' in client_secret_data:
        config = client_secret_data['installed']
    else:
        config = client_secret_data['web']

    creds = Credentials(
        None,
        refresh_token=os.environ['G_REFRESH_TOKEN'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config['client_id'],
        client_secret=config['client_secret']
    )
    return build(service_name, version, credentials=creds)

# --- MAIN LOGIC ---
def main():
    print("🚀 Mr Skelly Bot Started...")

    # -- DRIVE SETUP --
    drive_service = get_google_service('drive', 'v3')
    queue_folder_id = os.environ['DRIVE_QUEUE_FOLDER']
    done_folder_id = os.environ['DRIVE_DONE_FOLDER']

    # -- CHECK FOR VIDEO --
    results = drive_service.files().list(
        q=f"'{queue_folder_id}' in parents and mimeType contains 'video/' and trashed=false",
        fields="files(id, name)",
        pageSize=1
    ).execute()
    items = results.get('files', [])

    if not items:
        print("❌ Koi video nahi mili 'UploadQueue' folder mein.")
        return

    video_file = items[0]
    print(f"📥 Video mili: {video_file['name']}")

    # -- DOWNLOAD VIDEO --
    request = drive_service.files().get_media(fileId=video_file['id'])
    file_path = "video.mp4" 
    with open(file_path, "wb") as f:
        f.write(request.execute())
    print("✅ Video Downloaded.")

    # -- PREPARE CONTENT --
    raw_title = os.path.splitext(video_file['name'])[0]
    caption_text = (
        f"Just chilling with some thoughts... 💀☕\n\n"
        f"👇 Comment the quote that keeps you going!\n\n"
        f"Double tap if you need a break like this. ❤️\n"
        f".\n.\n"
    )
    hashtags = "#mrskelly #skeletonart #cozyvibes #aesthetic #lofi #shorts #viral"
    full_description = caption_text + hashtags
    youtube_title = f"{raw_title} - Mr Skelly Vibes 💀"

    # -- YOUTUBE UPLOAD --
    try:
        print("🎥 YouTube par upload chal raha hai...")
        youtube = get_google_service('youtube', 'v3')
        body = {
            'snippet': {
                'title': youtube_title,
                'description': full_description,
                'tags': ['shorts', 'skeleton', 'aesthetic'],
                'categoryId': '22'
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        yt_upload = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        ).execute()
        print(f"✅ YouTube Upload Success! ID: {yt_upload.get('id')}")
    except Exception as e:
        print(f"❌ YouTube Failed: {e}")

    # -- INSTAGRAM UPLOAD (USING SETTINGS) --
    try:
        print("📸 Instagram setup kar raha hoon...")
        cl = Client()
        
        # GitHub Secret se settings uthana
        settings_json = os.environ['INSTA_SETTINGS']
        settings_dict = json.loads(settings_json)
        
        # Load settings and login
        cl.set_settings(settings_dict)
        cl.login(os.environ['INSTA_USERNAME'], os.environ['INSTA_PASSWORD'])
        print("✅ Login Successful (Bypassed IP Block)!")

        print("📸 Uploading Reel...")
        cl.clip_upload(file_path, caption=full_description)
        print("✅ Instagram Upload Success!")
        
    except Exception as e:
        print(f"❌ Instagram Failed: {e}")

    # -- CLEANUP --
    print("🧹 File move kar raha hoon...")
    drive_service.files().update(
        fileId=video_file['id'],
        addParents=done_folder_id,
        removeParents=queue_folder_id
    ).execute()
    
    if os.path.exists(file_path): os.remove(file_path)
    print("🎉 Mr Skelly ka kaam ho gaya!")

if __name__ == "__main__":
    main()
