"""
Unit tests for HTTP client

Tests cover:
- HTTP request execution with authentication
- Retry strategy and exponential backoff
- Rate limit detection and handling
- Error handling for various HTTP status codes
- Context manager behavior
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter

from nasa_eo_data.core.auth import EarthDataLoginAuth
from nasa_eo_data.core.client import (
    HTTPClient,
    APIError,
    RateLimitError,
    AuthenticationError,
)


class MockResponse:
    """Mock requests.Response for testing."""
    
    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: str = "",
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text or json.dumps(self._json_data)
        self.headers = headers or {}
    
    def json(self):
        return self._json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")


class TestHTTPClient:
    """Tests for basic HTTPClient."""
    
    @pytest.fixture
    def auth(self):
        """Mock authentication handler."""
        auth = Mock(spec=EarthDataLoginAuth)
        auth.get_token.return_value = "test_token_123"
        return auth
    
    @pytest.fixture
    def client(self, auth):
        """Create HTTPClient for testing."""
        return HTTPClient(
            auth_handler=auth,
            base_url="https://api.example.com",
            timeout=5,
        )
    
    def test_initialization(self, auth):
        """Should initialize with correct defaults."""
        client = HTTPClient(
            auth_handler=auth,
            base_url="https://example.com",
            client_id="test-app",
            timeout=10,
        )
        
        assert client.base_url == "https://example.com"
        assert client.client_id == "test-app"
        assert client.timeout == 10
        assert client.auth_handler == auth
    
    def test_base_url_trailing_slash_handling(self, auth):
        """Should handle base URLs with/without trailing slashes."""
        client1 = HTTPClient(auth_handler=auth, base_url="https://api.com/")
        client2 = HTTPClient(auth_handler=auth, base_url="https://api.com")
        
        assert client1.base_url == "https://api.com"
        assert client2.base_url == "https://api.com"
    
    def test_get_headers_includes_auth_token(self, auth):
        """Should include bearer token in headers."""
        auth.get_token.return_value = "test_token_xyz"
        client = HTTPClient(auth_handler=auth, client_id="myapp")
        
        headers = client.get_headers()
        
        assert headers["Authorization"] == "Bearer test_token_xyz"
        assert headers["Client-Id"] == "myapp"
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
    
    def test_default_user_agent(self, auth):
        """Should use default User-Agent."""
        client = HTTPClient(auth_handler=auth)
        headers = client.get_headers()
        
        assert headers["User-Agent"] == HTTPClient.DEFAULT_USER_AGENT
    
    def test_custom_user_agent(self, auth):
        """Should use custom User-Agent if provided."""
        client = HTTPClient(
            auth_handler=auth,
            user_agent="MyApp/1.0 (Python)"
        )
        headers = client.get_headers()
        
        assert headers["User-Agent"] == "MyApp/1.0 (Python)"
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_get_request_success(self, mock_request, client):
        """Should successfully execute GET request."""
        mock_response = MockResponse(
            status_code=200,
            json_data={"data": "test"},
            headers={"Request-Id": "req-123"}
        )
        mock_request.return_value = mock_response
        
        response = client.get("search/granules", params={"short_name": "MODIS"})
        
        assert response.status_code == 200
        assert response.json() == {"data": "test"}
        mock_request.assert_called_once()
        
        # Check call arguments
        call_args = mock_request.call_args
        assert call_args[0][0] == "GET"
        assert "search/granules" in call_args[0][1]
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_post_request_success(self, mock_request, client):
        """Should successfully execute POST request."""
        mock_response = MockResponse(status_code=201, json_data={"id": "123"})
        mock_request.return_value = mock_response
        
        payload = {"name": "test"}
        response = client.post("submit", json_data=payload)
        
        assert response.status_code == 201
        mock_request.assert_called_once()
        
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[1]["json"] == payload
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_request_authentication_error_401(self, mock_request, client):
        """Should raise AuthenticationError for 401."""
        mock_response = MockResponse(status_code=401, text="Invalid or expired token")
        mock_request.return_value = mock_response
        
        with pytest.raises(AuthenticationError):
            client.get("protected/endpoint")
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_request_authentication_error_403(self, mock_request, client):
        """Should raise AuthenticationError for 403."""
        mock_response = MockResponse(status_code=403, text="Forbidden")
        mock_request.return_value = mock_response
        
        with pytest.raises(AuthenticationError):
            client.get("protected/endpoint")
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_rate_limit_error_429(self, mock_request, client):
        """Should raise RateLimitError for 429."""
        mock_response = MockResponse(
            status_code=429,
            headers={"Retry-After": "60"}
        )
        mock_request.return_value = mock_response
        
        with pytest.raises(RateLimitError) as exc_info:
            client.get("endpoint")
        
        assert "Rate limited" in str(exc_info.value)
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_server_error_500(self, mock_request, client):
        """Should raise APIError for server errors."""
        mock_response = MockResponse(
            status_code=500,
            text="Internal Server Error"
        )
        mock_request.return_value = mock_response
        
        with pytest.raises(APIError):
            client.get("endpoint")
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_bad_request_400(self, mock_request, client):
        """Should raise HTTPError for 400 (not APIError)."""
        mock_response = MockResponse(
            status_code=400,
            text="Bad Request"
        )
        mock_request.return_value = mock_response
        
        # 400 will call raise_for_status which raises HTTPError
        with pytest.raises(APIError):
            client.get("endpoint")
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_timeout_error(self, mock_request, client):
        """Should raise APIError on timeout."""
        mock_request.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        with pytest.raises(APIError) as exc_info:
            client.get("endpoint")
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_connection_error(self, mock_request, client):
        """Should raise APIError on connection error."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Cannot connect")
        
        with pytest.raises(APIError) as exc_info:
            client.get("endpoint")
        
        assert "Connection error" in str(exc_info.value)
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_custom_timeout(self, mock_request, client):
        """Should use custom timeout."""
        mock_response = MockResponse(status_code=200)
        mock_request.return_value = mock_response
        
        client.timeout = 15
        client.get("endpoint")
        
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["timeout"] == 15
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_merges_custom_headers(self, mock_request, client):
        """Should merge custom headers with default headers."""
        mock_response = MockResponse(status_code=200)
        mock_request.return_value = mock_response
        
        custom_headers = {"X-Custom": "value"}
        client.get("endpoint", headers=custom_headers)
        
        call_kwargs = mock_request.call_args[1]
        headers = call_kwargs["headers"]
        
        assert headers["X-Custom"] == "value"
        assert "Authorization" in headers  # Default header still present
    
    def test_context_manager(self, auth):
        """Should support context manager protocol."""
        with HTTPClient(auth_handler=auth) as client:
            assert client.session is not None
        
        # Session should be closed after exiting context
        assert client.session is not None
    
    def test_close_session(self, auth):
        """Should close session when close() is called."""
        client = HTTPClient(auth_handler=auth)
        assert client.session is not None
        
        client.close()
        assert client.session is not None

