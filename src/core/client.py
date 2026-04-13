"""
Base HTTP client for NASA API requests.

Handles authentication, retry logic, rate limiting, proper headers, and CMR-specific
request patterns (search-after pagination, custom headers).

References:
- https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
- https://cmr.earthdata.nasa.gov/ingest/site/docs/ingest/api.html
"""

import logging
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Raised for API errors."""
    pass


class RateLimitError(APIError):
    """Raised when rate limited (HTTP 429)."""
    pass


class AuthenticationError(APIError):
    """Raised for authentication failures."""
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
        base_url: str = "https://cmr.earthdata.nasa.gov",
        client_id: str = "nasa-eo-data",
        user_agent: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
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
        """
        self.auth_handler = auth_handler
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout
        
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
        token = self.auth_handler.get_bearer_token()
        
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
            self.CLIENT_ID_HEADER: self.client_id,
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """
        Make an HTTP request with authentication and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments passed to requests (params, json, etc.)
            
        Returns:
            Response object
            
        Raises:
            RateLimitError: If rate limited
            AuthenticationError: If authentication fails
            APIError: For other API errors
        """
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        headers = self.get_headers()
        
        # Merge with any custom headers in kwargs
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        # Set default timeout
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        
        logger.debug(f"{method} {url}")
        
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                **kwargs
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                self._handle_rate_limit(response)
                raise RateLimitError(
                    f"Rate limited. Retry-After: {response.headers.get('Retry-After', 'unknown')}"
                )
            
            # Handle authentication errors
            if response.status_code in (401, 403):
                raise AuthenticationError(
                    f"Authentication failed ({response.status_code}): {response.text[:200]}"
                )
            
            # Log request ID for debugging
            request_id = response.headers.get(self.CMR_REQUEST_ID_HEADER)
            if request_id:
                logger.debug(f"CMR Request ID: {request_id}")
            
            # Raise for other HTTP errors
            if response.status_code >= 400:
                logger.error(
                    f"{method} {endpoint} returned {response.status_code}: {response.text[:200]}"
                )
                response.raise_for_status()
            
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {url}")
            raise APIError(f"Request timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise APIError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Request failed: {e}")

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
        logger.warning(
            f"Rate limited. Waiting {wait_seconds}s before retry."
        )

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """Make a GET request."""
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """Make a POST request."""
        return self.request("POST", endpoint, json=json_data, **kwargs)

    def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
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


class CMRClient(HTTPClient):
    """
    Specialized HTTP client for CMR API with search-after pagination.
    
    CMR search-after is a stateless pagination mechanism recommended for:
    - Deep paging (avoiding server state)
    - Harvesting large result sets
    - Data consistency when results change between requests
    
    Reference:
    https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#search-after
    """

    SEARCH_AFTER_HEADER = "CMR-Search-After"
    HITS_HEADER = "CMR-Hits"

    def __init__(self, *args, **kwargs):
        """Initialize CMR client."""
        if "base_url" not in kwargs:
            kwargs["base_url"] = "https://cmr.earthdata.nasa.gov"
        super().__init__(*args, **kwargs)


    def search(self,
               endpoint: str,
               params: Dict[str, Any],
               page_size: int = 2000,
               max_results: Optional[int] = None,
               ) -> tuple[List[Dict[str, Any]], int]:
        """
        Execute a paginated CMR search using search-after.
        
        Args:
            endpoint: Search endpoint (e.g., "search/granules")
            params: Search parameters (spatial, temporal, product, etc.)
            page_size: Results per page (1-2000, default 2000)
            max_results: Maximum total results to retrieve (None = all)
            
        Returns:
            (results, total_hits) tuple
        """
        all_results = []
        total_hits = None
        search_after = None
        
        while True:
            # Build request
            request_params = {
                **params,
                "page_size": page_size,
            }
            
            headers = {}
            if search_after:
                headers[self.SEARCH_AFTER_HEADER] = search_after
            
            # Execute search
            logger.debug(f"Fetching results with page_size={page_size}")
            response = self.get(endpoint, params=request_params, headers=headers)
            
            # Parse response
            data = response.json()
            items = data.get("items", [])
            all_results.extend(items)
            
            # Capture total hits from first response
            if total_hits is None:
                total_hits = int(response.headers.get(self.HITS_HEADER, 0))
                logger.debug(f"Total hits: {total_hits}")
            
            # Check if we're done
            if not items:
                break
            
            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break
            
            # Get next page token
            search_after = response.headers.get(self.SEARCH_AFTER_HEADER)
            if not search_after:
                # No more results
                break
        
        return all_results, total_hits or 0


    def get_with_metadata(self,
                          endpoint: str,
                          params:
                          Dict[str, Any]) -> tuple[requests.Response, Dict[str, Any]]:
        """
        Execute a GET request and extract CMR metadata headers.
        
        Returns:
            (response, metadata) tuple where metadata includes request_id, hits, etc.
        """
        response = self.get(endpoint, params=params)
        
        metadata = {
            "request_id": response.headers.get(self.CMR_REQUEST_HEADER),
            "hits": int(response.headers.get(self.HITS_HEADER, 0)),
            "took_ms": response.headers.get("CMR-Took"),
        }
        
        return response, metadata

    # Add CMR Request ID header constant if missing
    CMR_REQUEST_HEADER = "CMR-Request-Id"