#!/usr/bin/env python3
"""
MCP server that wraps publish_social.py.

Exposes a single tool, `publish_reel`, which forwards arguments to the
existing CLI script (publish_social.py) running inside this project's venv.

The server runs on stdio so it can be registered as a local MCP in
Claude Desktop / Cowork via claude_desktop_config.json.
"""

import os
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "publish_social.py")
VENV_PYTHON = os.path.join(SCRIPT_DIR, "venv", "bin", "python")

mcp = FastMCP("publish-social")


@mcp.tool()
def publish_reel(
    title: str,
    description: str = "",
    file: Optional[str] = None,
    video_url: Optional[str] = None,
    instagram: bool = True,
    linkedin: bool = True,
    youtube: bool = False,
    keywords: str = "",
    privacy_status: str = "public",
    playlist: Optional[str] = None,
) -> str:
    """Publish a reel/video to Instagram, LinkedIn and/or YouTube.

    Wraps publish_social.py. Use absolute paths for `file`. `video_url`
    must be a public URL (e.g. Dropbox dl=1) and is required for Instagram.
    `file` is required for LinkedIn and YouTube.

    Args:
        title: Video title.
        description: Video description / caption body.
        file: Absolute path to the local video file.
        video_url: Public URL to the video (Instagram only).
        instagram: Publish to Instagram.
        linkedin: Publish to LinkedIn.
        youtube: Publish to YouTube.
        keywords: Comma-separated keywords (YouTube).
        privacy_status: YouTube privacy: public, unlisted, or private.
        playlist: Optional YouTube playlist name to add the video to.

    Returns:
        Combined stdout/stderr and exit code from publish_social.py.
    """
    if not (instagram or linkedin or youtube):
        return "error: enable at least one of instagram/linkedin/youtube"

    if instagram and not video_url:
        return "error: video_url is required when instagram=True"
    if (linkedin or youtube) and not file:
        return "error: file is required when linkedin or youtube is True"
    if file and not os.path.isfile(file):
        return f"error: file not found: {file}"

    python = VENV_PYTHON if os.path.isfile(VENV_PYTHON) else "python3"
    args = [
        python,
        SCRIPT,
        "--title", title,
        "--description", description,
        "--privacy-status", privacy_status,
        "--keywords", keywords,
    ]
    if instagram:
        args += ["--instagram", "--video-url", video_url or ""]
    if linkedin:
        args += ["--linkedin"]
    if youtube:
        args += ["--youtube"]
    if file:
        args += ["--file", file]
    if playlist:
        args += ["--playlist", playlist]

    proc = subprocess.run(args, capture_output=True, text=True)
    return (
        f"exit_code: {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}"
    )


if __name__ == "__main__":
    mcp.run()
