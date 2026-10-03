# Daily Insight Format Catalog and Roadmap

This is the public-safe product direction for the next version of Daily Insight.

## What exists now

- A vertical, swipeable card feed with direct links to editions and cards.
- Hook, explanation, visual, practice, and reusable-line cards.
- An in-browser 9:16 stick-figure animation pilot with timed captions, continuous
  motion, a viewer choice, and two outcomes.
- Warm, opt-in Kokoro narration synchronized with captions.
- A no-cost visual fallback built with SVG, CSS, and JavaScript.
- A path for exporting linear 9:16 videos for social platforms.

## What stays

- The swipeable cards and short reading time.
- Warm narration, always-visible captions, and mobile-first 9:16 framing.
- Concrete examples tied to public-safe work situations.
- Lightweight in-browser animation as the free and reliable fallback.

## What changes

1. During the two-week pilot, every other edition gets one complete 60-second
   contextual story video; the editions between them are static carousels.
2. The video follows context → problem → model or move → visible result.
3. The generic “See the Model” card is removed by default. A separate visual
   card appears only for a chart, formula, algorithm, causal diagram, or mechanism
   that genuinely adds understanding.
4. Lessons move up a level: more research-backed frameworks, algorithms,
   formulas, decision science, economics, strategy, systems, network effects,
   creator economics, and game theory; fewer obvious communication reminders.
5. Memorable claims carry an evidence label and source. The lesson distinguishes
   empirical findings from formal models, theories, and useful heuristics.

## Recommended edition sequence

1. **Hook** — the surprising question, tension, or number.
2. **Idea** — the advanced concept, explained simply with an evidence label.
3. **Watch it happen** — on video editions, one complete animated story that
   carries the lesson from hook through project application.
4. **Use it** — a calculation, decision, drill, or script to apply today.
5. **Keep this line** — a concise closing phrase worth remembering or copying.

## Video quality bar

- Establish the people, goal, and friction before naming the model.
- Use one setting, one visual metaphor, one concept, and one clear outcome.
- Make the cause-and-effect visible; do not merely animate labels.
- Keep the narration conversational and warm, with captions that work on mute.
- A standard example can be a short linear clip. Add branching only when the
  viewer's choice teaches something the linear version cannot.
- Avoid disconnected image slides, decorative motion, and vague “before” and
  “after” labels without a real situation.

## Story-led model lessons

Use this as a recurring flagship format, inspired by short illustrated explainers
that make a named concept memorable without requiring expensive full-motion video.
Borrow the teaching architecture, not another creator's artwork, wording, brand,
or promotional ending.

1. **Modern hook** — connect the idea to a current frustration, behavior, or
   decision in one provocative line.
2. **Vivid case** — tell a specific historical or real-world story with stakes
   and a causal turn.
3. **Model reveal** — name the concept only after the viewer can feel the pattern.
4. **Modern transfer** — show two different present-day places where the same
   mechanism appears.
5. **Diagnostic** — end with a question, test, or decision rule the viewer can use.

The illustrated version uses six to ten vertical scenes in one coherent visual
world, gentle pans or pushes, warm narration, a persistent top hook, and short
burned-style captions with one highlighted keyword. Target 45–75 seconds. The
website can reproduce this with generated still illustrations plus CSS motion;
it does not require a monthly video-generation subscription.

Accuracy is part of the format. Verify the anchor story and give its evidence
status. For example, the cobra-bounty story is a powerful illustration of
perverse incentives but its historical basis is disputed, so it must be labeled
as an often-told anecdote rather than established colonial history.

Strong future candidates include Goodhart's Law, Campbell's Law, Braess's
Paradox, Jevons Paradox, the principal-agent problem, survivorship bias,
Schelling points, power-law outcomes, option value, and the peak-end rule.

## Pay-per-video integration plan

A pay-per-generation provider can supply an occasional generated motion layer
while Daily Insight keeps the cards, choices, captions, narration controls, and
lesson logic. Do not require a monthly video subscription.

### Step 1 — Free production system

- Select and source the lesson.
- Write the five-card edition and evidence label.
- Storyboard the contextual example in four beats.
- Produce captions and warm narration.
- Render the example with the existing SVG/stick-figure system.

