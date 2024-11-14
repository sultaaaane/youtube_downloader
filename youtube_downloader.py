from pytubefix import YouTube
from pydub import AudioSegment
import os
import sys
from pathlib import Path

def create_download_directories():
    home = str(Path.home())
    video_dir = os.path.join(home, "Desktop", "Videos")
    audio_dir = os.path.join(home, "Desktop", "Music")
    
    os.makedirs(video_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    
    return video_dir, audio_dir

def get_video_info(url):
    try:
        yt = YouTube(url)
        return yt
    except Exception as e:
        print(f"Error fetching video information: {str(e)}")
        print("This might be due to:")
        print("1. Invalid YouTube URL")
        print("2. Network connectivity issues")
        print("3. YouTube API changes")
        sys.exit(1)

def download_video(yt, video_dir):
    try:
        video_streams = yt.streams.filter(only_video=True, mime_type="video/mp4")
        if not video_streams:
            print("No video streams found!")
            return
        
        print("\nAvailable video qualities:")
        for stream in video_streams:
            print(f" {stream.itag}- Resolution: {stream.resolution}, FPS: {stream.fps}")
        
        itag = int(input("\nEnter the itag number for your desired quality: "))
        stream = yt.streams.get_by_itag(itag)
        if not stream:
            print("Invalid itag selected!")
            return
        
        print(f"\nDownloading: {yt.title}")
        stream.download(video_dir)
        print(f"Video downloaded successfully to: {video_dir}")
        
    except Exception as e:
        print(f"Error during video download: {str(e)}")

def download_audio(yt, audio_dir):
    try:
        audio_streams = yt.streams.filter(only_audio=True, mime_type="audio/mp4")
        if not audio_streams:
            print("No audio streams found!")
            return
        
        print("\nAvailable audio qualities:")
        for stream in audio_streams:
            print(f" {stream.itag}- Bitrate: {stream.abr}")
        
        itag = int(input("\nEnter the itag number for your desired quality: "))
        stream = yt.streams.get_by_itag(itag)
        if not stream:
            print("Invalid itag selected!")
            return
        
        default_filename = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_'))
        print(f"\nDefault filename: {default_filename}")
        custom_filename = input("Enter a custom filename (press Enter to use default): ").strip()
        
        filename = custom_filename if custom_filename else default_filename
        mp4_path = os.path.join(audio_dir, f"{filename}.mp4")
        mp3_path = os.path.join(audio_dir, f"{filename}.mp3")
        
        print(f"\nDownloading: {yt.title}")
        stream.download(audio_dir, filename=f"{filename}.mp4")
        
        print("Converting to MP3...")
        try:
            audio = AudioSegment.from_file(mp4_path, format="mp4")
            audio.export(mp3_path, format="mp3")
            os.remove(mp4_path)
            print(f"Audio downloaded and converted successfully to: {mp3_path}")
        except Exception as e:
            print(f"Error during conversion: {str(e)}")
            print("Note: Make sure you have ffmpeg installed on your system.")
            if os.path.exists(mp4_path):
                print(f"MP4 file is still available at: {mp4_path}")
            
    except Exception as e:
        print(f"Error during audio download: {str(e)}")

def main():
    video_dir, audio_dir = create_download_directories()
    
    print("YouTube Downloader")
    print("-----------------")
    url = input("Paste your YouTube link: ").strip()
    
    yt = get_video_info(url)
    print(f"\nTitle: {yt.title}")
    print(f"Length: {yt.length} seconds")
    print(f"Views: {yt.views:,}")
    
    while True:
        print("\nOptions:")
        print("1. Download Video")
        print("2. Download Audio (MP3)")
        print("3. Exit")
        
        try:
            choice = int(input("\nEnter your choice (1-3): "))
            if choice == 1:
                download_video(yt, video_dir)
            elif choice == 2:
                download_audio(yt, audio_dir)
            elif choice == 3:
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    main()