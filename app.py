import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from imageio_ffmpeg import get_ffmpeg_exe
from pydantic import BaseModel
from starlette.background import BackgroundTask
from yt_dlp import YoutubeDL


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


def ytdlp_options() -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
        "extractor_retries": 3,
    }
    node = shutil.which("node")
    if node:
        options["js_runtimes"] = {"node": {"path": node}}
    return options


def extract_video(url: str) -> dict[str, Any]:
    options = {
        **ytdlp_options(),
        "skip_download": True,
        "noplaylist": True,
    }
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=False)
    if not info:
        raise HTTPException(status_code=404, detail="No video information was found.")
    return info


def extract_playlist(url: str) -> tuple[str, list[dict[str, str]]]:
    options = {
        **ytdlp_options(),
        "skip_download": True,
        "extract_flat": "in_playlist",
    }
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=False)

    if not info or not info.get("entries"):
        raise HTTPException(status_code=404, detail="No videos were found in this playlist.")

    entries: list[dict[str, str]] = []
    for entry in info["entries"]:
        if not entry:
            continue
        video_url = entry.get("webpage_url") or entry.get("url")
        if video_url and not video_url.startswith(("http://", "https://")):
            video_url = f"https://www.youtube.com/watch?v={video_url}"
        if video_url:
            entries.append(
                {
                    "url": video_url,
                    "title": entry.get("title") or entry.get("id") or "video",
                }
            )

    if not entries:
        raise HTTPException(status_code=404, detail="No videos were found in this playlist.")
    return info.get("title") or "YouTube Playlist", entries


def available_qualities(info: dict[str, Any]) -> list[str]:
    heights = {
        int(media_format["height"])
        for media_format in info.get("formats", [])
        if media_format.get("vcodec") not in {None, "none"}
        and isinstance(media_format.get("height"), (int, float))
        and media_format["height"] > 0
    }
    return [f"{height}p" for height in sorted(heights)]


def requested_height(quality: str) -> int:
    if not quality.endswith("p") or not quality[:-1].isdigit():
        raise HTTPException(status_code=400, detail="Select a valid video quality.")
    return int(quality[:-1])


def download_media(
    video_url: str,
    output_dir: Path,
    output_stem: str,
    file_format: Literal["mp4", "mp3"],
    quality: str,
) -> tuple[Path, str]:
    """Download one video and return its path and response media type."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = require_ffmpeg()
    options = {
        **ytdlp_options(),
        "noplaylist": True,
        "outtmpl": str(output_dir / f"{output_stem}.%(ext)s"),
        "ffmpeg_location": ffmpeg,
        "overwrites": True,
    }

    if file_format == "mp3":
        options.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "0",
                    }
                ],
            }
        )
        extension = "mp3"
        media_type = "audio/mpeg"
    else:
        height = requested_height(quality)
        options.update(
            {
                "format": (
                    f"bestvideo[height<={height}]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]/best"
                ),
                "merge_output_format": "mp4",
            }
        )
        extension = "mp4"
        media_type = "video/mp4"

    with YoutubeDL(options) as downloader:
        downloader.extract_info(video_url, download=True)

    expected_output = output_dir / f"{output_stem}.{extension}"
    if expected_output.is_file():
        return expected_output, media_type

    candidates = [
        path
        for path in output_dir.glob(f"{output_stem}.*")
        if path.is_file() and path.suffix not in {".part", ".ytdl"}
    ]
    if not candidates:
        raise HTTPException(status_code=500, detail="The downloaded file could not be located.")
    return candidates[0], media_type


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
        info = extract_video(url)
        return {
            "title": info.get("title") or "YouTube Video",
            "length": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "qualities": available_qualities(info),
            "count": 1,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not read that YouTube video: {error}",
        ) from error


@app.get("/api/media-info")
def media_info(
    url: str = Query(...),
    download_type: Literal["video", "playlist"] = Query("video"),
) -> dict:
    if download_type == "video":
        return video_info(url)

    url = validate_playlist_url(url)
    try:
        title, entries = extract_playlist(url)
        qualities: set[str] = set()
        failed_items = 0

        with ThreadPoolExecutor(max_workers=min(4, len(entries))) as executor:
            futures = {
                executor.submit(extract_video, entry["url"]): entry
                for entry in entries
            }
            for future in as_completed(futures):
                try:
                    qualities.update(available_qualities(future.result()))
                except Exception:
                    failed_items += 1

        ordered_qualities = sorted(
            qualities,
            key=lambda resolution: int(resolution.removesuffix("p")),
        )
        if not ordered_qualities:
            raise HTTPException(
                status_code=502,
                detail="Could not determine the available qualities for this playlist.",
            )
        return {
            "title": title,
            "count": len(entries),
            "qualities": ordered_qualities,
            "metadata_failures": failed_items,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not read that YouTube playlist: {error}",
        ) from error


@app.post("/api/download")
def download(request: DownloadRequest) -> FileResponse:
    url = validate_youtube_url(request.url)
    work_dir = Path(tempfile.mkdtemp(prefix="youtube-downloader-"))

    try:
        info = extract_video(url)
        title = safe_filename(info.get("title") or "download")
        output, media_type = download_media(
            url,
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
        raw_playlist_title, entries = extract_playlist(url)
        playlist_title = safe_filename(raw_playlist_title)
        errors: list[str] = []
        downloaded = 0

        for position, entry in enumerate(entries, start=1):
            item_dir = staging_dir / str(position)
            try:
                numbered_title = f"{position:03d} - {safe_filename(entry['title'])}"
                item_path, _ = download_media(
                    entry["url"],
                    item_dir,
                    numbered_title,
                    request.format,
                    request.quality,
                )
                shutil.move(str(item_path), media_dir / item_path.name)
                downloaded += 1
            except Exception as error:
                detail = error.detail if isinstance(error, HTTPException) else str(error)
                errors.append(f"{position:03d} | {entry['url']} | {detail}")
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
