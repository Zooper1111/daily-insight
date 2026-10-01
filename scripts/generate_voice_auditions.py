"""Generate local Kokoro voice auditions and approved episode narration.

The warm af_heart voice was approved for the first interactive episode.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "voice-auditions"
NARRATION_OUTPUT = ROOT / "assets" / "narration" / "2026-09-29"
SCRIPT = (
    "Here’s the problem with most updates: they tell people what happened, "
    "but not what changed. Let’s fix that in three beats. Before. Change. After."
)
VOICES = {
    "warm": ("af_heart", 0.98),
    "grounded": ("am_michael", 0.96),
    "british": ("bf_emma", 1.0),
}
NARRATION = {
    "intro-1": "Most work updates are accurate.",
    "intro-2": "And instantly forgettable.",
    "intro-3": "The facts are there. The movement isn't.",
    "intro-choice": "You have ten seconds. What would make this land?",
    "wrong-1": "More detail adds weight, not motion.",
    "wrong-2": "Try the move that lets people see the change.",
    "right-1": "Before: handoffs kept disappearing.",
    "right-2": "Change: put every handoff on one shared timeline.",
    "right-3": "After: blockers became visible.",
    "right-4": "Three beats. One story people can repeat.",
}


def render(pipeline: KPipeline, text: str, voice: str, speed: float) -> np.ndarray:
    chunks = [audio for _, _, audio in pipeline(text, voice=voice, speed=speed)]
    if not chunks:
        raise RuntimeError(f"No audio generated for {voice}")
    return np.concatenate(chunks)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    NARRATION_OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = KPipeline(lang_code="a")
    for label, (voice, speed) in VOICES.items():
        audio = render(pipeline, SCRIPT, voice, speed)
        path = OUTPUT / f"{label}.wav"
        sf.write(path, audio, 24000)
        print(f"{label}: {voice} -> {path}")

    for label, text in NARRATION.items():
        audio = render(pipeline, text, "af_heart", 0.98)
        path = NARRATION_OUTPUT / f"warm-{label}.wav"
        sf.write(path, audio, 24000)
        print(f"narration: af_heart -> {path}")


if __name__ == "__main__":
    main()
