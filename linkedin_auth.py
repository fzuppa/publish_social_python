#!/usr/bin/env python3
"""
One-time (well, every ~60 days) LinkedIn OAuth flow to renew linkedin_token.json.

LinkedIn access tokens for this app expire after ~60 days and there is no
refresh_token issued (that requires a separate LinkedIn "programmatic refresh
tokens" product grant), so renewal means redoing the authorization-code flow:

1. Open the printed URL in a browser and log in as Federico / authorize the app.
2. LinkedIn redirects to http://localhost:8080/callback?code=... — this script
   runs a tiny local server to catch that redirect.
3. Exchanges the code for a new access_token and overwrites linkedin_token.json
   in this same directory (the file publish_social.py / the MCP tool reads).

Usage:
    venv/bin/python linkedin_auth.py
"""

import http.server
import json
import os
import sys
import urllib.parse

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'linkedin_config.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'linkedin_token.json')
REDIRECT_URI = 'http://localhost:8080/callback'
SCOPES = 'openid profile w_member_social'


def main():
    if not os.path.exists(CONFIG_FILE):
        sys.exit(f"Config file not found: {CONFIG_FILE}")
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    client_id = config['client_id']
    client_secret = config['client_secret']

    auth_url = 'https://www.linkedin.com/oauth/v2/authorization?' + urllib.parse.urlencode({
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPES,
        'state': 'publish_social',
    })

    print("Open this URL in your browser and log in / authorize:\n")
    print(auth_url)
    print("\nWaiting for redirect on http://localhost:8080/callback ...")

    captured = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            captured['code'] = qs.get('code', [None])[0]
            captured['error'] = qs.get('error_description', [None])[0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body>Authorization complete. You can close this tab.</body></html>')

    server = http.server.HTTPServer(('localhost', 8080), Handler)
    server.handle_request()  # blocks until one request comes in, then stops

    if captured.get('error'):
        sys.exit(f"Error: {captured['error']}")
    code = captured.get('code')
    if not code:
        sys.exit("No authorization code received.")

    print("Got auth code, exchanging for token...")
    res = requests.post('https://www.linkedin.com/oauth/v2/accessToken', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': client_id,
        'client_secret': client_secret,
    })
    token_data = res.json()

    if token_data.get('error'):
        sys.exit(f"Error: {token_data.get('error_description', token_data['error'])}")

    access_token = token_data['access_token']
    expires_in = token_data['expires_in']
    print(f"Token obtained (expires in {expires_in} seconds / ~{expires_in // 86400} days)")

    print("Fetching LinkedIn profile...")
    profile_res = requests.get(
        'https://api.linkedin.com/v2/userinfo',
        headers={'Authorization': f'Bearer {access_token}'},
    )
    profile_data = profile_res.json()
    member_id = profile_data.get('sub')
    name = profile_data.get('name')
    print(f"Logged in as: {name} ({member_id})")

    with open(TOKEN_FILE, 'w') as f:
        json.dump({
            'access_token': access_token,
            'member_id': member_id,
            'name': name,
            'expires_in': expires_in,
        }, f, indent=2)

    print(f"\nSaved to {TOKEN_FILE}")


if __name__ == '__main__':
    main()
