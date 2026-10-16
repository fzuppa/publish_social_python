# publish_social_python

Command-line scripts to publish videos (reels) and LinkedIn posts to YouTube, Instagram and LinkedIn, plus an MCP server that exposes the video publisher as a tool for Claude Desktop / Cowork.

## Scripts

| Script | What it does |
|---|---|
| [`publish_social.py`](publish_social.py) | Uploads a video to YouTube, Instagram Reels and/or LinkedIn in one command. |
| [`linkedin_post.py`](linkedin_post.py) | Publishes a text post (optionally with one image) to LinkedIn, via the modern Posts API. |
| [`linkedin_auth.py`](linkedin_auth.py) | One-time (~every 60 days) OAuth flow that creates/renews `linkedin_token.json`, used by both LinkedIn scripts above. |
| [`publish_social_mcp.py`](publish_social_mcp.py) | MCP server wrapping `publish_social.py` as a single `publish_reel` tool. |

## Setup

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Credentials

Each platform needs its own credentials file in the project root. None of these are committed — they're all listed in [`.gitignore`](.gitignore) — so you need to create them yourself.

### YouTube

1. In Google Cloud Console, create an OAuth client of type "Desktop app" with the YouTube Data API v3 enabled.
2. Copy [`youtube_config.example.json`](youtube_config.example.json) to `youtube_config.json` and fill in `client_id` / `client_secret`.
3. Generate `youtube-oauth2.yaml` with your own OAuth helper for the YouTube API (`publish_social.py` only reads this file — it doesn't do the authorization flow itself). It must contain a `default` key holding a JSON string with `client_id`, `access_token`, `refresh_token`, `scope` and `expiration_time_millis`; the access token is refreshed automatically from the refresh token on every run.

### Instagram

1. In Meta for Developers, get a long-lived **Page** access token for the Facebook Page linked to your Instagram professional account, with the `instagram_basic` and `instagram_content_publish` scopes.
2. Copy [`instagram_token.example.json`](instagram_token.example.json) to `instagram_token.json` and fill in `page_access_token` and `instagram_account_id` (the Instagram Business Account ID behind that page).
3. This token does not need periodic renewal.

Instagram's API fetches the video itself, so publishing to Instagram always needs a **public** URL (`--video-url`), not a local file.

### LinkedIn

1. In the LinkedIn Developer Portal, create an app with the `w_member_social` scope (add `openid` and `profile` too) and `http://localhost:8080/callback` as an authorized redirect URL.
2. Copy [`linkedin_config.example.json`](linkedin_config.example.json) to `linkedin_config.json` and fill in `client_id` / `client_secret`.
3. Run the authorization flow:
   ```bash
   venv/bin/python linkedin_auth.py
   ```
   This prints a URL — open it, log in and authorize the app. The script catches the redirect on `localhost:8080` and writes `linkedin_token.json`.
4. LinkedIn access tokens for this app expire after ~60 days and LinkedIn doesn't issue a refresh token for this grant type, so re-run step 3 whenever `publish_social.py` or `linkedin_post.py` fail with an expired/invalid token error.

## Usage

### Publish a video (reel)

```bash
venv/bin/python publish_social.py --instagram --linkedin --youtube \
  --file /path/to/video.mp4 \
  --video-url "https://your-public-url/video.mp4" \
  --title "My reel" \
  --description "Description" \
  --keywords "tag1,tag2" \
  --privacy-status public \
  --playlist "My playlist"
```

- `--youtube` / `--instagram` / `--linkedin`: which platforms to publish to (at least one).
- `--file`: local video file, required for YouTube and LinkedIn.
- `--video-url`: public video URL, required for Instagram.
- `--title`, `--description`, `--keywords` (comma-separated): shared across platforms.
- `--privacy-status` (`public`/`private`/`unlisted`), `--category-id`, `--playlist`: YouTube-only.

### Publish a LinkedIn text/image post

```bash
venv/bin/python linkedin_post.py --text "Hello LinkedIn" \
  [--image photo.jpg] \
  [--visibility PUBLIC|CONNECTIONS] \
  [--dry-run]
```

- `--text` is the post body (required). Characters LinkedIn's markup reserves (`\ ( ) [ ] { } < > @ * _ ~ |`) are escaped automatically, so they appear literally instead of breaking the post's rendering.
- `--image` attaches a single local image.
- `--dry-run` prints the exact request payload — without uploading the image or publishing anything — so you can check it before a post goes live.

### MCP server

Register `publish_social_mcp.py` so an MCP-aware client (Claude Desktop, Cowork, etc.) can call `publish_reel` directly, e.g. in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "publish-social": {
      "command": "/absolute/path/to/publish_social_python/venv/bin/python",
      "args": ["/absolute/path/to/publish_social_python/publish_social_mcp.py"]
    }
  }
}
```

The tool takes the same parameters as `publish_social.py` (`title`, `description`, `file`, `video_url`, `instagram`, `linkedin`, `youtube`, `keywords`, `privacy_status`, `playlist`) and returns the wrapped script's stdout/stderr and exit code.

## Tests

```bash
venv/bin/python -m pytest
```

## Security notes

- Never commit `*_token.json`, `*_config.json` or `youtube-oauth2.yaml` — they hold real credentials and are already excluded via `.gitignore`.
- All requests to the YouTube, Instagram and LinkedIn APIs go over HTTPS with TLS certificate verification enabled (the default `requests` behavior).
