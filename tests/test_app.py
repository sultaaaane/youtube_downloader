import asyncio
import zipfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from app import DownloadRequest, download_playlist, validate_playlist_url


class PlaylistDownloadTests(TestCase):
    def test_playlist_url_requires_list_parameter(self) -> None:
        with self.assertRaises(HTTPException) as context:
            validate_playlist_url("https://www.youtube.com/watch?v=video-id")

        self.assertEqual(context.exception.status_code, 400)

    def test_playlist_is_packaged_as_numbered_zip(self) -> None:
        class FakePlaylist:
            title = "Demo Playlist"
            video_urls = ["https://youtu.be/one", "https://youtu.be/two"]

            def __init__(self, _url: str) -> None:
                pass

        class FakeVideo:
            def __init__(self, url: str) -> None:
                self.title = "First" if url.endswith("one") else "Second"

        def fake_download_media(video, output_dir, output_stem, file_format, quality):
            output_dir.mkdir(parents=True, exist_ok=True)
            output = output_dir / f"{output_stem}.{file_format}"
            output.write_bytes(video.title.encode("utf-8"))
            return output, "video/mp4"

        request = DownloadRequest(
            url="https://www.youtube.com/playlist?list=demo",
            format="mp4",
            quality="720p",
        )

        with (
            patch("app.Playlist", FakePlaylist),
            patch("app.YouTube", FakeVideo),
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
