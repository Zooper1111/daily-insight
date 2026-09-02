"""Generate today's Daily Insight edition with OpenAI and prepend it to editions.json.

The script is designed for GitHub Actions:
- reads public context from context.md
- skips if today's edition already exists or today is an off day
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
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")
SMOKE_TEST = os.getenv("SMOKE_TEST") == "1"
EDITION_INTERVAL_DAYS = int(os.getenv("EDITION_INTERVAL_DAYS", "2"))
EDITION_ANCHOR_DATE = os.getenv("EDITION_ANCHOR_DATE", "2026-07-27")


REQUIRED_TOP_LEVEL = {
    "date",
    "displayDate",
    "domain",
    "hook",
    "insight",
    "lab",
    "steal",
}

PROHIBITED_TEXT_PATTERNS = [
    (re.compile(r"\bCoordly\b", re.IGNORECASE), "Use Daisy 1, not Coordly."),
    (re.compile(r"\bDaisy One\b", re.IGNORECASE), "Use Daisy 1, not Daisy One."),
    (
        re.compile(r"\bMatt\s+(?:should|could|can|needs?|gets|has|is|wants|prefers|likes)\b"),
        'Address the reader as "you" instead of giving third-person advice about Matt.',
    ),
    (
        re.compile(r"\b(?:For|When|If)\s+Matt\b"),
        'Address the reader as "you" instead of giving third-person advice about Matt.',
    ),
    (
        re.compile(r"\bMatt[’']s\s+(?:work|project|strategy|planning|practice|next)\b"),
        'Address the reader as "you" instead of giving third-person advice about Matt.',
    ),
]

TEXT_REPLACEMENTS = [
    ("Coordly", "Daisy 1"),
    ("Daisy One", "Daisy 1"),
    ("Matt could", "you can"),
    ("Matt can", "you can"),
    ("Matt should", "you should"),
    ("For Matt’s", "For your"),
    ("For Matt's", "For your"),
    ("For Matt,", "For you,"),
    ("when Matt is", "when you are"),
    ("When Matt is", "When you are"),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_existing_text(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        updated = value
        for old, new in TEXT_REPLACEMENTS:
            updated = updated.replace(old, new)
        return updated, updated != value

    if isinstance(value, list):
        changed = False
        items = []
        for item in value:
            updated, item_changed = sanitize_existing_text(item)
            items.append(updated)
            changed = changed or item_changed
        return items, changed

    if isinstance(value, dict):
        changed = False
        items = {}
        for key, item in value.items():
            if key == "name" and value.get("talk", "").startswith("Writing Advice @ NYU"):
                items[key] = item
                continue
            updated, item_changed = sanitize_existing_text(item)
            items[key] = updated
            changed = changed or item_changed
        return items, changed

    return value, False


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
    for section in ("insight", "lab", "steal"):
        if not isinstance(edition[section], dict):
            raise ValueError(f"{section} must be an object")

    masters = edition.get("masters")
    if masters is not None:
        if not isinstance(masters, dict):
            raise ValueError("masters must be an object or null")
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,}", str(masters.get("videoId", ""))):
            raise ValueError("masters.videoId does not look like a YouTube ID")

    for path, text in iter_strings(edition):
        if path == ("masters", "name"):
            continue
        for pattern, message in PROHIBITED_TEXT_PATTERNS:
            if pattern.search(text):
                raise ValueError(f"{message} Found in {'.'.join(path)}: {text[:120]!r}")


def iter_strings(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
    strings: list[tuple[tuple[str, ...], str]] = []
    if isinstance(value, str):
        strings.append((path, value))
    elif isinstance(value, dict):
        for key, item in value.items():
            strings.extend(iter_strings(item, (*path, str(key))))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            strings.extend(iter_strings(item, (*path, str(index))))
    return strings


def should_publish_today() -> bool:
    if EDITION_INTERVAL_DAYS <= 1:
        return True

    today = dt.date.fromisoformat(TODAY)
    anchor = dt.date.fromisoformat(EDITION_ANCHOR_DATE)
    return (today - anchor).days % EDITION_INTERVAL_DAYS == 0


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
    "paras": ["One short paragraph, <strong>/<em> allowed. Teach one theory, model, framework, or mental model here."],
    "visualSvg": "<svg viewBox='0 0 560 320'>...</svg>",
    "visualCaption": "One-line caption",
    "after": ["One closing application sentence tied to a public-safe workstream example"]
  }},
  "lab": {{
    "title": "Skill title",
    "paras": ["One short sentence on why this skill matters"],
    "exercise": "One compact under-5-minute exercise with exact words to try"
  }},
  "masters": null,
  "steal": {{
    "line": "One punchy sentence.",
    "paras": ["How to practice it today"],
    "example": ["Example script line that could fit a planning session, product discussion, client conversation, demo, or strategy memo"]
  }}
}}

Content goals:
- Use a deliberately spread-out mix. Across any eight editions, aim for:
  1-2 small talk or everyday conversation lessons; 1-2 presentation or public
  speaking lessons; 1-2 business frameworks, strategy, product, or management
  lessons; 1-2 algorithmic, decision-science, philosophy-of-business, game
  theory, systems, or rule-based models; and occasional AI or innovation
  lessons when they are genuinely useful.
- Rotate domains across Conversation, Communication, Storytelling, Strategy,
  Decision-Making, Leadership, Innovation, AI, and Product Thinking.
- Every edition must teach one real theory, model, framework, mental model, or
  named concept from psychology, systems thinking, rhetoric, design,
  management, decision science, innovation, AI, or product strategy. Make the
  concept practical, not academic.
- Include everyday speaking skills often: small talk, better questions,
  follow-ups, warmth, transitions, graceful exits, provocative openings, and
  making ideas interesting without sounding gimmicky.
- Keep public-speaking and presentation craft in the mix, including framing,
  slide/setup structure, sharper delivery, and explaining current work clearly.
- Do not make every edition primarily about "how to talk." Some should be about
  thinking better, seeing systems, making decisions, shaping products, using AI,
  planning work, business philosophy, or framing strategy.
- Include small talk sometimes, but do not bunch it together. Include business
  and algorithmic/framework editions regularly so the sequence has range.
- Most editions should include a public-safe example tied to Daisy 1, StoryOS,
  DreamGuard, the strategy agent, quarterly planning, or consulting. Use simple
  scenes such as a planning session, product decision, client explanation, demo,
  workshop, or strategy memo. Never invent project capabilities or private
  details.
- Refer to the project coordination app as Daisy 1. Never call it Coordly or
  Daisy One.
- Address the reader directly as "you." Do not write "Matt should," "Matt
  could," "Matt can," "For Matt," or similar third-person coaching language in
  the generated edition. It is okay for the private context to mention Matt, but
  the public edition should read like direct advice to the reader.
- Include a short applied story, scenario, or example. Show how the idea plays
  out instead of only explaining what to say.
- Keep the full edition to roughly 150-250 words of prose across insight, lab,
  masters (when present), and steal. It must be easy to read and understand in
  no more than five minutes. Do not repeat the same idea across sections.
- Keep paragraphs short. Prefer one insight paragraph, one application sentence,
  one compact exercise, and one reusable line with one brief example.
- Set masters to null for most editions. Include a masters object only when
  watching or hearing the person demonstrate the idea materially improves
  understanding. A famous speaker alone is not a reason to add a video. When
  present, use exactly these fields: name, talk, videoId, start, watchWindow,
  paras (one short reason to watch), and observe (one specific thing to notice).
- visualSvg must be original inline SVG using this palette: bg #1b1e30,
  ink #eceef7, dim #9ba0b8, gold #e8b84b, coral #ff7a6e, teal #5fd4c4,
  violet #a48bfa.
- When masters is present, masters.videoId must be from a real YouTube video. Do
  not invent IDs.
- Voice: sharp, warm coach. Concise enough to grasp in one sitting.
"""


