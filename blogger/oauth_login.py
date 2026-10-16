#!/usr/bin/env python3
"""One-time OAuth approval for the Blogger publish pipeline (JHL-4 §2).

The owner runs this once. It opens the browser, the owner clicks "Allow", and the
refresh token is written to the local secrets directory (blogger/config.json ->
paths). Nothing secret is printed, and nothing secret leaves this machine.

Flow: loopback redirect (RFC 8252 for desktop clients)
    1. raise the OS browser at Google's consent screen for the configured scopes
    2. catch the ?code=... redirect on http://127.0.0.1:<port>/
    3. exchange it for access + refresh tokens, store them under the secrets dir

Usage:
    python blogger/oauth_login.py                 # browser flow, default port
    python blogger/oauth_login.py --port 8080     # fixed port (use if the client is type "web")
    python blogger/oauth_login.py --print-url     # headless: print the URL, paste back the code
    python blogger/oauth_login.py --check         # verify the stored token refreshes (no browser)
"""

from __future__ import annotations

import argparse
import http.server
import os
import secrets
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blogger_api as api  # noqa: E402

SUCCESS_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Authorised</title></head>
<body style="font-family:system-ui;margin:3rem auto;max-width:32rem;line-height:1.6">
<h1>Authorised</h1><p>The Owner's Handbook publish pipeline now holds a refresh token for
this Google account. You can close this tab and return to the terminal.</p></body></html>"""


def _handle_code(cfg: dict, code: str, redirect_uri: str) -> dict:
    print("Exchanging the authorization code for tokens ...")
    payload = api.exchange_code(cfg, code, redirect_uri)
    token = {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "token_type": payload.get("token_type", "Bearer"),
        "scopes": (payload.get("scope") or "").split(),
        "expires_at": time.time() + int(payload.get("expires_in", 3600)) - 60,
        "obtained_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    if not token["refresh_token"]:
        print("WARNING: no refresh token returned. The consent screen is probably still in")
        print("         'Testing' status (refresh tokens expire after 7 days) or the account")
        print("         already granted consent — set the consent screen to 'Publish' and re-run.")
    path = api.save_token(cfg, token)
    print(f"Token stored: {path}")
    print("Token metadata: " + api.token_summary(token))
    return token


def loopback_flow(cfg: dict, port: int) -> int:
    host = cfg["oauth"]["loopbackHost"]
    state = secrets.token_urlsafe(24)
    box: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):  # keep the console clean
            pass

        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if "code" not in params and "error" not in params:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(SUCCESS_PAGE.encode())
            box.update(params)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    with socketserver.TCPServer((host, port), Handler) as httpd:
        actual_port = httpd.server_address[1]
        redirect_uri = f"http://{host}:{actual_port}/"
        url = api.build_auth_url(cfg, redirect_uri, state)
        print("Open this URL and click Allow (scopes: " + " ".join(cfg["oauth"]["scopes"]) + "):")
        print(url)
        try:
            webbrowser.open(url)
        except Exception:  # pragma: no cover - headless fallback
            pass
        print(f"\nWaiting for the redirect on {redirect_uri} ...")
        httpd.serve_forever()

    if box.get("error"):
        print(f"Authorization failed: {box['error'][0]}")
        return 1
    if state and box.get("state", [None])[0] != state:
        print("State mismatch — aborting (possible CSRF).")
        return 1
    _handle_code(cfg, box["code"][0], redirect_uri)
    return 0


def manual_flow(cfg: dict, port: int) -> int:
    """Headless path: print the URL, the owner pastes the code back."""
    state = secrets.token_urlsafe(24)
    redirect_uri = f"http://{cfg['oauth']['loopbackHost']}:{port}/"
    url = api.build_auth_url(cfg, redirect_uri, state)
    print("1) Open this URL in any browser and click Allow:")
    print(url)
    print(f"\n2) The browser lands on {redirect_uri}?code=... (the page will not load — that is fine).")
    print("   Copy the value of the 'code' parameter and paste it below.\n")
    code = input("authorization code: ").strip()
    if not code:
        print("No code given — nothing stored.")
        return 1
    _handle_code(cfg, code, redirect_uri)
    return 0


def check_flow(cfg: dict) -> int:
    path = api.token_path(cfg)
    if not os.path.isfile(path):
        print(f"No token yet at {path}. Run oauth_login.py first.")
        return 1
    token = api.load_token(cfg)
    try:
        refreshed = api.refresh_access_token(cfg, token)
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        print(f"Token refresh FAILED: {exc}")
        return 1
    api.save_token(cfg, refreshed)
    print("Token refresh OK. " + api.token_summary(refreshed))
    client = api.BloggerClient(cfg, refreshed)
    blogs = client.blogs_by_user()
    print(f"Authorised blogs: {len(blogs)}")
    for blog in blogs:
        print(f"  - {blog.get('name')} ({blog.get('url')}) id={blog.get('id')} "
              f"posts={blog.get('posts', {}).get('totalItems')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="One-time Google authorization for the Blogger pipeline")
    parser.add_argument("--port", type=int, default=None, help="loopback port (0 = pick a free one)")
    parser.add_argument("--print-url", action="store_true", help="headless: print the URL and paste the code back")
    parser.add_argument("--check", action="store_true", help="verify the stored token by refreshing it")
    args = parser.parse_args()

    cfg = api.load_config()
    if args.check:
        return check_flow(cfg)
    port = args.port if args.port is not None else cfg["oauth"]["loopbackPort"]
    if args.print_url:
        return manual_flow(cfg, port or 8765)
    return loopback_flow(cfg, port)


if __name__ == "__main__":
    sys.exit(main())
