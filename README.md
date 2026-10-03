# Daily Insight

Standalone learning digest published every other day. The website reads `editions.json`, newest first, and turns every edition into a swipeable story.

## Reading experience

- Each edition is presented as a sequence of full-screen cards: hook, idea, short contextual video example, application, and a line to steal.
- Scroll or swipe vertically to move continuously through cards and older editions.
- Story-style progress bars show where you are inside the current edition.
- Every edition should include one short 9:16 example video that establishes the scene, shows the problem, demonstrates the idea, and makes the result visible. It may be a lightweight in-browser animation or a generated clip.
- Selected editions can upgrade that example into an interactive episode with continuous vector motion, timed captions, a decision point, two outcomes, and optional sound effects.
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

- One substantial theory, model, framework, algorithm, formula, or mental model explained simply, with its evidence status made clear.
- One public-safe connection to Matt's active workstreams, using Daisy 1 as the project coordination app name.
- One short contextual video example that shows who is involved, what is going wrong, the move being taught, and the visible result.

Keep the entire edition concise: roughly 150–250 words of prose and no more than
a five-minute read. The example video is a standard part of the lesson because
watching the idea in context should do more explanatory work than another block
of prose.

Write for the card experience: keep the hook compact, the core explanation to
one or two short paragraphs, the exercise immediately scannable, and the line to
steal short enough to stand alone as a full-screen closing card.

The sequence should feel spread out rather than repetitive. Weight the mix toward
intermediate and advanced material: research-backed frameworks, algorithms,
formulas, decision science, economics, growth loops, network effects, creator
economics, game theory, systems, incentives, tradeoffs, and business philosophy.
Simple communication reminders can appear occasionally, but only when they
reveal a non-obvious mechanism or unusually useful application.

Use story-led reveals regularly. A strong sequence starts with a modern hook,
enters a vivid historical or real-world case before naming the concept, reveals
the model at the moment the pattern becomes clear, transfers it to two present-day
situations, and ends with a diagnostic question or decision rule. Verify the
anchor story; label a disputed anecdote as an anecdote rather than history.

Use a separate visual/model card only when it materially improves understanding,
such as a chart, formula, algorithm, causal diagram, or mechanism. Do not include
a “See the Model” card that merely restates the lesson as before/change/after;
the contextual video example already performs that job.

When presenting a research claim or memorable number, identify whether it is an
empirical result, formal model, theory, or heuristic. Include the source or
provenance and the important caveat. Never present a viral threshold or audience
number as a guaranteed formula.

## Interactive episode workflow

Every lesson's short video example uses one recurring character, one setting,
one visual metaphor, and one concept. Its minimum story is: context → before or
problem → model or move → after or result. A more ambitious interactive episode
can reach a decision point quickly, let the viewer choose, show the consequence,
and end with a small action.

Story-led episodes may instead use six to ten consistently styled illustrated
scenes over roughly 45–75 seconds. Gentle camera movement, a persistent hook,
warm narration, phrase-level captions, and one highlighted keyword can create a
coherent video without expensive full-motion generation. The scenes must advance
one causal story; they must not feel like a disconnected slideshow.

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