def generate_edition(prompt: str) -> dict[str, Any]:
    client = OpenAI()
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        tools=[{"type": "web_search_preview"}],
    )
    return parse_json_object(extract_text(response))


def smoke_test() -> int:
    client = OpenAI()
    response = client.responses.create(
        model=MODEL,
        input="Reply with exactly: daily-insight-ok",
    )
    text = extract_text(response)
    if text.strip() != "daily-insight-ok":
        raise ValueError(f"Unexpected smoke test response: {text!r}")
    print("OpenAI smoke test passed.")
    return 0


def main() -> int:
    if SMOKE_TEST:
        return smoke_test()

    data = load_json(EDITIONS_PATH)
    data, sanitized = sanitize_existing_text(data)

    if not should_publish_today():
        if sanitized:
            EDITIONS_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print("Sanitized existing editions.")
            return 0
        print(
            f"Skipping {TODAY}: every {EDITION_INTERVAL_DAYS} days from "
            f"{EDITION_ANCHOR_DATE}."
        )
        return 0

    editions = data.get("editions", [])
    if editions and editions[0].get("date") == TODAY:
        if sanitized:
            EDITIONS_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print("Sanitized existing editions.")
            return 0
        print(f"Edition for {TODAY} already exists.")
        return 0

    context = CONTEXT_PATH.read_text(encoding="utf-8")
    recent = [
        {
            "date": e.get("date"),
            "domain": e.get("domain"),
            "insight": e.get("insight", {}).get("title"),
            "master": (e.get("masters") or {}).get("name"),
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
