#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time

import requests
import urllib3
import yaml
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YOUTUBE_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'youtube_config.json')
TOKEN_PATH = os.path.join(SCRIPT_DIR, 'youtube-oauth2.yaml')
INSTAGRAM_TOKEN_PATH = os.path.join(SCRIPT_DIR, 'instagram_token.json')
LINKEDIN_TOKEN_PATH = os.path.join(SCRIPT_DIR, 'linkedin_token.json')


def get_authenticated_service():
    if not os.path.exists(YOUTUBE_CONFIG_FILE):
        sys.exit(f"YouTube config not found: {YOUTUBE_CONFIG_FILE}\n"
                 "Copy youtube_config.example.json and fill in your credentials.")
    if not os.path.exists(TOKEN_PATH):
        sys.exit("YouTube credentials not found. Run youtube_auth.rb first.")

    with open(YOUTUBE_CONFIG_FILE) as f:
        config = json.load(f)
    with open(TOKEN_PATH) as f:
        token_data = yaml.safe_load(f)

    node_raw = token_data.get('default') if token_data else None
    if node_raw is None:
        sys.exit(f"YouTube credentials file {TOKEN_PATH} is malformed (missing 'default' key). Re-run youtube_auth.rb.")
    node = json.loads(node_raw) if isinstance(node_raw, str) else node_raw
    credentials = Credentials(
        token=node['access_token'],
        refresh_token=node['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=config['client_id'],
        client_secret=config['client_secret'],
    )
    return build('youtube', 'v3', credentials=credentials)


def find_playlist_id(service, name):
    page_token = None
    while True:
        params = {'part': 'snippet', 'mine': True, 'maxResults': 50}
        if page_token:
            params['pageToken'] = page_token
        response = service.playlists().list(**params).execute()
        for p in response.get('items', []):
            if p['snippet']['title'] == name:
                return p['id']
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    return None


def add_to_playlist(service, video_id, playlist_id):
    service.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id,
                },
            }
        }
    ).execute()


def publish_youtube(opts):
    try:
        service = get_authenticated_service()
        body = {
            'snippet': {
                'title': opts.title,
                'description': opts.description,
                'tags': [k.strip() for k in opts.keywords.split(',') if k.strip()],
                'categoryId': str(opts.category_id),
            },
            'status': {
                'privacyStatus': opts.privacy_status,
                'selfDeclaredMadeForKids': False,
            },
        }
        media = MediaFileUpload(opts.file, mimetype='video/*', resumable=True)
        response = service.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media,
        ).execute()
        print(f"YouTube: video '{response['id']}' uploaded.")

        if opts.playlist:
            playlist_id = find_playlist_id(service, opts.playlist)
            if playlist_id:
                add_to_playlist(service, response['id'], playlist_id)
                print(f"YouTube: added to playlist '{opts.playlist}'.")
            else:
                print(f"YouTube warning: playlist '{opts.playlist}' not found.")
    except HttpError as e:
        print(f"YouTube error: {e}")


def publish_instagram(opts):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    with open(INSTAGRAM_TOKEN_PATH) as f:
        token_data = json.load(f)
    token = token_data['page_access_token']
    ig_id = token_data['instagram_account_id']
    caption = f"{opts.title}\n\n{opts.description}"

    # Step 1: create media container
    print("Instagram: creating media container...")
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{ig_id}/media",
        data={
            'media_type': 'REELS',
            'video_url': opts.video_url,
            'caption': caption,
            'access_token': token,
        },
        verify=False,
    )
    data = res.json()
    if 'error' in data:
        print(f"Instagram error: {data['error']['message']}")
        return
    container_id = data['id']
    print(f"Instagram: container {container_id} created, waiting for processing...")

    # Step 2: poll until ready
    finished = False
    for _ in range(30):
        time.sleep(5)
        status_res = requests.get(
            f"https://graph.facebook.com/v19.0/{container_id}",
            params={'fields': 'status_code', 'access_token': token},
            verify=False,
        )
        status_data = status_res.json()
        status_code = status_data.get('status_code')
        print(f"Instagram: status {status_code}...")
        if status_code == 'FINISHED':
            finished = True
            break
        if status_code == 'ERROR':
            print("Instagram error: video processing failed.")
            return

    if not finished:
        print("Instagram error: video processing timed out (container never reached FINISHED).")
        return

    # Step 3: publish
    pub_res = requests.post(
        f"https://graph.facebook.com/v19.0/{ig_id}/media_publish",
        data={'creation_id': container_id, 'access_token': token},
        verify=False,
    )
    pub_data = pub_res.json()
    if 'error' in pub_data:
        print(f"Instagram error: {pub_data['error']['message']}")
    else:
        print(f"Instagram: reel '{pub_data['id']}' published.")


