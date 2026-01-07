import os
import json
import random
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from instagrapi import Client
from moviepy.editor import VideoFileClip, AudioFileClip
from moviepy.audio.fx.all import audio_loop # Music loop karne ke liye

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

# --- MAIN LOGIC ---
def main():
    print("🚀 Mr Skelly Bot (Sound Fix V2) Started...")

    drive_service = get_google_service('drive', 'v3')
    queue_folder_id = os.environ['DRIVE_QUEUE_FOLDER']
    done_folder_id = os.environ['DRIVE_DONE_FOLDER']

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
    raw_path = "raw_video.mp4"
    final_path = "final_video.mp4"
    print(f"📥 Video mili: {video_file['name']}")

    # -- DOWNLOAD VIDEO --
    request = drive_service.files().get_media(fileId=video_file['id'])
    with open(raw_path, "wb") as f:
        f.write(request.execute())
    print("✅ Video Downloaded.")

    # -- 🎵 STEP: ADD MUSIC (SOUND FIX) 🎵 --
    try:
        print("🎶 Mixing music from assets/music.mp3...")
        music_path = "assets/music.mp3" 
        
        # FIX 1: audio=False se video ka purana sound hat jayega
        v_clip = VideoFileClip(raw_path, audio=False) 
        a_clip = AudioFileClip(music_path)

        # FIX 2: Music ki duration adjust karna
        if a_clip.duration > v_clip.duration:
            # Agar music lamba hai toh kaat do
            a_clip = a_clip.subclip(0, v_clip.duration)
        else:
            # Agar music chota hai toh use repeat (loop) karo
            a_clip = audio_loop(a_clip, duration=v_clip.duration)
        
        final_video = v_clip.set_audio(a_clip)
        
        # FIX 3: Explicitly specify fps and audio codec
        final_video.write_videofile(
            final_path, 
            codec="libx264", 
            audio_codec="aac", 
            temp_audiofile='temp-audio.m4a', 
            remove_temp=True, 
            fps=v_clip.fps,
            logger=None
        )
        
        v_clip.close()
        a_clip.close()
        upload_file = final_path
        print("✅ Music Merged Successfully with Fixes!")
    except Exception as e:
        print(f"⚠️ Music add nahi ho payi: {e}")
        upload_file = raw_path

    # -- PREPARE CONTENT --
    raw_title = os.path.splitext(video_file['name'])[0]
    captions = [
        f"Silence speaks when words can't. 💀🌙\n👇 Comment 'YES' if you feel this.",
        f"Just a skeleton waiting for something good. 🦴⏳\nDouble tap if you relate!",
        f"Life is short, make it spooky. 💀✨",
        f"POV: Peace found in lofi vibes. 🥀💀"
    ]
    
    hashtag_sets = [
        "#mrskelly #skeleton #lofi #aesthetic #trending #viral #reelsindia #shorts",
        "#skullart #animation #blender #vibes #fyp #explorepage #digitalart #relatable",
        "#darkart #skeletonart #lofihiphop #aestheticvibes #nightvibes #viralshorts"
    ]
    
    full_description = f"{random.choice(captions)}\n.\n.\n{random.choice(hashtag_sets)}"
    youtube_title = f"{raw_title} - Mr Skelly Vibes 💀"

    # -- YOUTUBE UPLOAD --
    try:
        print("🎥 YouTube uploading...")
        youtube = get_google_service('youtube', 'v3')
        body = {
            'snippet': {
                'title': youtube_title,
                'description': full_description,
                'tags': ['shorts', 'skeleton', 'aesthetic', 'lofi'],
                'categoryId': '22'
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        media = MediaFileUpload(upload_file, chunksize=-1, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print("✅ YouTube Success!")
    except Exception as e: print(f"❌ YouTube Failed: {e}")

    # -- INSTAGRAM UPLOAD --
    try:
        print("📸 Instagram uploading...")
        cl = Client()
        cl.set_settings(json.loads(os.environ['INSTA_SETTINGS']))
        cl.login(os.environ['INSTA_USERNAME'], os.environ['INSTA_PASSWORD'])
        cl.video_upload(upload_file, caption=full_description)
        print("✅ Instagram Success!")
    except Exception as e: print(f"❌ Instagram Failed: {e}")

    # -- CLEANUP --
    print("🧹 Cleaning up...")
    drive_service.files().update(
        fileId=video_file['id'], addParents=done_folder_id, removeParents=queue_folder_id
    ).execute()
    
    if os.path.exists(raw_path): os.remove(raw_path)
    if os.path.exists(final_path): os.remove(final_path)
    print("🎉 Task Completed!")

if __name__ == "__main__":
    main()
