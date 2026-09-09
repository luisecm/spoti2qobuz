"""Matches a Spotify track to a Qobuz catalog track.

Strategy: search Qobuz for "<artist> <title>", then prefer an exact ISRC
match (most reliable), falling back to fuzzy title/artist scoring with a
duration sanity check when ISRC isn't available or doesn't match.
"""
from rapidfuzz import fuzz

from qobuz import Track

FUZZY_MATCH_THRESHOLD = 80
DURATION_TOLERANCE_MS = 5000
DURATION_MISMATCH_PENALTY = 15


def find_qobuz_track_id(spotify_track: dict) -> int | None:
    query = f"{spotify_track['artist']} {spotify_track['title']}"
    raw = Track.search(query, limit=10, raw=True)
    items = raw.get("tracks", {}).get("items", [])
    if not items:
        return None

    isrc = spotify_track.get("isrc")
    if isrc:
        for item in items:
            if (item.get("isrc") or "").upper() == isrc.upper():
                return item["id"]

    target = f"{spotify_track['artist']} {spotify_track['title']}"
    best_item, best_score = None, 0
    for item in items:
        performer = (item.get("performer") or {}).get("name", "")
        candidate = f"{performer} {item.get('title', '')}"
        score = fuzz.token_sort_ratio(target, candidate)

        duration_ms = spotify_track.get("duration_ms")
        item_duration_ms = (item.get("duration") or 0) * 1000
        if duration_ms and item_duration_ms:
            if abs(duration_ms - item_duration_ms) > DURATION_TOLERANCE_MS:
                score -= DURATION_MISMATCH_PENALTY

        if score > best_score:
            best_item, best_score = item, score

    if best_item and best_score >= FUZZY_MATCH_THRESHOLD:
        return best_item["id"]
    return None
