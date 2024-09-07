Here's the README in a single block for easy copying:

---

```markdown
# YouTube Downloader

A simple Python script to download videos or audio from YouTube. The program uses the `pytube` library to fetch video or audio streams and allows the user to choose between downloading either a video or an audio file. The audio files are automatically converted from MP4 to MP3 format using the `pydub` library.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
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

2. **Install required dependencies:**
   Make sure you have Python installed. Then, install the necessary libraries:
   ```bash
   pip install pytube
   pip install pydub
   ```

3. **Install `ffmpeg`:**
   The `pydub` library requires `ffmpeg` to be installed on your system. Download and install it from [ffmpeg.org](https://ffmpeg.org/download.html).

## Usage

1. **Run the script:**
   Execute the Python script:
   ```bash
   python downloader.py
   ```

2. **Input the YouTube link:**
   Paste the YouTube link when prompted.

3. **Choose the download option:**
   - Enter `1` for video download.
   - Enter `2` for audio download.

4. **Select desired quality:**
   - For video, select the desired resolution.
   - For audio, choose the desired bitrate.

5. **Follow on-screen instructions:**
   - Provide a custom filename for the audio download.
   - The audio will be converted to MP3, and the original file will be removed after conversion.

## Dependencies

- [pytube](https://pytube.io/): Python library for downloading YouTube videos.
- [pydub](https://pydub.com/): Python library for manipulating audio.
- [ffmpeg](https://ffmpeg.org/): A complete, cross-platform solution to record, convert and stream audio and video.

## Configuration

- Modify the download paths in the script (`'/Users/moham/Videos'` for video and `'/Users/moham/Music'` for audio) to match your local system's directories.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
