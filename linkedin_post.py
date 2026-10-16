#!/usr/bin/env python3
"""
Publish a text (optionally with one image) post to LinkedIn.

Uses the modern LinkedIn Posts API (/rest/posts, /rest/images), as opposed
to publish_social.py's video flow which still targets the older, deprecated
/v2/ugcPosts + /v2/assets endpoints. Reuses the same linkedin_token.json
produced/renewed by linkedin_auth.py.
"""

import argparse
import json
import mimetypes
import os
import sys
from datetime import date

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LINKEDIN_TOKEN_PATH = os.path.join(SCRIPT_DIR, 'linkedin_token.json')
API_BASE = 'https://api.linkedin.com/rest'
# LinkedIn only keeps a rolling window of versioned API releases active, so
# pin to the current month rather than a hardcoded value that goes stale.
LINKEDIN_API_VERSION = date.today().strftime('%Y%m')

# LinkedIn's commentary field uses a lightweight inline markup where these
# characters are reserved; an unescaped one can truncate or misrender the
# post. Escaping backslash itself must happen first, so it doesn't re-escape
# the backslashes this function inserts for the other characters.
# https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/plain-text-share-content
RESERVED_CHARS = ['\\', '(', ')', '[', ']', '{', '}', '<', '>', '@', '*', '_', '~', '|']


def escape_commentary(text):
    for ch in RESERVED_CHARS:
        text = text.replace(ch, '\\' + ch)
    return text


def load_auth():
    with open(LINKEDIN_TOKEN_PATH) as f:
        token_data = json.load(f)
    token = token_data['access_token']
    author_urn = f"urn:li:person:{token_data['member_id']}"
    headers = {
        'Authorization': f"Bearer {token}",
        'LinkedIn-Version': LINKEDIN_API_VERSION,
        'X-Restli-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json',
    }
    return author_urn, headers


def upload_image(author_urn, headers, image_path):
    print("LinkedIn: registering image upload...")
    res = requests.post(
        f"{API_BASE}/images?action=initializeUpload",
        headers=headers,
        json={'initializeUploadRequest': {'owner': author_urn}},
    )
    data = res.json()
    if res.status_code != 200:
        sys.exit(f"LinkedIn error registering image upload: {data}")

    upload_url = data['value']['uploadUrl']
    image_urn = data['value']['image']

    mime_type = mimetypes.guess_type(image_path)[0] or 'application/octet-stream'
    print(f"LinkedIn: uploading image ({os.path.getsize(image_path)} bytes)...")
    with open(image_path, 'rb') as f:
        put_res = requests.put(upload_url, data=f, headers={'Content-Type': mime_type})
    if put_res.status_code not in (200, 201):
        sys.exit(f"LinkedIn error uploading image: {put_res.status_code} {put_res.text}")

    return image_urn


def post_url(post_id):
    return f"https://www.linkedin.com/feed/update/{post_id}/"


def publish_post(opts):
    author_urn, headers = load_auth()

    body = {
        'author': author_urn,
        'commentary': escape_commentary(opts.text),
        'visibility': opts.visibility,
        'distribution': {
            'feedDistribution': 'MAIN_FEED',
            'targetEntities': [],
            'thirdPartyDistributionChannels': [],
        },
        'lifecycleState': 'PUBLISHED',
        'isReshareDisabledByAuthor': False,
    }

    if opts.image:
        if opts.dry_run:
            body['content'] = {'media': {'id': f"<would upload {opts.image}>"}}
        else:
            image_urn = upload_image(author_urn, headers, opts.image)
            body['content'] = {'media': {'id': image_urn}}

    if opts.dry_run:
        print("Dry run: would POST to", f"{API_BASE}/posts")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return

    print("LinkedIn: creating post...")
    res = requests.post(f"{API_BASE}/posts", headers=headers, json=body)
    if res.status_code == 201:
        post_id = res.headers.get('x-restli-id', '<unknown>')
        print(f"LinkedIn: post published ({post_id}).")
        print(post_url(post_id))
    else:
        print(f"LinkedIn error {res.status_code}: {res.text}")
        sys.exit(1)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Publish a post to LinkedIn')
    parser.add_argument('--text', required=True, help='Post text (commentary)')
    parser.add_argument('--image', help='Path to an image file to attach')
    parser.add_argument('--visibility', default='PUBLIC', choices=['PUBLIC', 'CONNECTIONS'],
                        help='Post visibility (default: PUBLIC)')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                        help='Print the request payload instead of publishing')
    return parser.parse_args(argv)


def main():
    opts = parse_args()
    if opts.image and not os.path.isfile(opts.image):
        print(f"error: image file not found: {opts.image}", file=sys.stderr)
        sys.exit(1)
    publish_post(opts)


if __name__ == '__main__':
    main()
