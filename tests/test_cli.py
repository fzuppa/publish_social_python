import pytest
from publish_social import parse_args


def test_defaults():
    args = parse_args(['--youtube', '--file', 'video.mp4'])
    assert args.title == 'Test Title'
    assert args.description == ''
    assert args.category_id == 22
    assert args.keywords == ''
    assert args.privacy_status == 'public'
    assert args.playlist is None
    assert args.youtube is True
    assert args.instagram is False
    assert args.linkedin is False


def test_all_flags():
    args = parse_args([
        '--youtube', '--instagram', '--linkedin',
        '--file', '/tmp/video.mp4',
        '--video-url', 'https://example.com/v.mp4',
        '--title', 'My Title',
        '--description', 'My Desc',
        '--category-id', '10',
        '--keywords', 'a,b,c',
        '--privacy-status', 'private',
        '--playlist', 'My Playlist',
    ])
    assert args.file == '/tmp/video.mp4'
    assert args.video_url == 'https://example.com/v.mp4'
    assert args.title == 'My Title'
    assert args.description == 'My Desc'
    assert args.category_id == 10
    assert args.keywords == 'a,b,c'
    assert args.privacy_status == 'private'
    assert args.playlist == 'My Playlist'
    assert args.youtube is True
    assert args.instagram is True
    assert args.linkedin is True