This remains the fallback even after a paid generator is connected.

### Step 2 — Two-week controlled pay-per-video pilot

- Use a pay-as-you-go provider account and keep its API key in repository
  secrets, never in the public site or repository.
- Use a faceless explainer style such as Stickman Cartoon, Hand Drawn, or
  Editorial Motion Graphics.
- Reuse one character and visual style so editions feel like a series.
- Begin with reference-guided video so the approved illustration controls the
  recurring character, palette, texture, and overall visual world.
- Generate six ten-second motion blocks and assemble them into one 60-second
  9:16 MP4 with warm local narration and burned captions.
- Alternate full-video and static-carousel editions from October 3 through
  October 17, 2026. This yields four possible video editions and four static
  editions on the existing every-other-day publication cadence.
- Cap the provider portion of each full video at $7.80. Submit no automatic paid
  retry; a failed block stops the run for review instead of silently spending
  again.
- Judge comprehension, visual continuity, voice fit, motion quality, generation
  time, phone playback, and actual cost after every completed video.

The website should continue to own interactivity. The selected provider
generates the visual clip; the site surrounds it with choices, captions,
controls, and the rest of the lesson. Full automation should wait until the
pilot establishes a repeatable quality and cost threshold.

### Step 3 — Repeatable production

- Save the approved style, character reference, prompt pattern, and shot timing.
- Generate full videos only on the alternating video dates, after the script and
  source check pass. Carousel dates must not call the paid video API.
- Keep a free SVG version available when generation fails or is not worth the
  credits.
- Consider API automation only after manual generation is consistently useful.

## First proposed pilot: 1,000 True Fans

This is a better content test because it contains a useful model and a formula,
not just a communication reminder.

**Model:** A creator may be able to build a sustainable business from a smaller
group of committed direct supporters rather than chasing a mass audience.

**Formula:**

`required true fans = target annual income ÷ annual gross profit per true fan`

- At $100 annual gross profit per fan, a $100,000 target requires 1,000 fans.
- At $20 annual gross profit per fan, the same target requires 5,000 fans.

**Evidence label:** useful creator-economics model or heuristic, not a proven
viral algorithm and not a guarantee that an audience will “explode.” Its value
is the unit-economics calculation. The answer changes with price, margin,
retention, direct reach, and the creator's income target.

**Video arc:** A creator watches a huge follower counter barely move, replaces
it with a small group of repeat supporters, changes the value per supporter,
and sees the required audience size recalculate in real time.

## Decision gate

Matt authorized a $30 prepaid API balance, and the first six ten-second sections
have been generated. Auto top-up remains off. Recurring paid generation is now
paused until the assembled first video is reviewed and approved. Recovery and
editing must reuse those existing six request IDs and may not submit another
paid batch. If the pilot is approved later, automation may be enabled explicitly
with the `VIDEO_PILOT_ENABLED` repository variable. Keep the free SVG path
regardless of the result.

## Cost guardrail

- The default production system must have no recurring video-generation
  subscription. Do not start a monthly video plan unless Matt explicitly changes
  this preference.
- Build standard examples with the existing SVG/CSS/JavaScript animation,
  warm local Kokoro narration, captions, and a local browser-to-video export.
- Use external generative video on the alternating pilot editions only; the
  editions between them remain static carousels.
- For occasional generated clips, prefer a capped pay-as-you-go API over a
  monthly subscription. Quote the estimated per-clip charge before generation
  and keep credentials in repository secrets, never in this public repository.
- The funded pilot is approved through October 17, 2026, within the $30 prepaid
  balance and the per-video ceiling above. Continuing paid generation after the
  pilot requires a new decision.

## References

- Kevin Kelly, [1,000 True Fans](https://kk.org/thetechnium/1000-true-fans/)
- Higgsfield, [MCP for ChatGPT and Claude](https://higgsfield.ai/mcp?tab=chatgpt)
- Higgsfield, [MCP for Marketers](https://higgsfield.ai/blog/mcp-for-marketers)
- Storyfelted, [illustrated Cobra Effect explainer](https://www.instagram.com/p/DdGftGzMTjq/)
