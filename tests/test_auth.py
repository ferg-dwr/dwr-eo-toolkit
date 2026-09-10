"""
Unit tests for EarthDataLoginAuth and related classes.

Tests cover:
- Credential provider priority chain
- Token caching and expiry
- .netrc file handling
- Environment variable reading
- Network request error handling
"""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dwr_eo_toolkit.core.auth import (
    AuthenticationError,
    EarthDataLoginAuth,
    EnvironmentProvider,
    NetrcProvider,
    TokenProvider,
)


class TestNetrcProvider:
    """Tests for .netrc credential provider."""

    def test_netrc_provider_finds_credentials(self):
        """Should read credentials from .netrc file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".netrc") as f:
            f.write("machine urs.earthdata.nasa.gov\n")
            f.write("login testuser\n")
            f.write("password testpass\n")
            netrc_path = f.name

        try:
            provider = NetrcProvider(netrc_path)
            creds = provider.get_credentials()

            assert creds == ("testuser", "testpass")
        finally:
            Path(netrc_path).unlink()

    def test_netrc_provider_returns_none_if_missing(self):
        """Should return None if .netrc doesn't exist."""
        provider = NetrcProvider("/nonexistent/path/.netrc")
        creds = provider.get_credentials()

        assert creds is None


class TestEnvironmentProvider:
    """Tests for environment variable credential provider."""

    def test_env_provider_finds_credentials(self):
        """Should read credentials from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "EARTHDATA_USERNAME": "envuser",
                "EARTHDATA_PASSWORD": "envpass",
            },
        ):
            provider = EnvironmentProvider()
            creds = provider.get_credentials()

            assert creds == ("envuser", "envpass")

    def test_env_provider_returns_none_if_missing(self):
        """Should return None if env vars not set."""
        with patch.dict("os.environ", {}, clear=True):
            provider = EnvironmentProvider()
            creds = provider.get_credentials()

            assert creds is None

    def test_env_provider_custom_var_names(self):
        """Should support custom environment variable names."""
        with patch.dict(
            "os.environ",
            {
                "MY_USER": "customuser",
                "MY_PASS": "custompass",
            },
        ):
            provider = EnvironmentProvider("MY_USER", "MY_PASS")
            creds = provider.get_credentials()

            assert creds == ("customuser", "custompass")


class TestTokenProvider:
    """Tests for pre-generated token provider."""

    def test_token_provider_gets_token(self):
        """Should read token from environment variable."""
        with patch.dict("os.environ", {"EARTHDATA_TOKEN": "mytoken123"}):
            provider = TokenProvider()
            token = provider.get_token()

            assert token == "mytoken123"

    def test_token_provider_returns_none_if_missing(self):
        """Should return None if token env var not set."""
        with patch.dict("os.environ", {}, clear=True):
            provider = TokenProvider()
            token = provider.get_token()

            assert token is None


class TestEarthDataLoginAuth:
    """Tests for main EarthDataLoginAuth class."""

    def test_initialization(self):
        """Should initialize with defaults."""
        auth = EarthDataLoginAuth()

        assert auth.token_cache_dir == Path.home() / ".nasa-eo-data"
        assert auth.EARTHDATA_LOGIN_HOST == "urs.earthdata.nasa.gov"
        assert auth._cached_token is None
        assert auth._token_expiry is None

    def test_custom_token_cache_dir(self):
        """Should respect custom cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = EarthDataLoginAuth(token_cache_dir=tmpdir)

            assert auth.token_cache_dir == Path(tmpdir)

    def test_get_token_from_env(self):
        """Should get token from EARTHDATA_TOKEN env var."""
        with patch.dict("os.environ", {"EARTHDATA_TOKEN": "envtoken"}):
            auth = EarthDataLoginAuth()
            token = auth.get_token()

            assert token == "envtoken"

    def test_credential_priority_order(self):
        """Should try credentials in correct priority order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock .netrc
            netrc_path = Path(tmpdir) / ".netrc"
            netrc_path.write_text(
                "machine urs.earthdata.nasa.gov\nlogin netrcuser\npassword netrcpass\n"
            )
            netrc_path.chmod(0o600)

            with patch.dict(
                "os.environ",
                {
                    "EARTHDATA_TOKEN": "tokenvalue",  # Highest priority
                    "EARTHDATA_USERNAME": "envuser",
                    "EARTHDATA_PASSWORD": "envpass",
                },
            ):
                auth = EarthDataLoginAuth(netrc_path=str(netrc_path))
                creds = auth._get_credentials()

                # Should get from .netrc (after env token check)
                # .netrc has higher priority than env vars
                assert creds == ("netrcuser", "netrcpass")

    def test_token_caching(self):
        """Should cache token in memory."""
        with patch.dict("os.environ", {"EARTHDATA_TOKEN": "cachedtoken"}):
            auth = EarthDataLoginAuth()

            # First call
            token1 = auth.get_token()
            # Second call should return cached value
            token2 = auth.get_token()

            assert token1 == token2
            assert auth._cached_token == "cachedtoken"

    def test_token_expiry(self):
        """Should respect token expiry."""
        with patch.dict("os.environ", {"EARTHDATA_TOKEN": "token1"}):
            auth = EarthDataLoginAuth()

            # First call
            token1 = auth.get_token()

            # Manually expire cache
            auth._token_expiry = datetime.now(UTC) - timedelta(seconds=1)

            with patch.dict("os.environ", {"EARTHDATA_TOKEN": "token2"}):
                # Second call should re-fetch (simulating token rotation)
                token2 = auth.get_token()

                assert token1 == "token1"
                assert token2 == "token2"

    def test_save_and_load_cached_token(self):
        """Should save and load token from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = EarthDataLoginAuth(token_cache_dir=tmpdir)

            # Save token
            auth._save_cached_token("testtoken123")

            # Load token
            loaded_token = auth._load_cached_token()

            assert loaded_token == "testtoken123"

    def test_cached_token_expiry(self):
        """Should not return expired cached tokens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = EarthDataLoginAuth(token_cache_dir=tmpdir)

            # Save old token
            cache_file = auth.token_cache_file
            cache_data = {
                "token": "oldtoken",
                "timestamp": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            }
            cache_file.write_text(json.dumps(cache_data))

            # Load should return None (expired)
            loaded = auth._load_cached_token()

            assert loaded is None

    @patch("dwr_eo_toolkit.core.auth.requests.post")
    def test_request_token_success(self, mock_post):
        """Should successfully request token."""
        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "newtoken"}
        mock_post.return_value = mock_response

        with patch.dict(
            "os.environ",
            {
                "EARTHDATA_USERNAME": "testuser",
                "EARTHDATA_PASSWORD": "testpass",
            },
        ):
            auth = EarthDataLoginAuth()
            token = auth._request_token()

            assert token == "newtoken"
            mock_post.assert_called_once()

    @patch("dwr_eo_toolkit.core.auth.requests.post")
    def test_request_token_failure(self, mock_post):
        """Should handle token request failure gracefully."""
        mock_post.side_effect = Exception("Network error")

        with patch.dict(
            "os.environ",
            {
                "EARTHDATA_USERNAME": "testuser",
                "EARTHDATA_PASSWORD": "testpass",
            },
        ):
            auth = EarthDataLoginAuth()
            token = auth._request_token()

            assert token is None

    def test_authentication_error_when_no_credentials(self):
        """Should raise AuthenticationError when no credentials available."""
        with patch.dict("os.environ", {}, clear=True):
            auth = EarthDataLoginAuth(netrc_path="/nonexistent/.netrc")

            with pytest.raises(AuthenticationError):
                auth.get_token()

    def test_setup_netrc(self):
        """Should create/update .netrc file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home_patch = patch.object(Path, "home", return_value=Path(tmpdir))

            with home_patch:
                auth = EarthDataLoginAuth()
                auth.setup_netrc("testuser", "testpass")

                netrc_path = Path(tmpdir) / ".netrc"
                assert netrc_path.exists()

                content = netrc_path.read_text()
                assert "testuser" in content
                assert "testpass" in content
                assert "urs.earthdata.nasa.gov" in content

    def test_clear_cache(self):
        """Should clear cached tokens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = EarthDataLoginAuth(token_cache_dir=tmpdir)

            # Cache a token
            auth._save_cached_token("token123")
            auth._cached_token = "token123"
            auth._token_expiry = datetime.now(UTC) + timedelta(hours=1)

            # Clear
            auth.clear_cache()

            assert auth._cached_token is None
            assert auth._token_expiry is None
            assert not auth.token_cache_file.exists()


class TestAuthCoverageExtra:
    """Cover auth.py lines 207-209, 223-226, 291-292, 304, 310-311, 328,
    356-364, 373-374."""

    def test_get_token_uses_pre_generated_token(self, tmp_path):
        """get_token returns env token when token_provider gives a string (lines 207-209)."""
        auth = EarthDataLoginAuth()
        auth._cached_token = None
        auth._token_expiry = None
        auth.token_cache_file = tmp_path / "cache.json"

        with patch.object(auth.token_provider, "get_credentials", return_value="pre_generated_tok"):
            token = auth.get_token()

        assert token == "pre_generated_tok"

    def test_get_token_requests_and_caches_new_token(self, tmp_path):
        """get_token calls _request_token and caches result (lines 223-226)."""
        auth = EarthDataLoginAuth()
        auth._cached_token = None
        auth._token_expiry = None
        auth.token_cache_file = tmp_path / "cache.json"

        with patch.object(auth.token_provider, "get_credentials", return_value=None):
            with patch.object(auth, "_request_token", return_value="new_token"):
                with patch.object(auth, "_save_cached_token") as mock_save:
                    token = auth.get_token()

        assert token == "new_token"
        mock_save.assert_called_once_with("new_token")

    def test_get_credentials_falls_back_to_env_provider(self):
        """_get_credentials falls back to env when netrc returns None (lines 291-292)."""
        auth = EarthDataLoginAuth()

        with patch.object(auth.netrc_provider, "get_credentials", return_value=None):
            with patch.object(
                auth.env_provider,
                "get_credentials",
                return_value=("envuser", "envpass"),
            ):
                creds = auth._get_credentials()

        assert creds == ("envuser", "envpass")

    def test_load_cached_token_returns_none_when_file_missing(self, tmp_path):
        """_load_cached_token returns None when cache file doesn't exist (line 304)."""
        auth = EarthDataLoginAuth()
        auth.token_cache_file = tmp_path / "no_cache.json"
        result = auth._load_cached_token()
        assert result is None

    def test_load_cached_token_handles_corrupt_file(self, tmp_path):
        """_load_cached_token returns None on malformed JSON (lines 310-311)."""
        auth = EarthDataLoginAuth()
        cache = tmp_path / "bad_cache.json"
        cache.write_text("{{invalid")
        auth.token_cache_file = cache
        result = auth._load_cached_token()
        assert result is None

    def test_setup_netrc_writes_credentials(self, tmp_path):
        """setup_netrc creates/updates .netrc file (line 328 area)."""
        auth = EarthDataLoginAuth()
        netrc_path = tmp_path / ".netrc"

        with patch("dwr_eo_toolkit.core.auth.Path.home", return_value=tmp_path):
            auth.setup_netrc("myuser", "mypass")

        assert netrc_path.exists()
        content = netrc_path.read_text()
        assert "myuser" in content
        assert "mypass" in content

    def test_setup_environment_prints_commands_with_token(self, capsys):
        """setup_environment prints export commands including token (lines 356-364)."""
        auth = EarthDataLoginAuth()
        auth.setup_environment("user1", "pass1", token="mytoken")
        out = capsys.readouterr().out
        assert "EARTHDATA_USERNAME=user1" in out
        assert "EARTHDATA_TOKEN=mytoken" in out

    def test_setup_environment_prints_commands_without_token(self, capsys):
        """setup_environment prints commands without token when not supplied."""
        auth = EarthDataLoginAuth()
        auth.setup_environment("user1", "pass1")
        out = capsys.readouterr().out
        assert "EARTHDATA_USERNAME=user1" in out
        assert "EARTHDATA_TOKEN" not in out

    def test_clear_cache_handles_unlink_error(self, tmp_path):
        """clear_cache swallows errors when deleting cache file (lines 373-374)."""
        auth = EarthDataLoginAuth()
        auth.token_cache_file = tmp_path / "cache.json"
        auth.token_cache_file.write_text('{"token":"t","timestamp":"2024-01-01T00:00:00+00:00"}')

        with patch.object(Path, "unlink", side_effect=OSError("locked")):
            auth.clear_cache()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
