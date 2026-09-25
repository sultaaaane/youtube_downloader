```markdown
# YouTube Downloader

A simple Python script to download videos or audio from YouTube. The program uses the `pytubefix` library to fetch video or audio streams and allows the user to choose between downloading either a video or an audio file. The audio files are automatically converted from MP4 to MP3 format using the `pydub` library.
```
## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)

## Features

- Download YouTube videos in different resolutions.
- Download YouTube audio and convert it to MP3 format.
- Clean up original downloaded audio files after conversion.

## Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/youtube-downloader.git
   cd youtube-downloader
   ```

2. **Create an environment and install the dependencies:**
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

The web backend includes an FFmpeg binary through `imageio-ffmpeg`, so MP3 conversion and high-resolution MP4 merging work without a separate system install. The original command-line script still requires a system FFmpeg installation.

## Web app usage

1. **Run the FastAPI server:**
   ```bash
   .venv/bin/uvicorn app:app --reload
   ```

2. Open `http://127.0.0.1:8000`, choose a single video or an entire playlist, paste its YouTube URL, select the format and quality, and press Download. Playlist downloads are returned as a ZIP file; unavailable items are skipped and documented in `_download_errors.txt` inside the ZIP.

The API also exposes interactive documentation at `http://127.0.0.1:8000/docs`.

## Command-line usage

Run the original interactive script with:

```bash
.venv/bin/python youtube_downloader.py
```

## Dependencies

- [pytubefix](https://pytubefix.io/): Python library for downloading YouTube videos.
- [pydub](https://pydub.com/): Python library for manipulating audio.
- [ffmpeg](https://ffmpeg.org/): A complete, cross-platform solution to record, convert and stream audio and video.
- [FastAPI](https://fastapi.tiangolo.com/): Web API framework used by the browser interface.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```
