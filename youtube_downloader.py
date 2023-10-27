from pytube import YouTube
from pydub import AudioSegment
import os

link = input("paste your youtube link below : \n")
yt = YouTube(link)

print("Title :", yt.title)

streams = yt.streams
video_streams = streams.filter(only_video=True, mime_type="video/mp4") 
audio_streams = streams.filter(only_audio=True, mime_type="audio/mp4")

choice = int(input("choose 1 if you want video and 2 if you want audio : "))

if (choice == 1):    
    for streams in video_streams:
        print(f" {streams.itag}- {streams.resolution}")
    itag = int(input("enter the itag you want : "))
    stream = yt.streams.get_by_itag(itag)
    stream.download('/Users/moham/Videos')
elif (choice == 2):
    for streams in audio_streams:
        print(f" {streams.itag}- {streams.abr}")
    itag = int(input("enter the itag you want : "))
    stream = yt.streams.get_by_itag(itag)
    custom_filename = input("Enter a custom filename for the download: ")
    mp4_file_path = f'/Users/moham/Music/{custom_filename}'
    stream.download('/Users/moham/Music', filename=custom_filename)
    audio_file = AudioSegment.from_file(f'/Users/moham/Music/{custom_filename}', format="mp4")
    audio_file.export(f'/Users/moham/Music/{custom_filename}.mp3', format="mp3")
    
    if os.path.exists(mp4_file_path):
        os.remove(mp4_file_path)
        print(f"Deleted {custom_filename}.mp4 after conversion.")
    
    print(f"Downloaded and converted {custom_filename} to MP3.")
else:
    print("invalid choice")

