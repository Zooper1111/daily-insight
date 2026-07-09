# Daily Insight

Standalone daily learning digest. NOT related to Coordly or any other project.

## How it works
- `index.html` — the app shell (rarely changes)
- `editions.json` — all editions, newest first. The daily scheduled Claude task prepends a new edition here each morning.
- `icon.b64` — base64 of apple-touch-icon.png (deploy with encoding base64 as `apple-touch-icon.png`)

## Publishing flow (performed by the scheduled task)
1. Read `editions.json` and `index.html` from this repo (branch `main`)
2. Generate a new edition object matching the schema of existing entries (see editions.json)
3. Prepend it to `editions[]`, keep max 30 editions, commit back to this repo
4. Deploy `index.html`, updated `editions.json`, and `apple-touch-icon.png` (decoded from icon.b64) to the Vercel project `daily-insight` with target `production`

## Edition schema notes
- `insight.visualSvg`: inline SVG string, single-quoted attributes, viewBox ~560 wide, dark theme colors (bg #1b1e30, ink #eceef7, dim #9ba0b8, gold #e8b84b, coral #ff7a6e, teal #5fd4c4, violet #a48bfa)
- `masters.videoId`: real YouTube video ID found via web search — never invented
- `masters.start`: seconds offset for the embed when a specific moment is known
- Paragraph arrays may contain simple inline HTML (<strong>, <em>)