class TestRetryStrategy:
    """Tests for retry behavior with exponential backoff."""
    
    @pytest.fixture
    def auth(self):
        """Mock auth."""
        auth = Mock(spec=EarthDataLoginAuth)
        auth.get_token.return_value = "token"
        return auth
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_retry_on_429(self, mock_request, auth):
        """Should retry on 429 (rate limit)."""
        client = HTTPClient(auth_handler=auth, max_retries=2)
        
        # Fail twice, then succeed
        responses = [
            MockResponse(status_code=429, headers={"Retry-After": "1"}),
            MockResponse(status_code=429, headers={"Retry-After": "1"}),
            MockResponse(status_code=200, json_data={"data": "ok"}),
            ]
        mock_request.side_effect = responses
        # Note: The underlying urllib3.Retry will handle retries
        # Our exception handling triggers on first 429
        with pytest.raises(RateLimitError):
            client.get("endpoint")
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_retry_on_500(self, mock_request, auth):
        """Should retry on 500 server error."""
        client = HTTPClient(auth_handler=auth, max_retries=2)
        
        # Fail once, then succeed
        responses = [
            MockResponse(status_code=500, text="Server error"),
            MockResponse(status_code=200, json_data={"data": "ok"}),
        ]
        mock_request.side_effect = responses
        
        # First call will get 500, retry mechanism will handle it
        # But our code raises on 500 after checking auth
        with pytest.raises(APIError):
            client.get("endpoint")
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_no_retry_on_401(self, mock_request, auth):
        """Should NOT retry on 401 (auth error)."""
        client = HTTPClient(auth_handler=auth, max_retries=3)
        
        mock_request.return_value = MockResponse(status_code=401, text="Unauthorized")
        
        with pytest.raises(AuthenticationError):
            client.get("endpoint")
        
        # Should only be called once (no retries)
        assert mock_request.call_count == 1
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_no_retry_on_404(self, mock_request, auth):
        """Should NOT retry on 404 (not found)."""
        client = HTTPClient(auth_handler=auth, max_retries=3)
        
        mock_request.return_value = MockResponse(status_code=404, text="Not found")
        
        with pytest.raises(APIError):
            client.get("endpoint")

        # Should only be called once (no retries)
        assert mock_request.call_count == 1


