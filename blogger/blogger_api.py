#!/usr/bin/env python3
"""Blogger API v3 client + OAuth token handling (Python standard library only).

Why these tools are plain stdlib Python and not the Google client library:
  * This Windows box has no google-api-python-client / google-auth installed and
    installing packages for a one-off publish tool adds a maintenance surface.
  * The whole surface we need is five HTTP calls (auth URL, token exchange, token
    refresh, Blogger REST, GSC REST) — all reachable with urllib.
  * Python 3.14 is already on PATH (`python -V`), so the owner and any future agent
    can run the pipeline with zero setup.

Secrets policy (JHL-4 §2): the OAuth client JSON and the token JSON live only in the
local secrets directory (see blogger/config.json). Neither file's *contents* are ever
printed, logged, committed or pasted into Paperclip. Only paths and metadata
(scopes, expiry, whether a refresh token exists) are reported.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
BLOGGER_API = "https://www.googleapis.com/blogger/v3"
GSC_API = "https://www.googleapis.com/webmasters/v3"


class ApiError(RuntimeError):
    """An HTTP error from Google, with the body kept (never contains secrets)."""

    def __init__(self, status: int, url: str, body: str):
        self.status = status
        self.url = url
        self.body = body
        super().__init__(f"HTTP {status} for {url}: {body[:400]}")


# --------------------------------------------------------------------------- config


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve(cfg: dict, key: str) -> str:
    paths = cfg["paths"]
    return os.path.join(paths["secretsDir"], paths[key])


def client_path(cfg: dict) -> str:
    return _resolve(cfg, "clientJson")


def token_path(cfg: dict) -> str:
    return _resolve(cfg, "tokenJson")


# ----------------------------------------------------------------------------- oauth


def read_client(cfg: dict) -> dict:
    """Return the OAuth client identity (client_id / client_secret / token_uri)."""
    path = client_path(cfg)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"OAuth client JSON not found at {path}. The owner creates it in GCP "
            "(Desktop app) — see blogger/README.md and the parent issue's §2."
        )
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    block = raw.get("installed") or raw.get("web") or raw
    missing = [k for k in ("client_id", "client_secret") if not block.get(k)]
    if missing:
        raise ValueError(f"client JSON is missing {missing}")
    return {
        "client_id": block["client_id"],
        "client_secret": block["client_secret"],
        "token_uri": block.get("token_uri") or TOKEN_ENDPOINT,
    }


def build_auth_url(cfg: dict, redirect_uri: str, state: str, scopes: list[str] | None = None) -> str:
    client = read_client(cfg)
    params = {
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes or cfg["oauth"]["scopes"]),
        # offline + consent: guarantees a refresh token (the 7-day expiry trap the
        # parent plan calls out is avoided by publishing the consent screen).
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params)


def _post_form(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, url, exc.read().decode("utf-8", "replace")) from None


def exchange_code(cfg: dict, code: str, redirect_uri: str) -> dict:
    client = read_client(cfg)
    return _post_form(
        client["token_uri"],
        {
            "code": code,
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def refresh_access_token(cfg: dict, token: dict) -> dict:
    client = read_client(cfg)
    if not token.get("refresh_token"):
        raise ValueError("token file has no refresh_token; re-run oauth_login.py")
    payload = _post_form(
        client["token_uri"],
        {
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    token = dict(token)
    token["access_token"] = payload["access_token"]
    token["expires_at"] = time.time() + int(payload.get("expires_in", 3600)) - 60
    if payload.get("scope"):
        token["scopes"] = payload["scope"].split()
    return token


def save_token(cfg: dict, token: dict) -> str:
    path = token_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(token, fh, indent=2)
        fh.write("\n")
    try:  # best-effort: keep the token readable only by the owner (POSIX; no-op risk on Windows)
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_token(cfg: dict) -> dict:
    path = token_path(cfg)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"No token at {path}. Run: python blogger/oauth_login.py (owner approves once in the browser)."
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def token_summary(token: dict) -> str:
    """Human-readable metadata about a token — never the secret values."""
    expiry = token.get("expires_at")
    when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry)) if expiry else "unknown"
    scopes = ", ".join(token.get("scopes", []) or [])
    return (
        f"refresh_token={'yes' if token.get('refresh_token') else 'no'} "
        f"access_token_expires_at={when} scopes=[{scopes}]"
    )


# ------------------------------------------------------------------------ api client


class BloggerClient:
    """Minimal Blogger API v3 wrapper. Refreshes the access token when needed."""

    def __init__(self, cfg: dict | None = None, token: dict | None = None):
        self.cfg = cfg or load_config()
        self.token = token or load_token(self.cfg)
        self._save_after_refresh = token is None

    # -- auth plumbing -----------------------------------------------------

    def _access_token(self) -> str:
        if not self.token.get("access_token") or self.token.get("expires_at", 0) < time.time():
            self.token = refresh_access_token(self.cfg, self.token)
            if self._save_after_refresh:
                save_token(self.cfg, self.token)
        return self.token["access_token"]

    def request(self, method: str, url: str, body: dict | None = None, params: dict | None = None) -> dict:
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self._access_token())
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, url, exc.read().decode("utf-8", "replace")) from None

    # -- blogs -------------------------------------------------------------

    @property
    def blog_id(self) -> str:
        return str(self.cfg["blog"]["id"])

    def blog(self, blog_id: str | None = None) -> dict:
        return self.request("GET", f"{BLOGGER_API}/blogs/{blog_id or self.blog_id}")

    def blogs_by_user(self) -> list[dict]:
        return self.request("GET", f"{BLOGGER_API}/users/self/blogs").get("items", [])

    # -- posts -------------------------------------------------------------

    def insert_post(self, post: dict, is_draft: bool = True) -> dict:
        return self.request(
            "POST",
            f"{BLOGGER_API}/blogs/{self.blog_id}/posts",
            post,
            {"isDraft": "true" if is_draft else "false"},
        )

    def patch_post(self, post_id: str, patch: dict) -> dict:
        return self.request("PATCH", f"{BLOGGER_API}/blogs/{self.blog_id}/posts/{post_id}", patch)

    def get_post(self, post_id: str) -> dict:
        return self.request("GET", f"{BLOGGER_API}/blogs/{self.blog_id}/posts/{post_id}")

    def list_posts(self, status: str | None = None, max_results: int = 25) -> list[dict]:
        params = {"maxResults": str(max_results), "fetchBodies": "false"}
        if status:
            params["status"] = status
        return self.request("GET", f"{BLOGGER_API}/blogs/{self.blog_id}/posts", params=params).get("items", [])

    def search_post(self, query: str) -> list[dict]:
        return self.request(
            "GET",
            f"{BLOGGER_API}/blogs/{self.blog_id}/posts/search",
            params={"q": query, "fetchBodies": "false"},
        ).get("items", [])

    def publish_post(self, post_id: str) -> dict:
        return self.request("POST", f"{BLOGGER_API}/blogs/{self.blog_id}/posts/{post_id}/publish")

    def revert_post(self, post_id: str) -> dict:
        return self.request("POST", f"{BLOGGER_API}/blogs/{self.blog_id}/posts/{post_id}/revert")

    def delete_post(self, post_id: str) -> None:
        self.request("DELETE", f"{BLOGGER_API}/blogs/{self.blog_id}/posts/{post_id}")

    # -- pages -------------------------------------------------------------

    def list_pages(self) -> list[dict]:
        return self.request("GET", f"{BLOGGER_API}/blogs/{self.blog_id}/pages").get("items", [])

    def insert_page(self, page: dict) -> dict:
        return self.request("POST", f"{BLOGGER_API}/blogs/{self.blog_id}/pages", page)

    def patch_page(self, page_id: str, patch: dict) -> dict:
        return self.request("PATCH", f"{BLOGGER_API}/blogs/{self.blog_id}/pages/{page_id}", patch)

    # -- Search Console (scope webmasters.readonly; used from Phase 3 onward) ----

    def gsc_sites(self) -> list[dict]:
        return self.request("GET", f"{GSC_API}/sites").get("siteEntry", [])

    def gsc_query(self, site_url: str, body: dict) -> dict:
        quoted = urllib.parse.quote(site_url, safe="")
        return self.request("POST", f"{GSC_API}/sites/{quoted}/searchAnalytics/query", body)
