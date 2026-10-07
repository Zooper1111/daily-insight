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
EDITION_DATE_OVERRIDE = os.getenv("EDITION_DATE", "").strip()
TODAY = EDITION_DATE_OVERRIDE or dt.datetime.now(
    ZoneInfo("America/New_York")
).date().isoformat()
try:
    dt.date.fromisoformat(TODAY)
except ValueError as exc:
    raise ValueError("EDITION_DATE must use YYYY-MM-DD format") from exc
WRITER_MODEL = os.getenv("OPENAI_WRITER_MODEL", "gpt-6-luna")
WRITER_REASONING_EFFORT = os.getenv("OPENAI_WRITER_REASONING_EFFORT", "medium")
REVIEW_MODEL = os.getenv("OPENAI_REVIEW_MODEL", "gpt-6.1-sol")
REVIEW_REASONING_EFFORT = os.getenv("OPENAI_REVIEW_REASONING_EFFORT", "high")
REFINER_MODEL = os.getenv("OPENAI_REFINER_MODEL", "gpt-6-astra")
REFINER_REASONING_EFFORT = os.getenv("OPENAI_REFINER_REASONING_EFFORT", "high")
WRITER_MAX_OUTPUT_TOKENS = int(
    os.getenv("OPENAI_WRITER_MAX_OUTPUT_TOKENS", "20000")
)
REVIEW_MAX_OUTPUT_TOKENS = int(
    os.getenv("OPENAI_REVIEW_MAX_OUTPUT_TOKENS", "12000")
)
REFINER_MAX_OUTPUT_TOKENS = int(
    os.getenv("OPENAI_REFINER_MAX_OUTPUT_TOKENS", "24000")
)
SMOKE_TEST = os.getenv("SMOKE_TEST") == "1"
EDITION_INTERVAL_DAYS = int(os.getenv("EDITION_INTERVAL_DAYS", "2"))
EDITION_ANCHOR_DATE = os.getenv("EDITION_ANCHOR_DATE", "2026-07-27")
VIDEO_PILOT_START = dt.date.fromisoformat(os.getenv("VIDEO_PILOT_START", "2026-10-03"))
VIDEO_PILOT_END = dt.date.fromisoformat(os.getenv("VIDEO_PILOT_END", "2026-10-17"))
VIDEO_PILOT_ENABLED = os.getenv("VIDEO_PILOT_ENABLED", "0") == "1"
VIDEO_STORY_MIN_SCORE = 4
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "1800"))


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

    edition_format = edition.get("format")
    expected_format = format_for_date(dt.date.fromisoformat(TODAY))
    if edition_format != expected_format:
        raise ValueError(
            f"Edition format must be {expected_format!r} for {TODAY}; got {edition_format!r}"
        )
    if edition_format == "video":
        plan = edition.get("storyVideoPlan")
        blocks = (plan or {}).get("blocks")
        if not isinstance(blocks, list) or len(blocks) != 6:
            raise ValueError("Video editions require exactly six storyVideoPlan blocks")
        for index, block in enumerate(blocks, start=1):
            if not isinstance(block, dict) or not block.get("prompt") or not block.get("narration"):
                raise ValueError(f"storyVideoPlan block {index} needs prompt and narration")
        if not str((plan or {}).get("narration", "")).strip():
            raise ValueError("Video editions require one continuous narration")
    elif edition.get("storyVideoPlan") is not None:
        raise ValueError("Carousel editions must not contain storyVideoPlan")

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


def format_for_date(day: dt.date) -> str:
    """Alternate full video and static carousel editions during the pilot."""
    if not VIDEO_PILOT_ENABLED or day < VIDEO_PILOT_START or day > VIDEO_PILOT_END:
        return "carousel"
    publication_number = (day - VIDEO_PILOT_START).days // EDITION_INTERVAL_DAYS
    return "video" if publication_number % 2 == 0 else "carousel"


