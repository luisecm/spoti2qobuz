"""Read-only Spotify client: fetches tracks from a public playlist.

Uses the Client Credentials flow (no user login needed) since we only
ever read a public playlist, never write to Spotify.
"""
import base64
import time

import requests

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token

        basic = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        resp = requests.post(
            TOKEN_URL,
            headers={"Authorization": f"Basic {basic}"},
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + payload["expires_in"] - 30
        return self._token

    def get_playlist_name(self, playlist_id: str) -> str:
        resp = requests.get(
            f"{API_BASE}/playlists/{playlist_id}",
            headers={"Authorization": f"Bearer {self._get_token()}"},
            params={"fields": "name"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["name"]

    def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        """Returns a list of {isrc, title, artist, duration_ms} for every
        playable track currently on the playlist."""
        tracks = []
        url = f"{API_BASE}/playlists/{playlist_id}/tracks"
        params = {
            "fields": (
                "next,items(track(name,duration_ms,is_local,"
                "external_ids(isrc),artists(name)))"
            ),
            "limit": 100,
        }
        headers = {"Authorization": f"Bearer {self._get_token()}"}

        while url:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            payload = resp.json()

            for item in payload.get("items", []):
                track = item.get("track")
                if not track or track.get("is_local"):
                    continue
                artists = track.get("artists") or []
                tracks.append(
                    {
                        "isrc": (track.get("external_ids") or {}).get("isrc"),
                        "title": track.get("name"),
                        "artist": artists[0]["name"] if artists else "",
                        "duration_ms": track.get("duration_ms"),
                    }
                )

            url = payload.get("next")
            params = None  # `next` already contains the query string

        return tracks
