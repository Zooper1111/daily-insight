"""Generate today's Daily Insight edition with OpenAI and prepend it to editions.json.

The script is designed for GitHub Actions:
- reads public context from context.md
- skips if today's edition already exists
- asks OpenAI for one JSON edition object
- validates the core schema before writing
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
EDITIONS_PATH = ROOT / "editions.json"
CONTEXT_PATH = ROOT / "context.md"
TODAY = dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")


REQUIRED_TOP_LEVEL = {
    "date",
    "displayDate",
    "domain",
    "hook",
    "insight",
    "lab",
    "masters",
    "steal",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_text(response: Any) -> str:
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text.strip()

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "".join(chunks).strip()


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def validate_edition(edition: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL - set(edition))
    if missing:
        raise ValueError(f"Edition missing keys: {', '.join(missing)}")
    if edition["date"] != TODAY:
        raise ValueError(f"Edition date {edition['date']} does not match {TODAY}")
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,}", str(edition["masters"]["videoId"])):
        raise ValueError("masters.videoId does not look like a YouTube ID")
    for section in ("insight", "lab", "masters", "steal"):
        if not isinstance(edition[section], dict):
            raise ValueError(f"{section} must be an object")


def build_prompt(context: str, recent: list[dict[str, Any]]) -> str:
    return f"""
Generate one new edition object for Matt's Daily Insight website, dated {TODAY}.
Return only raw JSON. No markdown fences, no prose.

Ground truth about Matt and his projects:
{context}

Recent editions to avoid repeating:
{json.dumps(recent, ensure_ascii=False, indent=2)}

Schema:
{{
  "date": "{TODAY}",
  "displayDate": "Mon · Jul 13",
  "domain": "Conversation",
  "hook": "One sharp, specific line",
  "insight": {{
    "title": "Title",
    "paras": ["2 short paragraphs, <strong>/<em> allowed"],
    "visualSvg": "<svg viewBox='0 0 560 320'>...</svg>",
    "visualCaption": "One-line caption",
    "after": ["One closing application paragraph"]
  }},
  "lab": {{
    "title": "Skill title",
    "paras": ["Why this skill matters"],
    "exercise": "Concrete under-5-minute exercise with exact words to try"
  }},
  "masters": {{
    "name": "Real person",
    "talk": "Real talk/interview/speech",
    "videoId": "Verified YouTube video ID",
    "start": 0,
    "watchWindow": "Specific portion to watch",
    "paras": ["Why this master fits today's lesson"],
    "observe": ["Three specific things to watch"]
  }},
  "steal": {{
    "line": "One punchy sentence.",
    "paras": ["How to practice it today"],
    "example": ["Example script line"]
  }}
}}

Content goals:
- Rotate domains across Innovation, AI, Strategy, Leadership, Storytelling,
  Decision-Making, Communication, and Conversation.
- Include everyday speaking skills often: small talk, better questions,
  follow-ups, warmth, transitions, graceful exits, provocative openings, and
  making ideas interesting without sounding gimmicky.
- Keep public-speaking craft in the mix, but do not make every edition about
  speeches or presentations.
- Personalize to Coordly, StoryOS, DreamGuard, the strategy agent, quarterly
  planning, or consulting only when natural. Never invent project capabilities.
- visualSvg must be original inline SVG using this palette: bg #1b1e30,
  ink #eceef7, dim #9ba0b8, gold #e8b84b, coral #ff7a6e, teal #5fd4c4,
  violet #a48bfa.
- masters.videoId must be from a real YouTube video. Do not invent IDs.
- Voice: sharp, warm coach. About a 3-minute read.
"""


def generate_edition(prompt: str) -> dict[str, Any]:
    client = OpenAI()
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        tools=[{"type": "web_search_preview"}],
    )
    return parse_json_object(extract_text(response))


def main() -> int:
    data = load_json(EDITIONS_PATH)
    editions = data.get("editions", [])
    if editions and editions[0].get("date") == TODAY:
        print(f"Edition for {TODAY} already exists.")
        return 0

    context = CONTEXT_PATH.read_text(encoding="utf-8")
    recent = [
        {
            "date": e.get("date"),
            "domain": e.get("domain"),
            "insight": e.get("insight", {}).get("title"),
            "master": e.get("masters", {}).get("name"),
        }
        for e in editions[:8]
    ]

    edition = generate_edition(build_prompt(context, recent))
    validate_edition(edition)

    data["editions"] = [edition] + editions
    data["editions"] = data["editions"][:30]
    EDITIONS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote edition {TODAY}: {edition['insight']['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