def publish_linkedin(opts):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    with open(LINKEDIN_TOKEN_PATH) as f:
        token_data = json.load(f)
    token = token_data['access_token']
    member_id = token_data['member_id']
    author_urn = f"urn:li:person:{member_id}"
    headers = {
        'Authorization': f"Bearer {token}",
        'X-Restli-Protocol-Version': '2.0.0',
    }

    file_path = opts.file
    file_size = os.path.getsize(file_path)
    caption = f"{opts.title}\n\n{opts.description}"

    # Step 1: register upload
    print("LinkedIn: registering video upload...")
    register_res = requests.post(
        'https://api.linkedin.com/v2/assets?action=registerUpload',
        json={
            'registerUploadRequest': {
                'owner': author_urn,
                'recipes': ['urn:li:digitalmediaRecipe:feedshare-video'],
                'serviceRelationships': [{
                    'identifier': 'urn:li:userGeneratedContent',
                    'relationshipType': 'OWNER',
                }],
                'supportedUploadMechanism': ['SYNCHRONOUS_UPLOAD'],
            }
        },
        headers=headers,
        verify=False,
    )
    register_data = register_res.json()
    if register_data.get('status') and register_data['status'] != 200:
        print(f"LinkedIn error: {register_data['message']}")
        return

    upload_url = register_data['value']['uploadMechanism'][
        'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
    asset_urn = register_data['value']['asset']
    print(f"LinkedIn: asset URN {asset_urn}, uploading...")

    # Step 2: upload video (single PUT)
    print(f"LinkedIn: uploading video ({file_size} bytes)...")
    with open(file_path, 'rb') as f:
        requests.put(
            upload_url,
            data=f,
            headers={'Content-Type': 'application/octet-stream'},
            verify=False,
        )

    # Step 3: create UGC post
    print("LinkedIn: creating post...")
    post_res = requests.post(
        'https://api.linkedin.com/v2/ugcPosts',
        json={
            'author': author_urn,
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {'text': caption},
                    'shareMediaCategory': 'VIDEO',
                    'media': [{
                        'status': 'READY',
                        'media': asset_urn,
                        'title': {'text': opts.title},
                    }],
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC',
            },
        },
        headers=headers,
        verify=False,
    )
    if post_res.status_code == 201:
        print(f"LinkedIn: post published ({post_res.headers.get('x-restli-id')}).")
    else:
        print(f"LinkedIn error {post_res.status_code}: {post_res.text}")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Publish video to social platforms')
    parser.add_argument('--file', help='Local video file to upload')
    parser.add_argument('--video-url', dest='video_url', help='Public video URL (required for Instagram)')
    parser.add_argument('--title', default='Test Title', help='Video title')
    parser.add_argument('--description', default='', help='Video description')
    parser.add_argument('--category-id', dest='category_id', type=int, default=22,
                        help='Numeric video category (see YouTube API docs)')
    parser.add_argument('--keywords', default='', help='Video keywords, comma-separated')
    parser.add_argument('--privacy-status', dest='privacy_status', default='public',
                        help='Video privacy status: public, private, or unlisted')
    parser.add_argument('--playlist', help='YouTube playlist name to add the video to')
    parser.add_argument('--youtube', action='store_true', help='Publish to YouTube')
    parser.add_argument('--instagram', action='store_true', help='Publish to Instagram')
    parser.add_argument('--linkedin', action='store_true', help='Publish to LinkedIn')
    return parser.parse_args(argv)


def main():
    opts = parse_args()

    if not opts.youtube and not opts.instagram and not opts.linkedin:
        print("error: specify at least one platform: --youtube, --instagram, and/or --linkedin",
              file=sys.stderr)
        sys.exit(1)

    if opts.youtube:
        if not opts.file or not os.path.isfile(opts.file):
            print("error: --file is required and must exist for YouTube", file=sys.stderr)
            sys.exit(1)
        publish_youtube(opts)

    if opts.instagram:
        if not opts.video_url:
            print("error: --video-url is required for Instagram (must be a public URL)", file=sys.stderr)
            sys.exit(1)
        publish_instagram(opts)

    if opts.linkedin:
        if not opts.file or not os.path.isfile(opts.file):
            print("error: --file is required and must exist for LinkedIn", file=sys.stderr)
            sys.exit(1)
        publish_linkedin(opts)


if __name__ == '__main__':
    main()
