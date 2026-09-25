import asyncio
import zipfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from app import (
    DownloadRequest,
    available_qualities,
    download_playlist,
    validate_playlist_url,
)


class PlaylistDownloadTests(TestCase):
    def test_playlist_url_requires_list_parameter(self) -> None:
        with self.assertRaises(HTTPException) as context:
            validate_playlist_url("https://www.youtube.com/watch?v=video-id")

        self.assertEqual(context.exception.status_code, 400)

    def test_playlist_is_packaged_as_numbered_zip(self) -> None:
        playlist = (
            "Demo Playlist",
            [
                {"url": "https://youtu.be/one", "title": "First"},
                {"url": "https://youtu.be/two", "title": "Second"},
            ],
        )

        def fake_download_media(video_url, output_dir, output_stem, file_format, quality):
            output_dir.mkdir(parents=True, exist_ok=True)
            output = output_dir / f"{output_stem}.{file_format}"
            output.write_bytes(video_url.encode("utf-8"))
            return output, "video/mp4"

        request = DownloadRequest(
            url="https://www.youtube.com/playlist?list=demo",
            format="mp4",
            quality="720p",
        )

        with (
            patch("app.extract_playlist", return_value=playlist),
            patch("app.download_media", side_effect=fake_download_media),
        ):
            response = download_playlist(request)

        archive_path = Path(response.path)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["001 - First.mp4", "002 - Second.mp4"],
                )
        finally:
            asyncio.run(response.background())

    def test_available_qualities_are_dynamic_and_sorted(self) -> None:
        info = {
            "formats": [
                {"height": 2160, "vcodec": "av01"},
                {"height": 720, "vcodec": "avc1"},
                {"height": 1080, "vcodec": "vp9"},
                {"height": None, "vcodec": "none"},
                {"height": 2160, "vcodec": "vp9"},
            ]
        }

        self.assertEqual(available_qualities(info), ["720p", "1080p", "2160p"])
