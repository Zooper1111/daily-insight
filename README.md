# Daily Insight

Standalone learning digest published every other day. The website reads `editions.json`, newest first, and turns every edition into a swipeable story.

## Reading experience

- Each edition is presented as a sequence of full-screen cards. During the
  October 2026 pilot, editions alternate between a complete 60-second narrated
  story video and a static carousel lesson.
- Scroll or swipe vertically to move continuously through cards and older editions.
- Story-style progress bars show where you are inside the current edition.
- Full-video editions use one coherent 9:16 animated story: hook, concrete
  friction, named-model reveal, mechanism or formula, caveat, and application.
- Carousel editions use designed words, images, and analytical visuals without
  requiring animation or narration.
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

The GitHub Action checks every morning and can also be run manually from the
Actions tab. The generator publishes every other day from the configured anchor
date. A manual run may supply `edition_date` in `YYYY-MM-DD` format to generate
an upcoming scheduled edition early; the normal run for that date then detects
the existing edition and skips it.

Setup required:

1. Create an OpenAI API key.
2. In GitHub, add it as a repository Actions secret named `OPENAI_API_KEY`.
3. For full-video editions, fund the pay-as-you-go Higgsfield API account and add
   the complete copied credential as a repository Actions secret named `HF_KEY`.
   Keep auto top-up off during the pilot.
4. Optional: set `OPENAI_WRITER_MODEL`, `OPENAI_REVIEW_MODEL`, or
   `OPENAI_REFINER_MODEL` repository variables to change the model roles without
   editing code.
5. Optional: set `EDITION_INTERVAL_DAYS` or `EDITION_ANCHOR_DATE` to adjust cadence.

The workflow:

1. Checks out the repo.
2. Installs the OpenAI Python SDK.
3. Runs `scripts/generate_edition.py`.
4. On alternating pilot editions, generates six ten-second animated sections,
   adds the approved warm local narration and captions, and assembles one
   60-second mobile video.
5. Commits `editions.json` and any completed video asset.

The cost-controlled default uses `gpt-6-luna` at medium reasoning for the first
draft and `gpt-6.1-sol` at high reasoning for the independent paid-video review.
If the complete cheap draft fails either local schema checks or the story review,
`gpt-6-astra` receives that draft plus the exact feedback and may refine it once.
It does not start from a blank page, and Astra is never called when Luna passes.
The draft is capped at 20,000 output tokens, each review at 12,000, and the one
Astra refinement at 24,000 so a stuck or unusually long reasoning pass cannot
repeat the previous open-ended cost.
For a video edition, the first draft contains the complete narration and
six-scene storyboard. The Sol editor scores causal story, visible reversal,
visual causality, ending payoff, and spoken clarity. After the one allowed Astra
refinement, Sol reviews again; another failure stops the run before paid
generation. This preserves the Cobra-standard gate without using Astra on every
edition. The free local narration is also rendered and duration-checked before
the first paid Higgsfield request.

The first pilot keeps a $7.80 hard provider ceiling per finished 60-second video,
caps total configured provider exposure at $30, and submits no automatic paid
retries. The H3 catalog rate verified on October 4, 2026 is $0.065 per second,
so each new 60-second video projects to $3.90. Counting the published first
video at its original conservative $7.80 ceiling, all three remaining video
slots project to a $19.50 configured maximum for the full pilot. A connection-
test workflow verifies `HF_KEY` without submitting a generation. Recurring paid
generation is paused by default; set the repository variable
`VIDEO_PILOT_ENABLED` to `1` to begin the protected two-week pilot. The protected
pilot was activated on October 3, 2026.

Higgsfield website subscriptions and the Higgsfield API are billed separately.
The automated workflow uses the API's prepaid dollar balance; website plan
credits or website-only Unlimited access do not fund these automated requests.

Complete the October 3–17 experiment with the already-funded Higgsfield API;
do not change providers mid-pilot or add more Higgsfield funds. After the pilot,
prioritize the cheapest private-use production route. Compare available Google
Flow credits with a zero-provider-cost procedural animation engine using reusable
SVG characters, real continuous motion, the approved local narrator, captions,
and the existing story review. The procedural option must be a full animated
story rather than a moving carousel. Do not buy ads or another video subscription
during this test.

Audience growth and distribution are not goals. Daily Insight and its free website
remain the destination and permanent archive. Do not create or connect a new
social-media account for video generation; specifically, TikTok Symphony is no
longer part of the plan. Instagram Edits and CapCut are finishing tools unless
their free generation allowances materially change.

The manual `resume_video` recovery path may rebuild an already-published MP4
from its six recorded request IDs. It never submits a new paid video request.
Each newly accepted request ID is saved immediately so an interrupted run can
continue without ordering the same earlier blocks again.

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
- On a video edition, one complete contextual story video that shows who is
  involved, what is going wrong, the model or move, the caveat, and the visible
  project application.

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

## Alternating video and carousel pilot

From October 3 through October 17, 2026, scheduled editions alternate formats:

- **Video edition:** one 60-second generated animated story with warm narration
  and burned captions, shown immediately after the hook card.
- **Carousel edition:** designed static cards with no animation or narration
  requirement.

The first video is the 1,000 True Fans lesson. Later videos may change topic but
must retain a coherent visual world, one causal story, a named model or formula,
an evidence caveat, and a practical connection to a current project.

The alternation is a two-week test, not the intended permanent cadence. The
desired post-pilot format is one full story-led video for every scheduled
edition. Do not expand the paid cadence until a lower-cost engine has been tested
against the same script review, narration, caption, spend-cap, and Cobra Effect
quality gates.

The revised first pilot established that the story-led form works, but it did
not yet meet the Cobra Effect quality bar. A future paid video must contain a
visible mid-story reversal, visual cause and effect, and an ending that resolves
the opening scene. A separate AI editor now enforces that bar before spending.

Math in a narrated video uses one plain-language worked example before showing
any formula. Continuous scripts target roughly 160–180 words, but word count is
only drafting guidance. Before any paid video request, the renderer measures the
actual spoken warm narration and refuses to publish a 60-second episode when the
voice ends before 56.5 seconds or runs past 59.5 seconds. Audio padding cannot
satisfy that check.

## Interactive episode workflow

Every lesson's short video example uses one recurring character, one setting,
one visual metaphor, and one concept. Its minimum story is: context → before or
problem → model or move → after or result. A more ambitious interactive episode
can reach a decision point quickly, let the viewer choose, show the consequence,
and end with a small action.

The earlier free interactive episode remains a fallback and experiment. It is
not the full-video format: full-video editions use generated motion across six
ten-second story blocks and are delivered as one MP4.

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
format going forward. The paid pipeline is `scripts/generate_higgsfield_video.py`.
