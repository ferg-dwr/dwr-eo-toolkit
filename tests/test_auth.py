"""
Unit tests for EarthDataLoginAuth and related classes.

Tests cover:
- Credential provider priority chain
- Token caching and expiry
- .netrc file handling
- Environment variable reading
- Network request error handling
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from nasa_eo_data.core.auth import (
    EarthDataLoginAuth,
    NetrcProvider,
    EnvironmentProvider,
    TokenProvider,
    AuthenticationError,
)


class TestNetrcProvider:
    """Tests for .netrc credential provider."""
    
    def test_netrc_provider_finds_credentials(self):
        """Should read credentials from .netrc file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.netrc') as f:
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
        with patch.dict('os.environ', {
            'EARTHDATA_USERNAME': 'envuser',
            'EARTHDATA_PASSWORD': 'envpass',
        }):
            provider = EnvironmentProvider()
            creds = provider.get_credentials()
            
            assert creds == ("envuser", "envpass")
    
    def test_env_provider_returns_none_if_missing(self):
        """Should return None if env vars not set."""
        with patch.dict('os.environ', {}, clear=True):
            provider = EnvironmentProvider()
            creds = provider.get_credentials()
            
            assert creds is None
    
    def test_env_provider_custom_var_names(self):
        """Should support custom environment variable names."""
        with patch.dict('os.environ', {
            'MY_USER': 'customuser',
            'MY_PASS': 'custompass',
        }):
            provider = EnvironmentProvider('MY_USER', 'MY_PASS')
            creds = provider.get_credentials()
            
            assert creds == ("customuser", "custompass")


class TestTokenProvider:
    """Tests for pre-generated token provider."""
    
    def test_token_provider_gets_token(self):
        """Should read token from environment variable."""
        with patch.dict('os.environ', {'EARTHDATA_TOKEN': 'mytoken123'}):
            provider = TokenProvider()
            token = provider.get_token()
            
            assert token == 'mytoken123'
    
    def test_token_provider_returns_none_if_missing(self):
        """Should return None if token env var not set."""
        with patch.dict('os.environ', {}, clear=True):
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
    
    def test_get_bearer_token_from_env(self):
        """Should get token from EARTHDATA_TOKEN env var."""
        with patch.dict('os.environ', {'EARTHDATA_TOKEN': 'envtoken'}):
            auth = EarthDataLoginAuth()
            token = auth.get_bearer_token()
            
            assert token == 'envtoken'
    
    def test_credential_priority_order(self):
        """Should try credentials in correct priority order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock .netrc
            netrc_path = Path(tmpdir) / ".netrc"
            netrc_path.write_text(
                "machine urs.earthdata.nasa.gov\n"
                "login netrcuser\n"
                "password netrcpass\n"
            )
            netrc_path.chmod(0o600)
            
            with patch.dict('os.environ', {
                'EARTHDATA_TOKEN': 'tokenvalue',  # Highest priority
                'EARTHDATA_USERNAME': 'envuser',
                'EARTHDATA_PASSWORD': 'envpass',
            }):
                auth = EarthDataLoginAuth(netrc_path=str(netrc_path))
                creds = auth._get_credentials()
                
                # Should get from .netrc (after env token check)
                # .netrc has higher priority than env vars
                assert creds == ("netrcuser", "netrcpass")
    
    def test_token_caching(self):
        """Should cache token in memory."""
        with patch.dict('os.environ', {'EARTHDATA_TOKEN': 'cachedtoken'}):
            auth = EarthDataLoginAuth()
            
            # First call
            token1 = auth.get_bearer_token()
            # Second call should return cached value
            token2 = auth.get_bearer_token()
            
            assert token1 == token2
            assert auth._cached_token == 'cachedtoken'
    
    def test_token_expiry(self):
        """Should respect token expiry."""
        with patch.dict('os.environ', {'EARTHDATA_TOKEN': 'token1'}):
            auth = EarthDataLoginAuth()
            
            # First call
            token1 = auth.get_bearer_token()
            
            # Manually expire cache
            auth._token_expiry = datetime.utcnow() - timedelta(seconds=1)
            
            with patch.dict('os.environ', {'EARTHDATA_TOKEN': 'token2'}):
                # Second call should re-fetch (simulating token rotation)
                token2 = auth.get_bearer_token()
                
                assert token1 == 'token1'
                assert token2 == 'token2'
    
    def test_save_and_load_cached_token(self):
        """Should save and load token from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = EarthDataLoginAuth(token_cache_dir=tmpdir)
            
            # Save token
            auth._save_cached_token('testtoken123')
            
            # Load token
            loaded_token = auth._load_cached_token()
            
            assert loaded_token == 'testtoken123'
    
    def test_cached_token_expiry(self):
        """Should not return expired cached tokens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = EarthDataLoginAuth(token_cache_dir=tmpdir)
            
            # Save old token
            cache_file = auth.token_cache_file
            cache_data = {
                'token': 'oldtoken',
                'timestamp': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            }
            cache_file.write_text(json.dumps(cache_data))
            
            # Load should return None (expired)
            loaded = auth._load_cached_token()
            
            assert loaded is None
    
    @patch('nasa_eo_data.core.auth.requests.post')
    def test_request_token_success(self, mock_post):
        """Should successfully request token."""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'newtoken'}
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {
            'EARTHDATA_USERNAME': 'testuser',
            'EARTHDATA_PASSWORD': 'testpass',
        }):
            auth = EarthDataLoginAuth()
            token = auth._request_token()
            
            assert token == 'newtoken'
            mock_post.assert_called_once()
    
    @patch('nasa_eo_data.core.auth.requests.post')
    def test_request_token_failure(self, mock_post):
        """Should handle token request failure gracefully."""
        mock_post.side_effect = Exception("Network error")
        
        with patch.dict('os.environ', {
            'EARTHDATA_USERNAME': 'testuser',
            'EARTHDATA_PASSWORD': 'testpass',
        }):
            auth = EarthDataLoginAuth()
            token = auth._request_token()
            
            assert token is None
    
    def test_authentication_error_when_no_credentials(self):
        """Should raise AuthenticationError when no credentials available."""
        with patch.dict('os.environ', {}, clear=True):
            auth = EarthDataLoginAuth(netrc_path='/nonexistent/.netrc')
            
            with pytest.raises(AuthenticationError):
                auth.get_bearer_token()
    
    def test_setup_netrc(self):
        """Should create/update .netrc file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home_patch = patch.object(Path, 'home', return_value=Path(tmpdir))
            
            with home_patch:
                auth = EarthDataLoginAuth()
                auth.setup_netrc('testuser', 'testpass')
                
                netrc_path = Path(tmpdir) / ".netrc"
                assert netrc_path.exists()
                
                content = netrc_path.read_text()
                assert 'testuser' in content
                assert 'testpass' in content
                assert 'urs.earthdata.nasa.gov' in content
    
    def test_clear_cache(self):
        """Should clear cached tokens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = EarthDataLoginAuth(token_cache_dir=tmpdir)
            
            # Cache a token
            auth._save_cached_token('token123')
            auth._cached_token = 'token123'
            auth._token_expiry = datetime.utcnow() + timedelta(hours=1)
            
            # Clear
            auth.clear_cache()
            
            assert auth._cached_token is None
            assert auth._token_expiry is None
            assert not auth.token_cache_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
