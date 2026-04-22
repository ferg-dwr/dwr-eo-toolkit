"""
Base HTTP client for EO API requests
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import AuthenticationError
from .exceptions import APIError

logger = logging.getLogger(__name__)


class RateLimitError(APIError):
    """Raised when rate limited (HTTP 429)."""

    pass


class HTTPClient:
    """
    Base HTTP client for NASA APIs with:
    - EDL bearer token authentication
    - Exponential backoff retry strategy
    - Rate limit handling
    - CMR-specific headers and pagination
    - Request/response logging

    References:
    - CMR Client Partner User Guide:
      https://wiki.earthdata.nasa.gov/display/CMR/CMR+Client+Partner+User+Guide
    """

    # Default User-Agent for NASA requests
    DEFAULT_USER_AGENT = "nasa-eo-data/1.0 (Python)"

    # CMR Request ID header (helps NASA debug)
    CMR_REQUEST_ID_HEADER = "CMR-Request-Id"

    # Client ID header (recommended by CMR Client Partner Guide)
    CLIENT_ID_HEADER = "Client-Id"

    def __init__(
        self,
        auth_handler,
        base_url: str = "https://data.earthdata.nasa.gov",
        client_id: str = "nasa-eo-data",
        user_agent: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        verify_ssl: Optional[bool] = None,
    ):
        """
        Initialize HTTP client.

        Args:
            auth_handler: EarthDataLoginAuth instance for token management
            base_url: Base URL for API requests
            client_id: Client ID for NASA metrics tracking
            user_agent: Custom User-Agent header
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            backoff_factor: Exponential backoff multiplier
            verify_ssl: Whether to verify SSL certificates.
                    If None, defaults to False for corporate proxy compatibility.
                    Set to True for public networks where security is critical.

                    Examples:
                        verify_ssl=False  # Corporate proxy (default)
                        verify_ssl=True   # Public network
                        verify_ssl="/path/to/ca-bundle.crt"  # Custom CA bundle
        """
        self.auth_handler = auth_handler
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout

        # Handle SSL verification setting
        if verify_ssl is None:
            # Auto-detect: Assume corporate environment by default
            # Users can override if needed
            self.verify_ssl = False
            logger.debug("SSL verification disabled (corporate proxy mode)")
        else:
            self.verify_ssl = verify_ssl
            if verify_ssl is False:
                logger.warning("SSL verification is disabled - only use in trusted networks")
            else:
                logger.debug(f"SSL verification enabled: {verify_ssl}")

        # Set up session with retry strategy
        self.session = requests.Session()
        self._configure_retries(max_retries, backoff_factor)

        # Track rate limiting
        self._rate_limit_reset_time: Optional[float] = None

    def _configure_retries(self, max_retries: int, backoff_factor: float) -> None:
        """
        Configure exponential backoff retry strategy.

        Retries on:
        - 429 (rate limited)
        - 500, 502, 503, 504 (server errors)
        - Connection errors

        Does NOT retry:
        - 401, 403 (authentication/authorization)
        - 404 (not found)
        - 400 (bad request)
        """
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            # Don't retry on client errors
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD"],
            raise_on_status=False,  # Let us handle status codes
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_headers(self) -> Dict[str, str]:
        """
        Build HTTP headers for all requests.

        Includes:
        - Authorization: Bearer token
        - User-Agent: Identifies client
        - Client-Id: NASA metrics tracking
        - Content-Type: JSON
        """
        token = self.auth_handler.get_token()

        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
            self.CLIENT_ID_HEADER: self.client_id,
            "Content-Type": "application/json",
        }

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with auth, retries, logging, and SSL verification.
        """
        # Ensure full URL
        full_url = url if url.startswith("http") else urljoin(self.base_url, url)

        # Add SSL verification setting if not already provided
        if "verify" not in kwargs:
            kwargs["verify"] = self.verify_ssl

        # Add standard headers
        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "User-Agent": self.user_agent,
                self.CLIENT_ID_HEADER: self.client_id,
            }
        )

        # Add authentication token if available
        if self.auth_handler:
            token = self.auth_handler.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"

        # Add timeout
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        # Add CMR request ID for tracking
        if self.CMR_REQUEST_ID_HEADER not in headers:
            headers[self.CMR_REQUEST_ID_HEADER] = str(uuid.uuid4())

        # Log request
        logger.debug(f"{method} {full_url}")

        # Make request with proper error handling
        try:
            response = self.session.request(method, full_url, headers=headers, **kwargs)

            # Log response
            logger.debug(f"Response: {response.status_code}")

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                logger.warning(f"Rate limited. Retry after {retry_after}s")
                self._handle_rate_limit(response)
                # raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
                raise RateLimitError(f"Rate limited. Retry after {retry_after}s")

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed: Invalid or expired token")

            # Handle forbidden
            if response.status_code == 403:
                raise AuthenticationError("Access forbidden: 403")

            # Handle bad requests
            if response.status_code == 400:
                raise APIError(f"Bad request: {response.text}")

            # Handle not found
            if response.status_code == 404:
                raise APIError(f"Not found: {response.text}")

            # Handle server errors
            if response.status_code >= 500:
                error_msg = f"Server error {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise APIError(error_msg)

            return response

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout ({self.timeout}s): {e}")
            raise APIError(f"Request timeout ({self.timeout}s): {e}") from e

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise APIError(f"Connection error: {e}") from e

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Request failed: {e}") from e

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """
        Handle rate limiting by extracting retry time and waiting.

        Args:
            response: Response with 429 status
        """
        retry_after = response.headers.get("Retry-After", "60")
        try:
            wait_seconds = int(retry_after)
        except ValueError:
            wait_seconds = 60

        self._rate_limit_reset_time = time.time() + wait_seconds
        logger.warning(f"Rate limited. Waiting {wait_seconds}s before retry.")

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> requests.Response:
        """Make a GET request."""
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(
        self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> requests.Response:
        """Make a POST request."""
        return self.request("POST", endpoint, json=json_data, **kwargs)

    def put(
        self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> requests.Response:
        """Make a PUT request."""
        return self.request("PUT", endpoint, json=json_data, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
