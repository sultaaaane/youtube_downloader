import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from imageio_ffmpeg import get_ffmpeg_exe
from pydantic import BaseModel
from pytubefix import Playlist, YouTube
from starlette.background import BackgroundTask


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="YouTube Downloader", version="1.0.0")
app.mount("/styles", StaticFiles(directory=BASE_DIR / "styles"), name="styles")


class DownloadRequest(BaseModel):
    url: str
    format: Literal["mp4", "mp3"]
    quality: str = "720p"


def validate_youtube_url(url: str) -> str:
    """Accept only HTTP(S) links to YouTube-owned video hosts."""
    candidate = url.strip()
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()

    allowed_host = (
        host == "youtu.be"
        or host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtube-nocookie.com"
        or host.endswith(".youtube-nocookie.com")
    )
    if parsed.scheme not in {"http", "https"} or not allowed_host:
        raise HTTPException(status_code=400, detail="Enter a valid YouTube URL.")

    return candidate


def validate_playlist_url(url: str) -> str:
    candidate = validate_youtube_url(url)
    playlist_ids = parse_qs(urlparse(candidate).query).get("list", [])
    if not playlist_ids or not playlist_ids[0].strip():
        raise HTTPException(status_code=400, detail="Enter a valid YouTube playlist URL.")
    return candidate


def safe_filename(value: str) -> str:
    cleaned = "".join(
        character
        for character in value
        if character.isalnum() or character in {" ", "-", "_", "."}
    ).strip(" .")
    return cleaned[:150] or "download"


def require_ffmpeg() -> str:
    executable = shutil.which("ffmpeg") or get_ffmpeg_exe()
    if not executable or not Path(executable).is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "FFmpeg is required for MP3 and high-resolution MP4 downloads, "
                "but no usable executable was found."
            ),
        )
    return str(executable)


def run_ffmpeg(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip().splitlines()[-1] if error.stderr else str(error)
        raise HTTPException(status_code=500, detail=f"FFmpeg failed: {message}") from error


def download_media(
    video: YouTube,
    output_dir: Path,
    output_stem: str,
    file_format: Literal["mp4", "mp3"],
    quality: str,
) -> tuple[Path, str]:
    """Download one video and return its path and response media type."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if file_format == "mp3":
        ffmpeg = require_ffmpeg()
        stream = video.streams.filter(only_audio=True).order_by("abr").desc().first()
        if stream is None:
            raise HTTPException(status_code=404, detail="No audio stream was found.")

        source = Path(
            stream.download(output_path=output_dir, filename=f".{output_stem}-audio-source.mp4")
        )
        output = output_dir / f"{output_stem}.mp3"
        run_ffmpeg(
            [
                ffmpeg,
                "-y",
                "-i",
                str(source),
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(output),
            ]
        )
        source.unlink(missing_ok=True)
        return output, "audio/mpeg"

    progressive = (
        video.streams.filter(
            progressive=True,
            mime_type="video/mp4",
            res=quality,
        )
        .order_by("fps")
        .desc()
        .first()
    )

    if progressive is not None:
        output = Path(
            progressive.download(output_path=output_dir, filename=f"{output_stem}.mp4")
        )
        return output, "video/mp4"

    video_stream = (
        video.streams.filter(
            only_video=True,
            mime_type="video/mp4",
            res=quality,
        )
        .order_by("fps")
        .desc()
        .first()
    )
    if video_stream is None:
        raise HTTPException(
            status_code=404,
            detail=f"The {quality} MP4 quality is unavailable for this video.",
        )

    ffmpeg = require_ffmpeg()
    audio_stream = (
        video.streams.filter(only_audio=True, mime_type="audio/mp4")
        .order_by("abr")
        .desc()
        .first()
    )
    if audio_stream is None:
        raise HTTPException(status_code=404, detail="No compatible audio stream was found.")

    video_path = Path(
        video_stream.download(output_path=output_dir, filename=f".{output_stem}-video-source.mp4")
    )
    audio_path = Path(
        audio_stream.download(output_path=output_dir, filename=f".{output_stem}-audio-source.mp4")
    )
    output = output_dir / f"{output_stem}.mp4"
    run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c",
            "copy",
            str(output),
        ]
    )
    video_path.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)
    return output, "video/mp4"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/video-info")
def video_info(url: str = Query(...)) -> dict:
    url = validate_youtube_url(url)
    try:
        video = YouTube(url)
        resolutions = {
            stream.resolution
            for stream in video.streams.filter(mime_type="video/mp4")
            if stream.resolution
        }
        ordered_resolutions = sorted(
            resolutions,
            key=lambda resolution: int(resolution.removesuffix("p")),
        )
        return {
            "title": video.title,
            "length": video.length,
            "thumbnail": video.thumbnail_url,
            "qualities": ordered_resolutions,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not read that YouTube video: {error}",
        ) from error


@app.post("/api/download")
def download(request: DownloadRequest) -> FileResponse:
    url = validate_youtube_url(request.url)
    work_dir = Path(tempfile.mkdtemp(prefix="youtube-downloader-"))

    try:
        video = YouTube(url)
        title = safe_filename(video.title)
        output, media_type = download_media(
            video,
            work_dir,
            title,
            request.format,
            request.quality,
        )

        return FileResponse(
            output,
            media_type=media_type,
            filename=output.name,
            background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
        )
    except HTTPException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(
            status_code=502,
            detail=f"The download could not be completed: {error}",
        ) from error


@app.post("/api/download-playlist")
def download_playlist(request: DownloadRequest) -> FileResponse:
    url = validate_playlist_url(request.url)
    work_dir = Path(tempfile.mkdtemp(prefix="youtube-playlist-"))
    media_dir = work_dir / "downloads"
    staging_dir = work_dir / "staging"
    media_dir.mkdir()
    staging_dir.mkdir()

    try:
        playlist = Playlist(url)
        video_urls = list(playlist.video_urls)
        if not video_urls:
            raise HTTPException(status_code=404, detail="No videos were found in this playlist.")

        playlist_title = safe_filename(playlist.title or "YouTube Playlist")
        errors: list[str] = []
        downloaded = 0

        for position, video_url in enumerate(video_urls, start=1):
            item_dir = staging_dir / str(position)
            try:
                video = YouTube(video_url)
                numbered_title = f"{position:03d} - {safe_filename(video.title)}"
                item_path, _ = download_media(
                    video,
                    item_dir,
                    numbered_title,
                    request.format,
                    request.quality,
                )
                shutil.move(str(item_path), media_dir / item_path.name)
                downloaded += 1
            except Exception as error:
                detail = error.detail if isinstance(error, HTTPException) else str(error)
                errors.append(f"{position:03d} | {video_url} | {detail}")
            finally:
                shutil.rmtree(item_dir, ignore_errors=True)

        if downloaded == 0:
            first_error = errors[0] if errors else "Unknown playlist error"
            raise HTTPException(
                status_code=502,
                detail=f"No playlist videos could be downloaded. First error: {first_error}",
            )

        if errors:
            error_report = media_dir / "_download_errors.txt"
            error_report.write_text(
                "Some playlist items could not be downloaded:\n\n" + "\n".join(errors),
                encoding="utf-8",
            )

        archive_base = work_dir / playlist_title
        archive_path = Path(
            shutil.make_archive(str(archive_base), "zip", root_dir=media_dir)
        )
        return FileResponse(
            archive_path,
            media_type="application/zip",
            filename=archive_path.name,
            background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
        )
    except HTTPException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(
            status_code=502,
            detail=f"The playlist download could not be completed: {error}",
        ) from error
