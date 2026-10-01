"""Render a captioned vertical Daily Insight video from still scenes and audio.

The renderer keeps the source format simple: a JSON spec, portrait images, and
one narration track. It adds subtle motion, timed captions, a progress line,
and web-friendly MP4 encoding through ffmpeg.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def ass_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def write_subtitles(spec: dict[str, Any], path: Path, width: int, height: int) -> None:
    duration = float(spec["duration"])
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial Rounded MT Bold,58,&H00111820,&H00111820,&H00F7F5EF,&H00F7F5EF,-1,0,0,0,100,100,0,0,3,24,0,2,120,120,270,1
Style: Brand,Avenir Next,27,&H0049BDF2,&H0049BDF2,&H72090B11,&H72090B11,-1,0,0,0,100,100,2,0,1,3,0,8,80,80,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{ass_time(0)},{ass_time(duration)},Brand,,0,0,0,,DAILY · INSIGHT
"""
    lines = [header]
    for caption in spec["captions"]:
        lines.append(
            "Dialogue: 1,"
            f"{ass_time(float(caption['start']))},"
            f"{ass_time(float(caption['end']))},"
            "Caption,,0,0,0,,"
            f"{ass_text(str(caption['text']))}\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def resolve_scene(scene: dict[str, Any], root: Path) -> Path:
    path = Path(scene["path"])
    return path if path.is_absolute() else (root / path).resolve()


def build_filter(
    scene_count: int,
    durations: list[float],
    subtitle_path: Path,
    width: int,
    height: int,
    fps: int,
    total_duration: float,
) -> str:
    filters: list[str] = []
    for index in range(scene_count):
        frames = max(1, round(durations[index] * fps))
        drift = 0.035 / frames
        if index % 2:
            x_expr = "iw/zoom-iw/zoom*0.47"
            y_expr = "ih/zoom-ih/zoom*0.52"
        else:
            x_expr = "iw/zoom-iw/zoom*0.52"
            y_expr = "ih/zoom-ih/zoom*0.48"
        filters.append(
            f"[{index}:v]"
            f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
            f"crop={width * 2}:{height * 2},"
            f"zoompan=z='min(zoom+{drift:.8f},1.035)':"
            f"x='{x_expr}':y='{y_expr}':d=1:s={width}x{height}:fps={fps},"
            "setsar=1,format=yuv420p"
            f"[v{index}]"
        )
    concat_inputs = "".join(f"[v{index}]" for index in range(scene_count))
    safe_subtitle = str(subtitle_path).replace("'", r"\'").replace(":", r"\:")
    filters.append(
        f"{concat_inputs}concat=n={scene_count}:v=1:a=0,"
        f"subtitles=filename='{safe_subtitle}':fontsdir='/System/Library/Fonts/Supplemental',"
        "drawbox=x=70:y=132:w=iw-140:h=8:color=0x111820@0.45:t=fill,"
        f"drawbox=x=70:y=132:w='(iw-140)*min(t/{total_duration:.3f},1)':"
        "h=8:color=0xf2bd49@0.95:t=fill"
        "[video]"
    )
    return ";".join(filters)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    scenes = spec["scenes"]
    durations = [float(scene["duration"]) for scene in scenes]
    total_duration = sum(durations)
    declared_duration = float(spec["duration"])
    if abs(total_duration - declared_duration) > 0.05:
        raise ValueError("Scene durations must add up to spec.duration")

    project_root = Path.cwd()
    scene_paths = [resolve_scene(scene, project_root) for scene in scenes]
    for path in [*scene_paths, args.audio, args.ffmpeg]:
        if not path.exists():
            raise FileNotFoundError(path)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="daily-insight-video-") as temp_dir:
        subtitle_path = Path(temp_dir) / "captions.ass"
        write_subtitles(spec, subtitle_path, args.width, args.height)
        command = [str(args.ffmpeg), "-y", "-hide_banner", "-loglevel", "warning"]
        for path, duration in zip(scene_paths, durations):
            command.extend(
                ["-loop", "1", "-framerate", str(args.fps), "-t", str(duration), "-i", str(path)]
            )
        command.extend(["-i", str(args.audio)])
        command.extend(
            [
                "-filter_complex",
                build_filter(
                    len(scenes),
                    durations,
                    subtitle_path,
                    args.width,
                    args.height,
                    args.fps,
                    total_duration,
                ),
                "-map",
                "[video]",
                "-map",
                f"{len(scenes)}:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-t",
                str(total_duration),
                "-movflags",
                "+faststart",
                str(args.output),
            ]
        )
        subprocess.run(command, check=True)

    print(f"Rendered {args.output} ({total_duration:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
