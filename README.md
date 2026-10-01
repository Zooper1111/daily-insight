# Daily Insight

Standalone learning digest published every other day. The website reads `editions.json`, newest first, and turns every edition into a swipeable story.

## Reading experience

- Each edition is presented as a sequence of full-screen cards: hook, optional interactive episode, idea, visual, practice, optional reference video, and a line to steal.
- Scroll or swipe vertically to move continuously through cards and older editions.
- Story-style progress bars show where you are inside the current edition.
- Selected editions can include an original 9:16 interactive episode with continuous vector motion, timed captions, a decision point, two outcomes, and optional sound effects.
- The edition library jumps directly to any saved insight, and reusable lines can be copied with one tap.
- Arrow keys, Page Up/Page Down, Space, J, and K provide desktop navigation.

## How it works

- `index.html` — the app shell.
- `editions.json` — all editions, newest first.
- `context.md` — public-safe memory for Matt, his projects, content preferences, and corrections.
- `scripts/generate_edition.py` — OpenAI-powered edition generator.
- `.github/workflows/daily-edition.yml` — GitHub Actions workflow that checks automatically.

## Automated publishing

The GitHub Action checks every morning and can also be run manually from the Actions tab. The generator publishes every other day from the configured anchor date.

Setup required:

1. Create an OpenAI API key.
2. In GitHub, add it as a repository Actions secret named `OPENAI_API_KEY`.
3. Optional: set repository variable `OPENAI_MODEL` to change the model without editing code.
4. Optional: set `EDITION_INTERVAL_DAYS` or `EDITION_ANCHOR_DATE` to adjust cadence.

The workflow:

1. Checks out the repo.
2. Installs the OpenAI Python SDK.
3. Runs `scripts/generate_edition.py`.
4. Commits `editions.json` only if a new edition was generated.

The script skips if today is an off day or today's edition already exists, so a manual run will not double-publish.

## Edition schema notes

- `insight.visualSvg`: inline SVG string, single-quoted attributes, viewBox ~560 wide, dark theme colors (bg #1b1e30, ink #eceef7, dim #9ba0b8, gold #e8b84b, coral #ff7a6e, teal #5fd4c4, violet #a48bfa).
- When a rare `masters` section is present, `masters.videoId` must be a real
  YouTube video ID found via web search—never invented—and `masters.start` is
  the seconds offset for the embed when a specific moment is known.
- Paragraph arrays may contain simple inline HTML (`<strong>`, `<em>`).

## Content direction

Daily Insight should teach public speaking, everyday conversation, small talk, better questions, provocative openings, storytelling, strategy, decision-making, AI, product thinking, business frameworks, and useful theories or models. Keep it personal, practical, and immediately usable.

Each edition should usually include:

- One theory, model, framework, or mental model explained simply.
- One public-safe connection to Matt's active workstreams, using Daisy 1 as the project coordination app name.
- One short applied story, scene, or example that shows how the idea could be used.

Keep the entire edition concise: roughly 150–250 words of prose and no more than
a five-minute read. A video section is optional and should be uncommon; add it
only when watching the idea demonstrated materially improves understanding.

Write for the card experience: keep the hook compact, the core explanation to
one or two short paragraphs, the exercise immediately scannable, and the line to
steal short enough to stand alone as a full-screen closing card.

The sequence should feel spread out rather than repetitive. A healthy run mixes small talk techniques, presentation craft, business frameworks, and algorithmic or decision-science ideas such as game theory, rules, systems, incentives, tradeoffs, and business philosophy.

## Interactive episode workflow

Interactive episodes are continuous motion pieces built directly into the web
experience. Each episode uses one recurring character, one setting, one visual
metaphor, and one concept. It should reach a decision point quickly, let the
viewer choose, show the consequence, and end with a small action.

Every example must establish the scene before introducing the model: who the
people are, what they are trying to do, and what specifically is going wrong.
Labels such as “handoff,” “blocker,” or “timeline” should never appear without
enough plain-language context for a first-time viewer to follow the situation.

The first pilot is the Micro Before/After episode in `index.html`. Its free,
dependency-free stack is inline SVG, CSS animation, a small JavaScript state
machine, timed captions, and optional synthesized sound effects. The web version
can branch; a later export workflow will render the strongest path as a linear
9:16 MP4 for social platforms.

Do not use operating-system speech synthesis in published episodes. The approved
default is the warm local Kokoro voice (`af_heart` at `0.98` speed). Narration is
opt-in, restarts the episode so audio and captions remain synchronized, and
never replaces the captions. Run `scripts/generate_voice_auditions.py` to
rebuild both the auditions in `assets/voice-auditions/` and the approved episode
clips in `assets/narration/2026-09-29/`. A paid voice service remains an optional
upgrade rather than a dependency.

The earlier image-based MP4 renderer remains in `scripts/render_short_video.py`
as an archive and export reference, but slideshow-style motion is not the target
format going forward.