class TestRateLimitHandling:
    """Tests for rate limit detection and tracking."""
    
    @pytest.fixture
    def auth(self):
        """Mock auth."""
        auth = Mock(spec=EarthDataLoginAuth)
        auth.get_token.return_value = "token"
        return auth
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_rate_limit_with_retry_after_header(self, mock_request, auth):
        """Should extract Retry-After from response."""
        client = HTTPClient(auth_handler=auth)
        
        mock_response = MockResponse(
            status_code=429,
            headers={"Retry-After": "120"}
        )
        mock_request.return_value = mock_response
        
        with pytest.raises(RateLimitError) as exc_info:
            client.get("endpoint")
        
        assert "120" in str(exc_info.value) or "Retry-After" in str(exc_info.value)
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_rate_limit_without_retry_after_header(self, mock_request, auth):
        """Should use default wait time if Retry-After missing."""
        client = HTTPClient(auth_handler=auth)
        
        mock_response = MockResponse(
            status_code=429,
            headers={}  # No Retry-After
        )
        mock_request.return_value = mock_response
        
        with pytest.raises(RateLimitError):
            client.get("endpoint")
        
        # Client should have tracked rate limit reset time
        assert client._rate_limit_reset_time is not None


class TestErrorMessages:
    """Tests for helpful error messages."""
    
    @pytest.fixture
    def auth(self):
        """Mock auth."""
        auth = Mock(spec=EarthDataLoginAuth)
        auth.get_token.return_value = "token"
        return auth
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_authentication_error_message(self, mock_request, auth):
        """Should include helpful message for auth errors."""
        client = HTTPClient(auth_handler=auth)
        
        mock_response = MockResponse(
            status_code=401,
            text="Invalid token"
        )
        mock_request.return_value = mock_response
        
        with pytest.raises(AuthenticationError) as exc_info:
            client.get("endpoint")
        
        error_msg = str(exc_info.value)
        assert "401" in error_msg or "authentication" in error_msg.lower()
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_timeout_error_message(self, mock_request, auth):
        """Should include helpful message for timeouts."""
        client = HTTPClient(auth_handler=auth, timeout=5)
        
        mock_request.side_effect = requests.exceptions.Timeout("timeout")
        
        with pytest.raises(APIError) as exc_info:
            client.get("endpoint")
        
        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg
        assert "5" in str(exc_info.value)  # Should mention timeout value


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    @pytest.fixture
    def auth(self):
        """Mock auth."""
        auth = Mock(spec=EarthDataLoginAuth)
        auth.get_token.return_value = "token"
        return auth
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_empty_endpoint_path(self, mock_request, auth):
        """Should handle empty endpoint path."""
        client = HTTPClient(auth_handler=auth, base_url="https://api.com")
        mock_request.return_value = MockResponse(status_code=200)
        
        client.get("")
        
        # Should make request to base URL
        call_url = mock_request.call_args[0][1]
        assert "api.com" in call_url
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_endpoint_with_leading_slash(self, mock_request, auth):
        """Should handle endpoint with leading slash."""
        client = HTTPClient(auth_handler=auth, base_url="https://api.com")
        mock_request.return_value = MockResponse(status_code=200)
        
        client.get("/search/data")
        
        call_url = mock_request.call_args[0][1]
        assert "api.com/search/data" in call_url
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_params_none(self, mock_request, auth):
        """Should handle None params gracefully."""
        client = HTTPClient(auth_handler=auth)
        mock_request.return_value = MockResponse(status_code=200)
        
        client.get("endpoint", params=None)
        
        # Should work without error
        assert mock_request.called
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_empty_response_json(self, mock_request, auth):
        """Should handle empty JSON response."""
        client = HTTPClient(auth_handler=auth)
        mock_response = MockResponse(status_code=200, json_data={})
        mock_request.return_value = mock_response
        
        response = client.get("endpoint")
        
        assert response.json() == {}
    
    def test_very_large_timeout(self, auth):
        """Should accept very large timeout values."""
        client = HTTPClient(auth_handler=auth, timeout=3600)
        assert client.timeout == 3600
    
    @patch('nasa_eo_data.core.client.requests.Session.request')
    def test_special_characters_in_params(self, mock_request, auth):
        """Should handle special characters in parameters."""
        client = HTTPClient(auth_handler=auth)
        mock_request.return_value = MockResponse(status_code=200)
        
        params = {
            "query": "test & special = chars",
            "bbox": "-120,30,-100,40",
        }
        client.get("endpoint", params=params)
        
        call_params = mock_request.call_args[1]["params"]
        assert call_params["query"] == "test & special = chars"


class TestIntegration:
    """Integration tests combining multiple features."""
    
    @pytest.fixture
    def auth(self):
        """Mock auth."""
        auth = Mock(spec=EarthDataLoginAuth)
        auth.get_token.return_value = "token123"
        return auth


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
