# Spotify 2 Qobuz Sync!

Mirrors a public Spotify playlist into a single Qobuz playlist. Run it
manually whenever you want to refresh — it always updates the *same*
Qobuz playlist (created once, then reused) and makes its tracks match
whatever is currently on the Spotify playlist, adding new tracks and
removing ones that fell off.

Qobuz has no official public API, so this uses their private
(reverse-engineered) API via the [python-qobuz](https://github.com/fdenivac/python-qobuz)
library — same one Qobuz's own apps use, but unofficial and could break
if Qobuz changes something.

## Setup

1. This needs Python 3.11+ (the Qobuz library requires it). A venv is
   already set up in `.venv` using Homebrew's `python@3.11`. If you need
   to recreate it:

   ```
   /opt/homebrew/bin/python3.11 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. Create a Spotify app to read the playlist (read-only, no user login
   needed since we only read a public playlist):
   - Go to https://developer.spotify.com/dashboard, create an app.
   - Copy the **Client ID** and **Client Secret**.

3. Copy `.env.example` to `.env` and fill in your Spotify credentials.
   The playlist ID is already set to the one from your link
   (`3oek0V0Gmx1QO4ZTNERl3U`); change `QOBUZ_PLAYLIST_NAME` if you want
   the created Qobuz playlist to have a different name.

   ```
   cp .env.example .env
   ```

4. Run the sync:

   ```
   .venv/bin/python sync.py
   ```

   On the first run, a browser tab opens for you to log into Qobuz.
   After you approve, the session is cached in `state.json` (gitignored)
   so future runs don't need the browser again — and reuse the same
   playlist id, never create a duplicate.

## Refreshing later

Just run `.venv/bin/python sync.py` again, any time. It's idempotent:
re-running without any changes on Spotify does nothing.

## Known limitations

- Every run fully rebuilds the Qobuz playlist's track list (deletes all
  tracks, then re-adds them one at a time in Spotify's current order)
  rather than diffing incrementally. Qobuz has no reorder endpoint, and
  its batched "add multiple tracks" call doesn't respect the order of
  the track list it's given — only sequential single-track add calls
  actually append in order. That means a sync makes roughly one API
  call per track, which is slower for a big playlist but fine for a
  manual, occasional refresh.
- A small percentage of tracks may not be found on Qobuz's catalog (or
  match a different regional release); these are printed at the end of
  each run as "unmatched" so you can check them manually.
- If Qobuz changes their private API, this may need updating — it's
  unofficial and not guaranteed stable.
