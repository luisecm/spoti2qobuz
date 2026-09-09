#!/usr/bin/env python3
"""Mirrors a public Spotify playlist into a single, fixed Qobuz playlist.

Run manually whenever you want to refresh:  python sync.py

Idempotent: always targets the same Qobuz playlist (its id is cached in
state.json after the first run). Every run fully rebuilds that playlist's
track list (delete all, then re-add in Spotify's current order) so it
always matches the Spotify playlist's tracks *and order* exactly. Qobuz's
API has no reorder endpoint, so incremental add/remove can't keep order
in sync -- a full rebuild is the only reliable way.
"""
import os
import sys
from collections import Counter

from dotenv import load_dotenv

from qobuz import Playlist, User

from src.matcher import find_qobuz_track_id
from src.qobuz_auth import ensure_authenticated
from src.spotify_client import SpotifyClient
from src.state import load_state, save_state

load_dotenv()

SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_PLAYLIST_ID = os.environ["SPOTIFY_PLAYLIST_ID"]
QOBUZ_PLAYLIST_NAME = os.environ.get("QOBUZ_PLAYLIST_NAME", "Spotify Sync")


def get_or_create_qobuz_playlist(name: str) -> Playlist:
    state = load_state()
    playlist_id = state.get("qobuz_playlist_id")

    if playlist_id:
        try:
            return Playlist.from_id(playlist_id)
        except Exception:
            print(
                f"Cached Qobuz playlist {playlist_id} no longer exists, "
                "creating a new one."
            )

    playlist = User().playlist_create(
        name=name, description="Synced from Spotify"
    )
    state["qobuz_playlist_id"] = playlist.id
    save_state(state)
    print(f"Created Qobuz playlist '{name}' (id={playlist.id})")
    return playlist


def main() -> int:
    print(f"Fetching Spotify playlist tracks...")
    spotify = SpotifyClient(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    spotify_tracks = spotify.get_playlist_tracks(SPOTIFY_PLAYLIST_ID)
    print(f"  {len(spotify_tracks)} tracks on Spotify")

    ensure_authenticated()
    playlist = get_or_create_qobuz_playlist(QOBUZ_PLAYLIST_NAME)

    existing = playlist.get_tracks()
    existing_playlist_track_ids = [t.playlist_track_id for t in existing]
    existing_track_id_counts = Counter(t.id for t in existing)
    print(f"  {len(existing)} tracks currently in Qobuz playlist")

    ordered_track_ids = []
    unmatched = []
    for track in spotify_tracks:
        qobuz_id = find_qobuz_track_id(track)
        if qobuz_id is None:
            unmatched.append(track)
        else:
            ordered_track_ids.append(qobuz_id)

    new_track_id_counts = Counter(ordered_track_ids)
    added = sum((new_track_id_counts - existing_track_id_counts).values())
    removed = sum((existing_track_id_counts - new_track_id_counts).values())
    unchanged = sum((new_track_id_counts & existing_track_id_counts).values())

    # Rebuild from scratch every run: only way to guarantee order matches
    # Spotify's current order (see module docstring). Tracks are added one
    # at a time (max_elements_per_request=1) because Qobuz's batched
    # playlist/addTracks call does NOT respect the order of the track_ids
    # it's given -- only sequential single-track calls append in order.
    if existing_playlist_track_ids:
        playlist.del_tracks(existing_playlist_track_ids)
    if ordered_track_ids:
        playlist.add_tracks(ordered_track_ids, max_elements_per_request=1)

    print(f"\nSync complete for '{playlist.name}':")
    print(f"  added:     {added}")
    print(f"  removed:   {removed}")
    print(f"  unchanged: {unchanged}")
    if unmatched:
        print(f"  unmatched: {len(unmatched)} (not found on Qobuz)")
        for track in unmatched:
            print(f"    - {track['artist']} - {track['title']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
