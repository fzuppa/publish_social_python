import pytest
from linkedin_post import parse_args, post_url


def test_text_only():
    args = parse_args(['--text', 'Hello LinkedIn'])
    assert args.text == 'Hello LinkedIn'
    assert args.image is None
    assert args.visibility == 'PUBLIC'
    assert args.dry_run is False


def test_dry_run_flag():
    args = parse_args(['--text', 'Hello', '--dry-run'])
    assert args.dry_run is True


def test_post_url():
    assert post_url('urn:li:share:123') == 'https://www.linkedin.com/feed/update/urn:li:share:123/'


def test_with_image_and_visibility():
    args = parse_args(['--text', 'Hello', '--image', '/tmp/pic.jpg', '--visibility', 'CONNECTIONS'])
    assert args.image == '/tmp/pic.jpg'
    assert args.visibility == 'CONNECTIONS'


def test_text_required():
    with pytest.raises(SystemExit):
        parse_args(['--image', '/tmp/pic.jpg'])


def test_invalid_visibility():
    with pytest.raises(SystemExit):
        parse_args(['--text', 'Hello', '--visibility', 'PRIVATE'])
