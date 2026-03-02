# YouTube Transcript Module

File: `src/ia_phase1/youtube_transcript.py`

## What it does

- Detects YouTube URLs and extracts video IDs.
- Downloads manual/automatic subtitle tracks using `yt-dlp` (subtitle-only, no video download).
- Cleans VTT/SRT caption artifacts into transcript text.
- Saves transcript text files under a per-video folder.

## API

- `extract_youtube_video_id(source: str) -> Optional[str]`
- `is_youtube_url(source: str) -> bool`
- `download_youtube_transcript(video_url: str, output_dir: Optional[Path] = None, preferred_langs: Optional[List[str]] = None) -> Dict[str, Any]`

## Usage

```python
from ia_phase1.youtube_transcript import download_youtube_transcript

result = download_youtube_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(result["video_id"])
print(result["transcript_path"])
```

## Key environment variables

- `IA_PHASE1_TRANSCRIPT_OUTPUT_DIR` (preferred)
- `YOUTUBE_TRANSCRIPT_OUTPUT_DIR` (fallback)

If unset, default output root is: `.ia_phase1_data/transcripts`.

## Dependencies

Install from `requirements.txt` in this folder.
