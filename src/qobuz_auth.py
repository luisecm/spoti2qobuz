"""Authenticates against Qobuz, reusing a cached OAuth token when possible.

First run opens a browser for you to log into Qobuz; the resulting token
is cached in state.json so later runs don't need a browser at all.
"""
from qobuz.qoauth import QobuzOAuth
from qobuz.qopy import qobuz_api, AuthenticationError

from src.state import load_state, save_state


def _login_with_browser() -> dict:
    oauth = QobuzOAuth()
    if not oauth.handle_oauth_login():
        raise RuntimeError("Qobuz OAuth login failed or was cancelled.")
    return {
        "user_id": oauth.oauth_user_id,
        "auth_token": oauth.oauth_user_auth_token,
        "app_id": oauth.app_id,
        "secrets": oauth.secrets,
    }


def ensure_authenticated() -> None:
    """Connects qobuz_api, logging in via browser only if there is no
    usable cached token."""
    state = load_state()
    creds = state.get("qobuz")

    if creds:
        try:
            qobuz_api.connect_with_token(
                creds["user_id"],
                creds["auth_token"],
                creds["app_id"],
                creds["secrets"],
            )
            return
        except AuthenticationError:
            print("Cached Qobuz session expired, re-authenticating...")

    creds = _login_with_browser()
    state["qobuz"] = creds
    save_state(state)

    qobuz_api.connect_with_token(
        creds["user_id"], creds["auth_token"], creds["app_id"], creds["secrets"]
    )
