"""Generate short local Kokoro voice auditions for Daily Insight.

This script is intentionally separate from the site. A voice is not published
until it has been heard and approved.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "voice-auditions"
SCRIPT = (
    "Here’s the problem with most updates: they tell people what happened, "
    "but not what changed. Let’s fix that in three beats. Before. Change. After."
)
VOICES = {
    "warm": ("af_heart", 0.98),
    "grounded": ("am_michael", 0.96),
    "british": ("bf_emma", 1.0),
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = KPipeline(lang_code="a")
    for label, (voice, speed) in VOICES.items():
        chunks = [audio for _, _, audio in pipeline(SCRIPT, voice=voice, speed=speed)]
        if not chunks:
            raise RuntimeError(f"No audio generated for {voice}")
        audio = np.concatenate(chunks)
        path = OUTPUT / f"{label}.wav"
        sf.write(path, audio, 24000)
        print(f"{label}: {voice} -> {path}")


if __name__ == "__main__":
    main()
