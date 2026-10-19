"""Find each Japan Live source's current YouTube live stream and write jlive/v1/live.json.

Runs on a schedule in GitHub Actions. No API key needed: it reads each channel's public
"Live" tab, picks the live stream whose title matches the source, and checks through
YouTube's oEmbed endpoint that the video may be embedded.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'jlive', 'v1')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ja,en;q=0.8', 'Cookie': 'CONSENT=YES+1; SOCS=CAI'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', 'replace')


def initial_data(html):
    m = re.search(r'var ytInitialData = (\{.*?\});</script>', html)
    return json.loads(m.group(1)) if m else {}


def live_videos(channel_id):
    """Return [(videoId, title)] for streams that are live right now on the channel."""
    data = initial_data(fetch(f'https://www.youtube.com/channel/{channel_id}/streams'))
    found = []

    def walk(o):
        if isinstance(o, dict):
            if 'lockupViewModel' in o:
                v = o['lockupViewModel']
                blob = json.dumps(v.get('contentImage', {}))
                if 'BADGE_STYLE_LIVE' in blob:
                    title = v.get('metadata', {}).get('lockupMetadataViewModel', {}).get('title', {}).get('content', '')
                    found.append((v.get('contentId'), title))
                return
            if 'videoRenderer' in o:  # older layout
                v = o['videoRenderer']
                blob = json.dumps(v.get('badges', [])) + json.dumps(v.get('thumbnailOverlays', []))
                if 'LIVE' in blob:
                    title = ''.join(r.get('text', '') for r in v.get('title', {}).get('runs', []))
                    found.append((v.get('videoId'), title))
                return
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    seen, out = set(), []
    for vid, title in found:
        if vid and vid not in seen:
            seen.add(vid)
            out.append((vid, title))
    return out


def embeddable(video_id):
    url = 'https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote(f'https://www.youtube.com/watch?v={video_id}')
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return False


def pick(source, lives):
    match = [m.lower() for m in source.get('match', [])]
    exclude = [m.lower() for m in source.get('exclude', [])]
    pinned = source.get('pinnedVideoId')
    for vid, _ in lives:
        if vid == pinned:
            return vid, _
    ok = [(v, t) for v, t in lives if not any(x in t.lower() for x in exclude)]
    for m in match:
        for v, t in ok:
            if m in t.lower():
                return v, t
    if not match and ok:
        return ok[0]
    return None, None


def main():
    channels = json.load(open(os.path.join(ROOT, 'channels.json'), encoding='utf-8'))['channels']
    cams = json.load(open(os.path.join(ROOT, 'cams.json'), encoding='utf-8'))['cams']
    old_path = os.path.join(ROOT, 'live.json')
    try:
        old = json.load(open(old_path, encoding='utf-8')).get('streams', {})
    except Exception:
        old = {}

    sources = {}
    for s in channels + cams:
        sources.setdefault(s['id'], s)

    cache, streams, errors = {}, {}, 0
    for sid, s in sources.items():
        ch = s['channelId']
        try:
            if ch not in cache:
                cache[ch] = live_videos(ch)
                time.sleep(1)
            vid, title = pick(s, cache[ch])
            if vid and not embeddable(vid):
                streams[sid] = dict(live=False, reason='embedding-disabled', videoId=vid)
                continue
            if vid:
                streams[sid] = dict(live=True, videoId=vid, title=title,
                                    embedUrl=f'https://www.youtube.com/embed/{vid}',
                                    watchUrl=f'https://www.youtube.com/watch?v={vid}',
                                    thumb=f'https://i.ytimg.com/vi/{vid}/hqdefault_live.jpg')
            else:
                streams[sid] = dict(live=False, reason='not-live')
        except Exception as e:  # keep the last known value when YouTube can't be read
            errors += 1
            print(f'{sid}: {e}', file=sys.stderr)
            if sid in old:
                streams[sid] = {**old[sid], 'stale': True}

    if errors == len(sources):
        print('No source could be read; leaving live.json unchanged', file=sys.stderr)
        return 1

    def comparable(d):
        return {k: {kk: vv for kk, vv in v.items() if kk != 'stale'} for k, v in d.items()}
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    stamp = now.isoformat().replace('+00:00', 'Z')
    try:
        prev = json.load(open(old_path, encoding='utf-8'))
    except Exception:
        prev = {}
    changed = comparable(streams) != comparable(old) or any(v.get('stale') for v in streams.values())
    last_check = datetime.datetime.fromisoformat((prev.get('checked') or prev.get('updated') or '2000-01-01T00:00:00Z').replace('Z', '+00:00'))
    if not changed and now - last_check < datetime.timedelta(hours=3):
        print('No change')
        return 0

    # "updated" = when the stream list last changed; "checked" = last time this job confirmed it.
    # A heartbeat write at least every 3 hours keeps "checked" honest without a commit every run.
    out = dict(updated=stamp if changed else prev.get('updated', stamp), checked=stamp, streams=streams)
    with open(old_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')
    live = sum(1 for v in streams.values() if v.get('live'))
    print(f'Wrote live.json: {live} of {len(streams)} live')
    return 0


if __name__ == '__main__':
    sys.exit(main())
