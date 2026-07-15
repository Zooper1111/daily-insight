# Daily Insight

Standalone daily learning digest. The website reads `editions.json`, newest first.

## How it works

- `index.html` — the app shell.
- `editions.json` — all editions, newest first.
- `context.md` — public-safe memory for Matt, his projects, content preferences, and corrections.
- `scripts/generate_edition.py` — OpenAI-powered daily generator.
- `.github/workflows/daily-edition.yml` — GitHub Actions workflow that publishes automatically.

## Automated publishing

The GitHub Action runs every morning and can also be run manually from the Actions tab.

Setup required:

1. Create an OpenAI API key.
2. In GitHub, add it as a repository Actions secret named `OPENAI_API_KEY`.
3. Optional: set repository variable `OPENAI_MODEL` to change the model without editing code.

The workflow:

1. Checks out the repo.
2. Installs the OpenAI Python SDK.
3. Runs `scripts/generate_edition.py`.
4. Commits `editions.json` only if a new edition was generated.

The script skips if today's edition already exists, so a manual run will not double-publish.

## Edition schema notes

- `insight.visualSvg`: inline SVG string, single-quoted attributes, viewBox ~560 wide, dark theme colors (bg #1b1e30, ink #eceef7, dim #9ba0b8, gold #e8b84b, coral #ff7a6e, teal #5fd4c4, violet #a48bfa).
- `masters.videoId`: real YouTube video ID found via web search — never invented.
- `masters.start`: seconds offset for the embed when a specific moment is known.
- Paragraph arrays may contain simple inline HTML (`<strong>`, `<em>`).

## Content direction

Daily Insight should teach public speaking, everyday conversation, small talk, better questions, provocative openings, storytelling, strategy, decision-making, AI, product thinking, and useful theories or models. Keep it personal, practical, and immediately usable.

Each edition should usually include:

- One theory, model, framework, or mental model explained simply.
- One public-safe connection to Matt's active workstreams.
- One short applied story, scene, or example that shows how the idea could be used.
