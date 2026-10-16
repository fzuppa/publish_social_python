import pytest
from linkedin_post import escape_commentary, parse_args, post_url


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


def test_escape_reserved_chars():
    raw = '(a)[b]{c}<d>@e*f_g~h|i'
    expected = r'\(a\)\[b\]\{c\}\<d\>\@e\*f\_g\~h\|i'
    assert escape_commentary(raw) == expected


def test_escape_backslash_before_other_chars():
    # Literal backslash followed by a literal '(': the backslash must be
    # escaped first, or it would swallow the escaping of the '(' instead of
    # the other way around.
    raw = 'a\\(b'
    expected = 'a' + '\\' * 3 + '(b'
    assert escape_commentary(raw) == expected


def test_escape_leaves_plain_text_and_hashtags_untouched():
    raw = 'Hola comunidad, gracias! #agiles2026 #agilidad'
    assert escape_commentary(raw) == raw


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