def build_prompt(context: str, recent: list[dict[str, Any]]) -> str:
    edition_format = format_for_date(dt.date.fromisoformat(TODAY))
    if edition_format == "video":
        format_schema = '''
  "format": "video",
  "storyVideoPlan": {
    "style": "Warm editorial storybook animation with hand-painted gouache texture, bold cobalt, amber, coral and teal shapes, one recurring adult protagonist, no photorealism, no logos, no spoken characters",
    "narration": "One complete roughly 160-180 word continuous narration in plain spoken English",
    "blocks": [
      {
        "narration": "One concise spoken summary for the matching ten-second scene",
        "prompt": "One detailed ten-second vertical animation prompt containing exactly five hard-cut shots of about two seconds each. Vary shot size and angle, demand motion from frame one, preserve the recurring protagonist and editorial storybook style, and say characters gesture but never talk."
      }
    ]
  },'''
        format_direction = '''
This is a FULL VIDEO edition in the two-week pilot. Add exactly six ordered
storyVideoPlan blocks, producing sixty seconds total. The six blocks must form
one causal story: provocative hook, concrete friction, named-model reveal,
formula or mechanism, important caveat, and a final application to one public-
safe active project. Each block narration is one concise line. Each visual prompt must
describe exactly five hard-cut shots, about two seconds each, with motion from
the first frame. Keep the same recurring adult protagonist and one coherent
warm editorial storybook world. Characters only gesture and never speak; the
external narrator carries the lesson. Do not ask the video model to draw text.

Before choosing the topic, apply a strict story-fit gate inspired by the Cobra
Effect: a protagonist wants something concrete, someone changes a rule or takes
an action, behavior changes because of it, a surprising consequence appears,
and the ending makes the mechanism visually obvious. Silently reject a candidate
that lacks that causal turn and choose a stronger topic. Do not force an abstract
definition or calculator lesson into animation. If math appears, first explain
what the numbers mean, then use one worked example at roughly a third-grade
listening level. Never change a second variable in the same 60-second story.

Treat the Cobra Effect as the creative quality bar, not just a checklist. Every
ten-second block must change the situation. Reveal a visible reversal by roughly
the middle, then make the final scene resolve the opening problem. If the same
lesson would work equally well as narrated prose over unrelated attractive
motion, reject it and choose a more cinematic mechanism. Let the viewer see the
cause, surprise, or consequence before the narrator names it.

Write storyVideoPlan.narration as one continuous roughly 160-180 word read. It must tell
the entire story in order and end with the project application. The six shorter
block narration fields are timing summaries for the matching visuals; they do
not replace the continuous narration.
'''
    else:
        format_schema = '  "format": "carousel",'
        format_direction = '''
This is a STATIC CAROUSEL edition in the two-week pilot. Do not include
storyVideoPlan, narration, or animation instructions. Let the hook, analytical
visual, application, exercise, and closing line carry the lesson as swipeable
cards.
'''
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
{format_schema}
  "insight": {{
    "title": "Title",
    "paras": ["One short paragraph, <strong>/<em> allowed. Teach one substantial theory, model, framework, algorithm, formula, or mental model here, with its evidence status or provenance."],
    "visualSvg": "<svg viewBox='0 0 560 320'>...</svg>",
    "visualCaption": "One-line caption",
    "after": ["Modern transfer example one", "Modern transfer example two ending with a practical diagnostic question"]
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
{format_direction}
- Use a deliberately spread-out mix. Across any eight editions, aim for:
  1-2 small talk or everyday conversation lessons; 1-2 presentation or public
  speaking lessons; 1-2 business frameworks, strategy, product, or management
  lessons; 1-2 algorithmic, decision-science, philosophy-of-business, game
  theory, systems, or rule-based models; and occasional AI or innovation
  lessons when they are genuinely useful.
- Rotate domains across Conversation, Communication, Storytelling, Strategy,
  Decision-Making, Leadership, Innovation, AI, and Product Thinking.
- Every edition must teach one substantial theory, model, framework, algorithm,
  formula, or named concept from psychology, systems thinking, rhetoric,
  design, management, decision science, economics, creator economics,
  innovation, AI, or product strategy. Favor intermediate or advanced ideas
  that provide a genuinely new lens, calculation, mechanism, or decision rule.
  Obvious reminders are not strong enough on their own.
- For a memorable claim or number, identify whether it is an empirical result,
  formal model, theory, or heuristic. Include its source or provenance and its
  important caveat. Never present an audience size or viral threshold as a
  guaranteed formula.
- Regularly use a story-led reveal. Start with a sharp present-day hook, enter a
  vivid historical or real-world case before naming the concept, reveal the named
  model only after the pattern is visible, transfer it to two modern situations,
  and end with a practical diagnostic question or decision rule. Use insight.paras
  for the case and model reveal, then insight.after for the modern transfer.
- Source-check the anchor case with web search. If a memorable historical story is
  disputed, apocryphal, or merely illustrative, label it honestly in the prose or
  choose a documented case. Never present an uncertain anecdote as established fact.
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
- Include a short, video-ready applied story or scenario. Establish who is
  involved, what they are trying to do, and what specifically is going wrong;
  then show the model or move and the visible result. Put this compact contextual
  arc in insight.after so it can become the edition's video example.
- Favor mechanisms with a reveal and consequence—perverse incentives, Goodhart's
  Law, principal-agent problems, paradoxes, feedback loops, cognitive biases,
  power laws, option value, and other ideas that become visible through a story.
- Keep the full edition to roughly 150-250 words of prose across insight, lab,
  masters (when present), and steal. It must be easy to read and understand in
  no more than five minutes. Do not repeat the same idea across sections.
- The website presents each section as a full-screen swipeable card. Keep the
  hook to roughly 5-12 words. Keep insight.paras to one or two short paragraphs,
  lab.paras to one brief sentence, lab.exercise to a compact set of directions,
  and steal.line short enough to work as a large standalone headline.
- Keep paragraphs short. Prefer one insight paragraph, one application sentence,
  one compact exercise, and one reusable line with one brief example.
- Set masters to null for most editions. Include a masters object only when
  watching or hearing the person demonstrate the idea materially improves
  understanding. A famous speaker alone is not a reason to add a video. When
  present, use exactly these fields: name, talk, videoId, start, watchWindow,
  paras (one short reason to watch), and observe (one specific thing to notice).
- visualSvg must do analytical work: show a useful chart, formula, algorithm,
  causal diagram, or mechanism. Never make a generic before/change/after graphic
  that merely repeats the prose. Use original inline SVG with this palette: bg
  #1b1e30, ink #eceef7, dim #9ba0b8, gold #e8b84b, coral #ff7a6e, teal #5fd4c4,
  violet #a48bfa.
- When masters is present, masters.videoId must be from a real YouTube video. Do
  not invent IDs.
- Voice: sharp, warm coach. Concise enough to grasp in one sitting.
"""


def generate_edition(
    prompt: str,
    *,
    model: str = WRITER_MODEL,
    reasoning_effort: str = WRITER_REASONING_EFFORT,
    max_output_tokens: int = WRITER_MAX_OUTPUT_TOKENS,
) -> dict[str, Any]:
    client = OpenAI(timeout=OPENAI_TIMEOUT_SECONDS, max_retries=0)
    print(f"Generating edition with {model} ({reasoning_effort} reasoning).")
    response = client.responses.create(
        model=model,
        input=prompt,
        reasoning={"effort": reasoning_effort},
        tools=[{"type": "web_search_preview"}],
        max_output_tokens=max_output_tokens,
    )
    return parse_json_object(extract_text(response))


def refine_edition(
    original_prompt: str,
    candidate: dict[str, Any],
    feedback: dict[str, Any] | str,
) -> dict[str, Any]:
    """Use Astra once to repair a complete cheap draft, never to start over."""
    refinement_prompt = f"""
You are refining an existing Daily Insight edition, not inventing a new lesson.
Preserve its central story, named model, factual sources, characters, visual
world, project application, and strongest lines. Make only the changes needed
to fix the supplied feedback and satisfy the original requirements. Return only
the complete corrected edition as raw JSON.

Original requirements:
{original_prompt}

Existing draft:
{json.dumps(candidate, ensure_ascii=False, indent=2)}

Specific feedback to fix:
{json.dumps(feedback, ensure_ascii=False, indent=2) if isinstance(feedback, dict) else feedback}
"""
    return generate_edition(
        refinement_prompt,
        model=REFINER_MODEL,
        reasoning_effort=REFINER_REASONING_EFFORT,
        max_output_tokens=REFINER_MAX_OUTPUT_TOKENS,
    )


def review_video_story(edition: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Fail closed unless a second model pass clears the paid-video story bar."""
    client = OpenAI(timeout=OPENAI_TIMEOUT_SECONDS, max_retries=0)
    print(
        f"Reviewing paid-video story with {REVIEW_MODEL} "
        f"({REVIEW_REASONING_EFFORT} reasoning)."
    )
    response = client.responses.create(
        model=REVIEW_MODEL,
        input=f"""
Act as the final story editor for a paid 60-second animated lesson. Judge the
candidate against the Cobra Effect standard. Return only raw JSON with exactly
this shape:
{{
  "approved": true,
  "scores": {{
    "causalStory": 1,
    "visibleReversal": 1,
    "visualCausality": 1,
    "endingPayoff": 1,
    "spokenClarity": 1
  }},
  "problems": ["short, specific problem"],
  "revisionBrief": "precise instructions for one rewrite"
}}

Approve only if every score is at least {VIDEO_STORY_MIN_SCORE} out of 5. The
animation must reveal a changing situation, not merely decorate explanatory
prose. A visible reversal should occur by the middle. The ending must resolve
the opening problem. The narration must be understandable on one listen without
pausing, and any math must be explained at roughly a third-grade listening
level. Be demanding: protecting the paid generation budget matters more than
publishing on schedule.

Candidate edition:
{json.dumps(edition, ensure_ascii=False, indent=2)}
""",
        reasoning={"effort": REVIEW_REASONING_EFFORT},
        max_output_tokens=REVIEW_MAX_OUTPUT_TOKENS,
    )
    review = parse_json_object(extract_text(response))
    score_names = {
        "causalStory",
        "visibleReversal",
        "visualCausality",
        "endingPayoff",
        "spokenClarity",
    }
    scores = review.get("scores")
    if not isinstance(scores, dict) or set(scores) != score_names:
        raise ValueError("Video story review returned an invalid scorecard")
    if any(
        not isinstance(scores[name], int) or not 1 <= scores[name] <= 5
        for name in score_names
    ):
        raise ValueError("Video story review scores must be integers from 1 to 5")
    approved = bool(review.get("approved")) and all(
        scores[name] >= VIDEO_STORY_MIN_SCORE for name in score_names
    )
    return approved, review


def smoke_test() -> int:
    client = OpenAI(timeout=OPENAI_TIMEOUT_SECONDS, max_retries=0)
    response = client.responses.create(
        model=WRITER_MODEL,
        input="Reply with exactly: daily-insight-ok",
        reasoning={"effort": "low"},
        max_output_tokens=256,
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

    prompt = build_prompt(context, recent)
    writer_model = WRITER_MODEL
    used_refiner = False
    edition = generate_edition(prompt)
    try:
        validate_edition(edition)
    except ValueError as exc:
        print(f"Cheap draft failed local validation: {exc}")
        edition = refine_edition(prompt, edition, f"Local validation: {exc}")
        writer_model = REFINER_MODEL
        used_refiner = True
        validate_edition(edition)

    if edition.get("format") == "video":
        approved, review = review_video_story(edition)
        if not approved and not used_refiner:
            edition = refine_edition(prompt, edition, review)
            writer_model = REFINER_MODEL
            used_refiner = True
            validate_edition(edition)
            approved, review = review_video_story(edition)
        if not approved:
            raise RuntimeError(
                "Video story failed the Cobra-standard review after its one "
                "Astra refinement; "
                "no edition was published and no paid video request was made."
            )
        edition["storyVideoPlan"]["qualityGate"] = {
            "approved": True,
            "writerModel": writer_model,
            "reviewModel": REVIEW_MODEL,
            "usedRefiner": used_refiner,
            "scores": review["scores"],
        }

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
