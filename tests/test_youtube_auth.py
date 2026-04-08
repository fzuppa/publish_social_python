import os
import sys
import unittest.mock as mock
import pytest
from publish_social import get_authenticated_service


SAMPLE_YAML = (
    '---\n'
    'default: \'{"client_id":"test-client-id","client_secret":"test-client-secret",'
    '"access_token":"test-access-token","refresh_token":"test-refresh-token",'
    '"scope":["https://www.googleapis.com/auth/youtube"]}\'\n'
)

SAMPLE_CONFIG = '{"client_id": "test-client-id", "client_secret": "test-client-secret"}'


def test_get_authenticated_service_builds_credentials(tmp_path, monkeypatch):
    yaml_file = tmp_path / 'youtube-oauth2.yaml'
    yaml_file.write_text(SAMPLE_YAML)
    config_file = tmp_path / 'youtube_config.json'
    config_file.write_text(SAMPLE_CONFIG)

    monkeypatch.setattr('publish_social.TOKEN_PATH', str(yaml_file))
    monkeypatch.setattr('publish_social.YOUTUBE_CONFIG_FILE', str(config_file))

    with mock.patch('publish_social.build') as mock_build:
        mock_build.return_value = mock.MagicMock()
        service = get_authenticated_service()
        assert service is not None
        mock_build.assert_called_once()
        _, kwargs = mock_build.call_args
        creds = kwargs['credentials']
        assert creds.token == 'test-access-token'
        assert creds.refresh_token == 'test-refresh-token'
        assert creds.client_id == 'test-client-id'
        assert creds.client_secret == 'test-client-secret'


def test_get_authenticated_service_aborts_if_no_config(tmp_path, monkeypatch):
    monkeypatch.setattr('publish_social.YOUTUBE_CONFIG_FILE', str(tmp_path / 'missing.json'))
    with pytest.raises(SystemExit):
        get_authenticated_service()


def test_get_authenticated_service_aborts_if_no_token(tmp_path, monkeypatch):
    config_file = tmp_path / 'youtube_config.json'
    config_file.write_text(SAMPLE_CONFIG)
    monkeypatch.setattr('publish_social.YOUTUBE_CONFIG_FILE', str(config_file))
    monkeypatch.setattr('publish_social.TOKEN_PATH', str(tmp_path / 'missing.yaml'))
    with pytest.raises(SystemExit):
        get_authenticated_service()
