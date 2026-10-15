import pytest
from linkedin_post import parse_args


def test_text_only():
    args = parse_args(['--text', 'Hello LinkedIn'])
    assert args.text == 'Hello LinkedIn'
    assert args.image is None
    assert args.visibility == 'PUBLIC'


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
