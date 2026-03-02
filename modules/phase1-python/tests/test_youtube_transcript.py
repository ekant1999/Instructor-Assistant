from __future__ import annotations

from pathlib import Path

import pytest
from yt_dlp.utils import DownloadError

from ia_phase1 import youtube_transcript as yt


def test_extract_youtube_video_id_variants() -> None:
    assert yt.extract_youtube_video_id("https://www.youtube.com/watch?v=abc123XYZ") == "abc123XYZ"
    assert yt.extract_youtube_video_id("https://youtu.be/abc123XYZ") == "abc123XYZ"
    assert yt.extract_youtube_video_id("https://www.youtube.com/shorts/abc123XYZ") == "abc123XYZ"
    assert yt.extract_youtube_video_id("https://example.com/watch?v=abc123XYZ") is None
    assert yt.is_youtube_url("https://m.youtube.com/watch?v=abc123XYZ")
    assert not yt.is_youtube_url("https://example.com/video")


def test_download_youtube_transcript_writes_clean_txt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {"id": "vid123", "title": "Demo Video"}

        def download(self, _urls):
            outtmpl = str(self.opts["outtmpl"])
            vtt_path = Path(outtmpl.replace("%(id)s", "vid123").replace("%(ext)s", "en.vtt"))
            vtt_path.parent.mkdir(parents=True, exist_ok=True)
            vtt_path.write_text(
                "WEBVTT\n\n"
                "00:00:00.000 --> 00:00:02.000\n"
                "Hello\n\n"
                "00:00:02.000 --> 00:00:04.000\n"
                "Hello world\n\n"
                "NOTE temporary\n"
                "drop this line\n\n"
                "00:00:04.000 --> 00:00:06.000\n"
                "<c.colorE5E5E5>Bye &amp; thanks</c>\n",
                encoding="utf-8",
            )
            return 0

    monkeypatch.setattr(yt.yt_dlp, "YoutubeDL", FakeYDL)
    result = yt.download_youtube_transcript(
        "https://www.youtube.com/watch?v=vid123",
        output_dir=tmp_path,
    )

    assert result["video_id"] == "vid123"
    assert result["title"] == "Demo Video"
    transcript_path = Path(result["transcript_path"])
    assert transcript_path.exists()
    text = transcript_path.read_text(encoding="utf-8")
    assert "Hello world" in text
    assert "Hello\n\nHello world" not in text
    assert "Bye & thanks" in text
    assert "WEBVTT" not in text


def test_download_youtube_transcript_tolerates_partial_caption_download_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {"id": "vid429", "title": "Rate Limited Video"}

        def download(self, _urls):
            outtmpl = str(self.opts["outtmpl"])
            vtt_path = Path(outtmpl.replace("%(id)s", "vid429").replace("%(ext)s", "en.vtt"))
            vtt_path.parent.mkdir(parents=True, exist_ok=True)
            vtt_path.write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nPartial but useful subtitle text\n",
                encoding="utf-8",
            )
            raise DownloadError("subtitle HTTP 429")

    monkeypatch.setattr(yt.yt_dlp, "YoutubeDL", FakeYDL)
    result = yt.download_youtube_transcript(
        "https://www.youtube.com/watch?v=vid429",
        output_dir=tmp_path,
    )

    assert result["video_id"] == "vid429"
    assert Path(result["transcript_path"]).exists()


def test_download_youtube_transcript_raises_when_no_caption_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {"id": "nosubs", "title": "No Subs"}

        def download(self, _urls):
            return 0

    monkeypatch.setattr(yt.yt_dlp, "YoutubeDL", FakeYDL)
    with pytest.raises(RuntimeError, match="No subtitles available"):
        yt.download_youtube_transcript(
            "https://www.youtube.com/watch?v=nosubs",
            output_dir=tmp_path,
        )
