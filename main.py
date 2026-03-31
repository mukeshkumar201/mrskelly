import os
import json
import time

# --- PIL FIX (Pillow 10+ ne ANTIALIAS hata diya, ye patch zaroori hai) ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from instagrapi import Client

# --- VIDEO EDITING ---
from moviepy.editor import VideoFileClip, AudioFileClip, vfx
from moviepy.audio.fx.all import audio_loop

# --- AI CAPTION ---
from groq import Groq

# --- 1. GROQ CAPTION GENERATOR ---
def generate_caption(video_title):
    """Har video ke liye AI se unique caption generate karo — 3 retries ke saath"""

    FALLBACK_CAPTIONS = [
        "Some things hurt more in silence. 💀🌙\nComment if you relate 👇\n.\n.\n.\n.\n.\n#mrskelly #skeleton #aesthetic #viral #reels #explore #trending #fyp #darkart #motivation",
        "Not all wounds are visible. 🥀💀\nComment if you relate 👇\n.\n.\n.\n.\n.\n#mrskelly #skeleton #aesthetic #viral #reels #explore #trending #fyp #skeletonart #lofi",
        "Still standing, barely. 💀⏳\nComment if you relate 👇\n.\n.\n.\n.\n.\n#mrskelly #skeleton #aesthetic #viral #reels #explore #trending #fyp #darkart #vibes",
        "Peace found in the darkest places. 🌑💀\nComment if you relate 👇\n.\n.\n.\n.\n.\n#mrskelly #skeleton #aesthetic #viral #reels #explore #trending #fyp #relatable #motivation",
    ]

    for attempt in range(3):  # 3 baar try karega
        try:
            client = Groq(api_key=os.environ['GROQ_API_KEY'])

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "user",
                        "content": f"""Instagram page "Mr Skelly" ke liye caption banao.
Video title: "{video_title}"

Exactly is format mein likho:
- 1 emotional English line (max 8 words, relatable feeling)
- 2-3 emojis
- "Comment if you relate 👇"
- 5 dots alag alag line pe:
.
.
.
.
.
- Hashtags: #mrskelly #skeleton #aesthetic #viral #reels #explore #trending #fyp #darkart #motivation #skeletonart #lofi #vibes #relatable

Sirf caption do. Koi explanation mat do. Koi quotes mat lagao."""
                    }
                ],
                max_tokens=250,
                temperature=0.9
            )

            caption = completion.choices[0].message.content.strip()
            print(f"✅ Caption Generated: {caption[:60]}...")
            return caption

        except Exception as e:
            print(f"⚠️ Groq Attempt {attempt + 1}/3 Failed: {e}")
            if attempt < 2:
                time.sleep(5)  # 5 second wait karke dobara try
            else:
                import random
                fallback = random.choice(FALLBACK_CAPTIONS)
                print(f"⚠️ Using fallback caption.")
                return fallback


# --- 2. SETUP GOOGLE LOGIN ---
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


# --- 3. VIDEO EDITING FUNCTION ---
def process_video(raw_path, final_path, music_path):
    print("🎬 Editing Started...")

    # 1. Video Load (original audio hata ke background music dalenge)
    clip = VideoFileClip(raw_path, audio=False)

    # 2. Speed 1.05x (copyright protection - subtle change)
    clip = clip.fx(vfx.speedx, 1.05)

    # 3. Color Boost (thoda zyada vibrant)
    clip = clip.fx(vfx.colorx, 1.3)

    # 4. Brightness + Contrast (copyright protection ke liye)
    #    White border HATAYA gaya hai - full screen experience ke liye
    clip = clip.fx(vfx.lum_contrast, lum=10, contrast=0.1)

    # 5. Edges se thoda crop (border ki jagah, full screen bana rehta hai)
    clip = clip.crop(x1=8, y1=8, x2=clip.w - 8, y2=clip.h - 8)

    # 6. Original size pe resize wapas
    clip = clip.resize((1080, 1920))

    # 7. Background Music
    try:
        print(f"🎶 Adding Music: {music_path}")
        audio = AudioFileClip(music_path)

        if audio.duration < clip.duration:
            audio = audio_loop(audio, duration=clip.duration)
        else:
            audio = audio.subclip(0, clip.duration)

        clip = clip.set_audio(audio)
    except Exception as e:
        print(f"⚠️ Music Error (Skipping): {e}")

    # 8. Save
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
    music_path = "assets/background.mp3"

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

    # -- AI SE CAPTION GENERATE KARO --
    raw_title = os.path.splitext(video_file['name'])[0]
    print(f"🤖 Generating AI Caption for: {raw_title}")
    full_description = generate_caption(raw_title)

    youtube_title = f"{raw_title} - Mr Skelly Vibes 💀"

    # -- YOUTUBE UPLOAD --
    try:
        print("🎥 YouTube Uploading...")
        youtube = get_google_service('youtube', 'v3')
        body = {
            'snippet': {
                'title': youtube_title,
                'description': full_description,
                'tags': ['shorts', 'skeleton', 'aesthetic', 'lofi', 'mrskelly'],
                'categoryId': '22'
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        media = MediaFileUpload(upload_file, chunksize=-1, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print("✅ YouTube Upload Success!")
    except Exception as e:
        print(f"❌ YouTube Failed: {e}")

    # -- INSTAGRAM UPLOAD --
    try:
        print("📸 Instagram Uploading...")
        cl = Client()

        proxy = os.environ.get('IG_PROXY')
        if proxy:
            cl.set_proxy(proxy)

        settings = os.environ.get('INSTA_SETTINGS')
        if settings:
            cl.set_settings(json.loads(settings))

        cl.login(os.environ['INSTA_USERNAME'], os.environ['INSTA_PASSWORD'])
        cl.clip_upload(upload_file, full_description)
        print("✅ Instagram Upload Success!")
    except Exception as e:
        print(f"❌ Instagram Failed: {e}")
        import traceback
        traceback.print_exc()

    # -- CLEANUP --
    print("🧹 Cleaning up...")
    try:
        drive_service.files().update(
            fileId=video_file['id'],
            addParents=done_folder_id,
            removeParents=queue_folder_id
        ).execute()
    except Exception as e:
        print(f"⚠️ Drive Move Failed: {e}")

    if os.path.exists(raw_path):
        os.remove(raw_path)
    if os.path.exists(final_path):
        os.remove(final_path)
    print("🎉 All Done! Bot Finished.")


if __name__ == "__main__":
    main()
