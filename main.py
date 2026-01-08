import os
import json
import random
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from instagrapi import Client

# --- VIDEO EDITING ---
from moviepy.editor import VideoFileClip, AudioFileClip, vfx
from moviepy.audio.fx.all import audio_loop

# --- 1. SETUP GOOGLE LOGIN ---
def get_google_service(service_name, version):
    client_secret_data = json.loads(os.environ['G_CLIENT_SECRET'])
    config = client_secret_data['installed'] if 'installed' in client_secret_data else client_secret_data['web']

    creds = Credentials(
        None,
        refresh_token=os.environ['G_REFRESH_TOKEN'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config['client_id'],
        client_secret=config['client_secret']
    )
    return build(service_name, version, credentials=creds)

# --- 2. PRO EDITING FUNCTION (Speed + Color + Border + Music) ---
def process_video(raw_path, final_path, music_path):
    print("🎬 Editing Started: Speed, Color, Border & Music...")
    
    # 1. Video Load (Audio hata diya taaki background music dalein)
    clip = VideoFileClip(raw_path, audio=False)
    
    # 2. Speed 1.1x (Copyright Protection)
    clip = clip.fx(vfx.speedx, 1.1)
    
    # 3. Filter (Color Vibrance)
    clip = clip.fx(vfx.colorx, 1.2)
    
    # 4. Border (White Gap - Aesthetic Look)
    clip = clip.margin(top=40, bottom=40, left=40, right=40, color=(255, 255, 255))
    
    # 5. Background Music Logic
    try:
        print(f"🎶 Adding Music: {music_path}")
        audio = AudioFileClip(music_path)
        
        # Audio ko video ki length ke hisaab se loop ya cut karna
        if audio.duration < clip.duration:
            audio = audio_loop(audio, duration=clip.duration)
        else:
            audio = audio.subclip(0, clip.duration)
            
        clip = clip.set_audio(audio)
    except Exception as e:
        print(f"⚠️ Music Error (Skipping Music): {e}")

    # 6. Save Final Video
    clip.write_videofile(
        final_path, 
        codec="libx264", 
        audio_codec="aac", 
        fps=24,
        temp_audiofile='temp-audio.m4a', 
        remove_temp=True, 
        verbose=False, 
        logger=None
    )
    print("✅ Video Processing Complete!")

# --- MAIN LOGIC ---
def main():
    print("🚀 Mr Skelly Bot (Pro Version) Started...")

    # -- DRIVE SETUP --
    try:
        drive_service = get_google_service('drive', 'v3')
        queue_folder_id = os.environ['DRIVE_QUEUE_FOLDER']
        done_folder_id = os.environ['DRIVE_DONE_FOLDER']
    except Exception as e:
        print(f"❌ Login Error: {e}")
        return

    # -- CHECK FOR VIDEO --
    print("🔍 Checking Drive for videos...")
    results = drive_service.files().list(
        q=f"'{queue_folder_id}' in parents and mimeType contains 'video/' and trashed=false",
        fields="files(id, name)",
        pageSize=1
    ).execute()
    items = results.get('files', [])

    if not items:
        print("❌ Folder Khali Hai (No Videos).")
        return

    video_file = items[0]
    raw_path = "raw_video.mp4"
    final_path = "final_video.mp4"
    music_path = "assets/background.mp3" # Ensure this file exists in repo
    
    print(f"📥 Found Video: {video_file['name']}")

    # -- DOWNLOAD VIDEO --
    request = drive_service.files().get_media(fileId=video_file['id'])
    with open(raw_path, "wb") as f:
        f.write(request.execute())
    print("✅ Download Complete.")

    # -- EDIT & PROCESS --
    try:
        process_video(raw_path, final_path, music_path)
        upload_file = final_path
    except Exception as e:
        print(f"❌ Editing Failed: {e}. Uploading Raw Video.")
        upload_file = raw_path

    # -- PREPARE CAPTIONS --
    raw_title = os.path.splitext(video_file['name'])[0]
    
    captions = [
        f"Silence speaks when words can't. 💀🌙\n👇 Comment 'YES' if you feel this.",
        f"Just a skeleton waiting for something good. 🦴⏳\nDouble tap if you relate!",
        f"Life is short, make it spooky. 💀✨",
        f"POV: Found my peace in the dark. 🥀💀"
    ]
    
    hashtag_sets = [
        "#mrskelly #skeleton #lofi #aesthetic #trending #viral #reels #explore",
        "#skullart #animation #blender #vibes #fyp #explorepage #relatable",
        "#darkart #skeletonart #lofihiphop #moody #viralshorts #trendingreels"
    ]
    
    full_description = f"{random.choice(captions)}\n.\n.\n{random.choice(hashtag_sets)}"
    youtube_title = f"{raw_title} - Mr Skelly Vibes 💀"

    # -- YOUTUBE UPLOAD --
    try:
        print("🎥 YouTube Uploading...")
        youtube = get_google_service('youtube', 'v3')
        body = {
            'snippet': {
                'title': youtube_title,
                'description': full_description,
                'tags': ['shorts', 'skeleton', 'aesthetic', 'lofi'],
                'categoryId': '22' # People & Blogs (Best for general clips)
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        media = MediaFileUpload(upload_file, chunksize=-1, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print("✅ YouTube Upload Success!")
    except Exception as e: print(f"❌ YouTube Failed: {e}")

    # -- INSTAGRAM UPLOAD --
    try:
        print("📸 Instagram Uploading...")
        cl = Client()
        cl.set_settings(json.loads(os.environ['INSTA_SETTINGS']))
        cl.login(os.environ['INSTA_USERNAME'], os.environ['INSTA_PASSWORD'])
        
        cl.clip_upload(upload_file, full_description) # clip_upload is safer for Reels
        print("✅ Instagram Upload Success!")
    except Exception as e: print(f"❌ Instagram Failed: {e}")

    # -- CLEANUP --
    print("🧹 Cleaning up...")
    try:
        drive_service.files().update(
            fileId=video_file['id'], addParents=done_folder_id, removeParents=queue_folder_id
        ).execute()
    except Exception as e:
        print(f"⚠️ Drive Move Failed: {e}")

    if os.path.exists(raw_path): os.remove(raw_path)
    if os.path.exists(final_path): os.remove(final_path)
    print("🎉 All Done! Bot Finished.")

if __name__ == "__main__":
    main()
