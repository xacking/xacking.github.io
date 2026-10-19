# Japan Live content API

Static JSON served by GitHub Pages. The app reads these files; nothing here needs a server or an API key.

Base URL: `https://xacking.github.io/jlive/v1/`

| File | What it holds | How it changes |
|---|---|---|
| `config.json` | Feed URLs, minimum app version, `showPendingSources`, optional `notice` banner | Edit by hand |
| `channels.json` | Watch tab: news, weather, alert and featured cam channels, numbered for the remote | Edit by hand |
| `cams.json` | Live cams map: real lat/lon, category, credit, YouTube channel | Edit by hand |
| `live.json` | Current live video for every channel and cam, keyed by source `id` | **Automatic**, every 30 minutes |
| `links.json` | Sources the app opens instead of embedding (NHK World, TVer, radiko) | Edit by hand |
| `wallpapers.json` + `wallpapers/` | Wallpaper list, 1170×2532 JPEGs and 390×844 thumbnails | Edit by hand |
| `quiz.json` | "Where in Japan?" and kanji sprint questions | Edit by hand |
| `words.json` | Word of the day; the app picks `words[(daysSince(startDate)) % words.length]` | Edit by hand |
| `sudoku.json` | 30 puzzles (easy, medium, hard), each with one solution | Edit by hand |

## How live streams stay current

`.github/workflows/jlive-live.yml` runs `.github/scripts/jlive_live.py` every 30 minutes. For each source it reads the YouTube channel's Live tab, picks the stream whose title matches the source's `match` words (skipping `exclude` words), checks that embedding is allowed, and commits `live.json` only when something changed.

Each entry in `live.json` looks like:

```json
"dotonbori": {"live": true, "videoId": "6OgYfTMOmhY", "title": "…", "embedUrl": "https://www.youtube.com/embed/6OgYfTMOmhY", "watchUrl": "…", "thumb": "…"}
```

`live: false` comes with a `reason`: `not-live` or `embedding-disabled`. `checked` is the last time the job confirmed the list (at least every 3 hours); `updated` is when it last changed. `stale: true` means YouTube couldn't be read on the last run and the previous value was kept.

## Rules the app must follow

- Play streams only in YouTube's own embedded player. Draw nothing over the video.
- Show `credit` with a link to `channelUrl` on every player and cam card.
- Hide sources with `"status": "pending"` unless `config.showPendingSources` is `true`. Flip a source to `"official"` once its owner says yes.
- Cache feeds on the device; refresh `live.json` every `config.liveRefreshMinutes`.

## Adding a cam

Add an entry to `cams.json` with a unique `id`, the channel's `channelId`, `lat`/`lon` and a few `match` words from the stream title. Pushing the change runs the workflow, which fills in `live.json`.
