# radjp — Japan Live radio list

Static JSON served by GitHub Pages. The Japan Live Android app downloads it on launch (and when you pull to refresh), caches it on the phone, and falls back to the last good copy when offline.

URL: `https://xacking.github.io/radjp/stations.json`

## Fields

| Field | Meaning |
|---|---|
| `id` | Stable id, `r-…`. Favorites are saved by this id, so don't change it. |
| `name`, `jp` | Display name and Japanese name (may be empty) |
| `genre` | One of the values in the top-level `genres` list. The app builds its genre chips from these. |
| `city`, `country` | Where the station is (country is a two-letter code) |
| `desc` | Short line shown under the name |
| `stream.type` | `audio` (MP3/AAC/Ogg/Opus) or `hls` (`.m3u8`) |
| `stream.url` | Direct stream address |
| `homepage`, `logo`, `credit`, `color` | Shown on the player |
| `status` | `official` = the station publishes this stream itself. `directory` = listed in the public [Radio Browser](https://www.radio-browser.info/) directory and confirmed playing when the list was built. |

## Editing

- Add a station: copy an entry, give it a new `id`, and set `status`.
- Hide a station without deleting it: add `"enabled": false`.
- Bump `updated` when you change the file; the app shows it as "List updated".
- Remove any station whose owner asks you to.

The first 11 stations come from `jlive/v1/radio.json`.
