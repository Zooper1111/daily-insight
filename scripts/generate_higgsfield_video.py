"""Generate and publish one 60-second Daily Insight story video.

The edition supplies six 10-second visual blocks plus six narration lines. The
Higgsfield credential stays in the server-side ``HF_KEY`` environment variable.
This pilot deliberately performs no automatic paid retries.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests
import soundfile as sf
from kokoro import KPipeline


ROOT = Path(__file__).resolve().parents[1]
EDITIONS_PATH = ROOT / "editions.json"
API_BASE = "https://api.higgsfield.ai"
MODEL_PATH = "minimax/h3/reference-to-video"
SECONDS_PER_BLOCK = 10
BLOCK_COUNT = 6
MAX_RATE_USD_PER_SECOND = float(os.getenv("HF_MAX_RATE_USD_PER_SECOND", "0.13"))
MAX_VIDEO_COST_USD = float(os.getenv("HF_MAX_VIDEO_COST_USD", "7.80"))
REFERENCE_URL = os.getenv(
    "HF_STORY_REFERENCE_URL",
    "https://raw.githubusercontent.com/Zooper1111/daily-insight/main/"
    "assets/video-scenes/true-fans-pilot/scene-01-attention.png",
)


def run(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def load_current_edition() -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(EDITIONS_PATH.read_text(encoding="utf-8"))
    editions = data.get("editions", [])
    if not editions:
        raise RuntimeError("editions.json contains no editions")
    return data, editions[0]


def save_editions(data: dict[str, Any]) -> None:
    EDITIONS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def validate_plan(edition: dict[str, Any]) -> list[dict[str, str]] | None:
    if edition.get("format") != "video":
        print("Newest edition is a static carousel; no paid video generation is due.")
        return None
    if edition.get("storyVideo"):
        print("Newest edition already has its published story video.")
        return None

    plan = edition.get("storyVideoPlan")
    blocks = (plan or {}).get("blocks")
    if not isinstance(blocks, list) or len(blocks) != BLOCK_COUNT:
        raise ValueError(f"storyVideoPlan must contain exactly {BLOCK_COUNT} blocks")
    for number, block in enumerate(blocks, start=1):
        if not isinstance(block, dict) or not block.get("prompt") or not block.get("narration"):
            raise ValueError(f"Video block {number} needs prompt and narration")
        words = re.findall(r"\b[\w’'-]+\b", block["narration"])
        if not 17 <= len(words) <= 24:
            raise ValueError(
                f"Video block {number} narration must be 17-24 words; got {len(words)}"
            )
    return blocks


def headers() -> dict[str, str]:
    key = os.getenv("HF_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "HF_KEY is missing. Add the complete copied Higgsfield API key as a "
            "GitHub Actions repository secret named HF_KEY."
        )
    return {"Authorization": f"Key {key}", "Content-Type": "application/json"}


def connection_test() -> int:
    """Validate the encrypted credential without submitting a paid generation."""
    response = requests.post(
        f"{API_BASE}/files/generate-upload-url",
        headers=headers(),
        json={"content_type": "image/png"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("upload_url") or not payload.get("public_url"):
        raise RuntimeError("Higgsfield authenticated, but the upload test response was incomplete")
    print("Higgsfield API credential verified. No generation was submitted.")
    return 0


def submit_block(index: int, prompt: str) -> dict[str, str]:
    response = requests.post(
        f"{API_BASE}/{MODEL_PATH}",
        headers=headers(),
        json={
            "prompt": prompt,
            "duration": SECONDS_PER_BLOCK,
            "image_urls": [REFERENCE_URL],
            "resolution": "2K",
            "aspect_ratio": "9:16",
            "aigc_watermark": False,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    request_id = payload.get("request_id")
    status_url = payload.get("status_url") or (
        f"{API_BASE}/requests/{request_id}/status" if request_id else None
    )
    cancel_url = payload.get("cancel_url") or (
        f"{API_BASE}/requests/{request_id}/cancel" if request_id else None
    )
    if not request_id or not status_url:
        raise RuntimeError(f"Block {index} submission did not return a request id")
    print(f"Submitted paid video block {index}/{BLOCK_COUNT}: {request_id}")
    return {"request_id": request_id, "status_url": status_url, "cancel_url": cancel_url or ""}


def find_video_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        video = payload.get("video")
        if isinstance(video, dict) and isinstance(video.get("url"), str):
            return video["url"]
        for value in payload.values():
            found = find_video_url(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = find_video_url(value)
            if found:
                return found
    return None


def wait_for_block(index: int, request: dict[str, str], timeout_seconds: int = 2400) -> str:
    deadline = time.monotonic() + timeout_seconds
    delay = 8
    while time.monotonic() < deadline:
        response = requests.get(request["status_url"], headers=headers(), timeout=60)
        response.raise_for_status()
        payload = response.json()
        status = str(payload.get("status", "")).lower()
        if status == "completed":
            url = find_video_url(payload)
            if not url:
                raise RuntimeError(f"Block {index} completed without a video URL")
            print(f"Completed video block {index}/{BLOCK_COUNT}.")
            return url
        if status in {"failed", "nsfw", "canceled"}:
            raise RuntimeError(f"Block {index} ended with status {status}; no paid retry was submitted")
        time.sleep(delay)
        delay = min(delay + 2, 20)
    if request.get("cancel_url"):
        requests.post(request["cancel_url"], headers=headers(), timeout=30)
    raise TimeoutError(f"Block {index} timed out and was canceled")


def download(url: str, destination: Path) -> None:
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def media_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def render_narration(blocks: list[dict[str, str]], work: Path) -> tuple[Path, Path]:
    pipeline = KPipeline(lang_code="a")
    voice_segments: list[Path] = []
    caption_entries: list[str] = []
    caption_number = 1

    for index, block in enumerate(blocks, start=1):
        audio_chunks = [
            audio for _, _, audio in pipeline(block["narration"], voice="af_heart", speed=0.98)
        ]
        if not audio_chunks:
            raise RuntimeError(f"Warm narration block {index} produced no audio")
        raw = work / f"voice-{index:02d}-raw.wav"
        sf.write(raw, np.concatenate(audio_chunks), 24000)
        duration = media_duration(raw)
        if duration > 9.75:
            raise RuntimeError(
                f"Narration block {index} is {duration:.2f}s; shorten its wording before spending again"
            )

        padded = work / f"voice-{index:02d}.wav"
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(raw),
                "-af",
                "apad=pad_dur=10,atrim=0:10",
                "-ac",
                "1",
                "-ar",
                "24000",
                "-y",
                str(padded),
            ]
        )
        voice_segments.append(padded)

        words = block["narration"].split()
        groups = [words[offset : offset + 5] for offset in range(0, len(words), 5)]
        speech_window = min(duration, 9.5)
        for group_index, group in enumerate(groups):
            start = (index - 1) * 10 + speech_window * group_index / len(groups)
            end = (index - 1) * 10 + speech_window * (group_index + 1) / len(groups)
            caption_entries.append(
                f"{caption_number}\n{srt_time(start)} --> {srt_time(end)}\n{' '.join(group)}\n"
            )
            caption_number += 1

    audio_list = work / "audio.txt"
    audio_list.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in voice_segments), encoding="utf-8"
    )
    narration = work / "narration.wav"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(audio_list),
            "-c",
            "copy",
            "-y",
            str(narration),
        ]
    )
    subtitles = work / "captions.srt"
    subtitles.write_text("\n".join(caption_entries), encoding="utf-8")
    return narration, subtitles


def srt_time(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    whole_seconds, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"


def assemble_video(
    clips: list[Path], narration: Path, subtitles: Path, destination: Path, work: Path
) -> None:
    normalized: list[Path] = []
    for index, clip in enumerate(clips, start=1):
        target = work / f"block-{index:02d}-normalized.mp4"
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(clip),
                "-t",
                "10",
                "-vf",
                "scale=720:1280:force_original_aspect_ratio=decrease,"
                "pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=#090b11,fps=30,format=yuv420p",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "21",
                "-y",
                str(target),
            ]
        )
        normalized.append(target)

    concat_file = work / "video.txt"
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in normalized), encoding="utf-8"
    )
    visual = work / "visual.mp4"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-y",
            str(visual),
        ]
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    subtitle_filter = (
        f"subtitles={subtitles.name}:force_style='FontName=Arial,FontSize=19,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,"
        "Outline=3,Shadow=0,Alignment=2,MarginV=118'"
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(visual),
            "-i",
            str(narration),
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "22",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            "-t",
            "60",
            "-y",
            str(destination),
        ],
        cwd=work,
    )


def main() -> int:
    if "--connection-test" in sys.argv:
        return connection_test()

    data, edition = load_current_edition()
    blocks = validate_plan(edition)
    if blocks is None:
        return 0

    projected_cost = BLOCK_COUNT * SECONDS_PER_BLOCK * MAX_RATE_USD_PER_SECOND
    if projected_cost > MAX_VIDEO_COST_USD + 1e-9:
        raise RuntimeError(
            f"Projected provider cost ${projected_cost:.2f} exceeds the per-video cap "
            f"${MAX_VIDEO_COST_USD:.2f}"
        )
    headers()  # fail before any paid request if the secret is missing
    print(
        f"Starting one 60-second video. Maximum configured provider cost: "
        f"${projected_cost:.2f}; automatic paid retries are disabled."
    )

    generation = edition["storyVideoPlan"].setdefault("generation", {})
    existing_ids = generation.get("requestIds") or []
    if len(existing_ids) == BLOCK_COUNT:
        print("Reusing six previously submitted Higgsfield requests; no new paid generation.")
        requests_by_block = [
            {
                "request_id": request_id,
                "status_url": f"{API_BASE}/requests/{request_id}/status",
                "cancel_url": f"{API_BASE}/requests/{request_id}/cancel",
            }
            for request_id in existing_ids
        ]
    else:
        requests_by_block = [
            submit_block(index, block["prompt"])
            for index, block in enumerate(blocks, start=1)
        ]
        generation.update(
            {
                "provider": "Higgsfield API",
                "maximumConfiguredCostUsd": round(projected_cost, 2),
                "paidRetries": 0,
                "requestIds": [request["request_id"] for request in requests_by_block],
                "status": "submitted",
            }
        )
        save_editions(data)

    with tempfile.TemporaryDirectory(prefix="daily-insight-higgsfield-") as temp_dir:
        work = Path(temp_dir)
        clips: list[Path] = []
        for index, request in enumerate(requests_by_block, start=1):
            url = wait_for_block(index, request)
            clip = work / f"block-{index:02d}.mp4"
            download(url, clip)
            clips.append(clip)

        generation["status"] = "visuals-completed"
        save_editions(data)

        narration, subtitles = render_narration(blocks, work)
        output = ROOT / "assets" / "videos" / edition["date"] / "story.mp4"
        assemble_video(clips, narration, subtitles, output, work)

    edition["storyVideo"] = {
        "title": edition.get("hook", edition.get("insight", {}).get("title", "Daily Insight")),
        "src": f"assets/videos/{edition['date']}/story.mp4",
        "poster": "assets/video-scenes/true-fans-pilot/scene-01-attention.png",
        "duration": "60 seconds",
        "captions": True,
    }
    generation.update(
        {
            "provider": "Higgsfield API",
            "maximumConfiguredCostUsd": round(projected_cost, 2),
            "paidRetries": 0,
            "status": "published",
        }
    )
    save_editions(data)
    print(f"Published {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
