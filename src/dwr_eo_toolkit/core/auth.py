"""
Authentication module for API Login Integration

Handles credential retrieval from multiple sources (.netrc, env vars, tokens),
secure token management, and token refresh.

References:
- https://urs.earthdata.nasa.gov/documentation/for_users/user_token
- https://urs.earthdata.nasa.gov/sso_client_impl
"""

import base64
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple, Union

import requests

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class CredentialProvider(ABC):
    """Abstract base for credential sources."""

    @abstractmethod
    def get_credentials(self) -> Union[Tuple[str, str], str, None]:
        """Returns either (username, password) tuple or token string or None"""
        pass


class NetrcProvider(CredentialProvider):
    """Reads credentials from .netrc file (Unix/Linux/Mac)."""

    def __init__(self, netrc_path: Optional[str] = None):
        """
        Args:
            netrc_path: Path to .netrc file. Defaults to ~/.netrc
        """
        if netrc_path:
            self.netrc_path = Path(netrc_path)
        else:
            self.netrc_path = Path.home() / ".netrc"

    def get_credentials(self) -> Optional[tuple[str, str]]:
        """Extract Earthdata Login credentials from .netrc."""
        if not self.netrc_path.exists():
            return None

        try:
            # Read .netrc in a safe way (respects file permissions)
            import netrc as netrc_module

            rc = netrc_module.netrc(self.netrc_path)
            auth = rc.authenticators("urs.earthdata.nasa.gov")
            if auth:
                # netrc returns (login, account, password) tuple
                if auth:
                    username = auth[0]
                    password = auth[2]
                    if username and password:
                        return (username, password)
        except (FileNotFoundError, TypeError, Exception) as e:
            logger.debug(f"Could not read .netrc: {e}")

        return None


class EnvironmentProvider(CredentialProvider):
    """Reads credentials from environment variables."""

    def __init__(
        self,
        username_var: str = "EARTHDATA_USERNAME",
        password_var: str = "EARTHDATA_PASSWORD",
    ):
        """
        Args:
            username_var: Environment variable name for username
            password_var: Environment variable name for password
        """
        self.username_var = username_var
        self.password_var = password_var

    def get_credentials(self) -> Optional[tuple[str, str]]:
        """Extract credentials from environment variables."""
        username = os.getenv(self.username_var)
        password = os.getenv(self.password_var)

        if username and password:
            return (username, password)
        return None


class TokenProvider(CredentialProvider):
    """
    Uses a pre-generated EDL bearer token instead of username/password.

    Tokens are valid for 60 days and can be generated via:
    - https://urs.earthdata.nasa.gov (GUI: Account Settings > Generate Token)
    - EDL User Tokens API
    """

    def __init__(self, token_var: str = "EARTHDATA_TOKEN"):
        """
        Args:
            token_var: Environment variable name for the token
        """
        self.token_var = token_var

    def get_token(self) -> Optional[str]:
        """Get EDL bearer token from environment."""
        return os.getenv(self.token_var)

    def get_credentials(self) -> Optional[str]:
        return os.getenv(self.token_var)


class EarthDataLoginAuth:
    """
    Manages authentication with NASA Earthdata Login (EDL).

    Supports multiple authentication methods in priority order:
    1. Pre-generated EDL bearer token (fastest, no network call)
    2. Credentials from .netrc (Unix/Linux/Mac)
    3. Credentials from environment variables

    References:
    - Bearer tokens: https://urs.earthdata.nasa.gov/documentation/for_users/user_token
    - Token validity: 60 days, max 2 active tokens
    """

    EARTHDATA_LOGIN_HOST = "urs.earthdata.nasa.gov"
    TOKEN_ENDPOINT = f"https://{EARTHDATA_LOGIN_HOST}/api/users/tokens"
    TOKEN_REFRESH_ENDPOINT = f"https://{EARTHDATA_LOGIN_HOST}/oauth/token"

    def __init__(
        self,
        netrc_path: Optional[str] = None,
        token_cache_dir: Optional[str] = None,
        username_var: str = "EARTHDATA_USERNAME",
        password_var: str = "EARTHDATA_PASSWORD",
        token_var: str = "EARTHDATA_TOKEN",
    ):
        """
        Initialize Earthdata Login authentication.

        Args:
            netrc_path: Path to .netrc file (defaults to ~/.netrc)
            token_cache_dir: Directory to cache tokens (defaults to ~/.nasa-eo-data)
            username_var: Environment variable for username
            password_var: Environment variable for password
            token_var: Environment variable for pre-generated token
        """
        self.netrc_path = netrc_path

        # Set up token cache directory
        if token_cache_dir:
            self.token_cache_dir = Path(token_cache_dir)
        else:
            self.token_cache_dir = Path.home() / ".nasa-eo-data"
        self.token_cache_dir.mkdir(parents=True, exist_ok=True)
        self.token_cache_file = self.token_cache_dir / ".edl_token"

        # Set up credential providers in priority order
        self.token_provider = TokenProvider(token_var)
        self.netrc_provider = NetrcProvider(netrc_path)
        self.env_provider = EnvironmentProvider(username_var, password_var)

        self._cached_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def get_token(self) -> str:
        """
        Get a valid EDL bearer token.

        Priority:
        1. Check cached in-memory token (if not expired)
        2. Check cached token file (if not expired)
        3. Check for pre-generated token in environment
        4. Request new token using credentials from .netrc or environment

        Returns:
            Valid EDL bearer token string

        Raises:
            AuthenticationError: If no valid token can be obtained
        """
        # 1. Check in-memory cache
        if self._cached_token and self._token_expiry:
            if datetime.now(timezone.utc) < self._token_expiry - timedelta(minutes=5):
                logger.debug("Using cached bearer token (in-memory)")
                return self._cached_token

        # 2. Check file cache
        token_from_file = self._load_cached_token()
        if token_from_file:
            logger.debug("Using cached bearer token (file)")
            self._cached_token = token_from_file
            return token_from_file

        # 3. Check for pre-generated token in environment
        creds = self.token_provider.get_credentials()
        if isinstance(creds, str):  # It's a token, not a tuple
            logger.debug("Using pre-generated EDL bearer token from environment")
            self._cached_token = creds
            # Pre-generated tokens expire in 60 days, but we don't know when
            self._token_expiry = datetime.now(timezone.utc) + timedelta(days=59)
            return creds

        # 4. Request new token using credentials
        token = self._request_token()
        if token:
            self._cached_token = token
            self._token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            self._save_cached_token(token)
            return token

        raise AuthenticationError(
            "Could not obtain EDL bearer token. Provide credentials via:\n"
            "  1. EARTHDATA_TOKEN environment variable (pre-generated token)\n"
            "  2. ~/.netrc file with 'urs.earthdata.nasa.gov' entry\n"
            "  3. EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables"
        )

    def _request_token(self) -> Optional[str]:
        """
        Request a new EDL bearer token using username/password credentials.

        Uses HTTP Basic Auth as per:
        https://urs.earthdata.nasa.gov/documentation/for_users/user_token
        """
        credentials = self._get_credentials()
        if not credentials:
            return None

        username, password = credentials
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()

        try:
            response = requests.post(
                self.TOKEN_ENDPOINT,
                headers={"Authorization": f"Basic {auth}"},
                timeout=10,
            )
            token_data = response.json()
            token = token_data.get("access_token")
            return str(token) if token else None

        except Exception as e:
            logger.error(f"Failed to request EDL token: {e}")
            return None

    def _get_credentials(self) -> Optional[Tuple[str, str]]:
        """Get credentials from first available source."""
        # Try .netrc first (most secure)
        creds = self.netrc_provider.get_credentials()
        if creds and isinstance(creds, tuple) and len(creds) == 2:
            return creds

        # Fall back to environment variables
        creds = self.env_provider.get_credentials()
        if creds and isinstance(creds, tuple) and len(creds) == 2:
            return creds

        return None

    def _save_cached_token(self, token: str) -> None:
        """Save token to file cache (world-readable only by owner)."""
        try:
            cache_data = {
                "token": token,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.token_cache_file.write_text(
                json.dumps(cache_data, indent=2),
                encoding="utf-8",
            )
            # Restrict file permissions: owner read/write only
            self.token_cache_file.chmod(0o600)
            logger.debug(f"Cached token to {self.token_cache_file}")
        except Exception as e:
            logger.warning(f"Could not cache token: {e}")

    def _load_cached_token(self) -> Optional[str]:
        if not self.token_cache_file.exists():
            return None

        try:
            cache_data = json.loads(self.token_cache_file.read_text())
            token = cache_data.get("token")
            timestamp_str = cache_data.get("timestamp")

            if not token or not timestamp_str:
                return None

            # Tokens expire in 1 hour (conservative assumption)
            cached_time = datetime.fromisoformat(timestamp_str)
            if datetime.now(timezone.utc) - cached_time < timedelta(hours=1):
                return str(token) if isinstance(token, str) else None
        except Exception as e:
            logger.debug(f"Could not load cached token: {e}")

        return None

    def setup_netrc(self, username: str, password: str) -> None:
        """
        Create or update .netrc file with Earthdata Login credentials.

        Args:
            username: Earthdata Login username
            password: Earthdata Login password
        """
        netrc_path = Path.home() / ".netrc"

        # Read existing .netrc if present
        existing_lines = []
        if netrc_path.exists():
            existing_lines = netrc_path.read_text().splitlines()

        # Remove any existing urs.earthdata.nasa.gov entry
        new_lines = [line for line in existing_lines if "urs.earthdata.nasa.gov" not in line]

        # Add new entry
        new_lines.extend(
            [
                f"machine {self.EARTHDATA_LOGIN_HOST}",
                f"login {username}",
                f"password {password}",
                "",
            ]
        )

        netrc_path.write_text("\n".join(new_lines))
        netrc_path.chmod(0o600)  # .netrc must be readable only by owner
        logger.info(f"Updated {netrc_path} with Earthdata Login credentials")

    def setup_environment(self, username: str, password: str, token: Optional[str] = None) -> None:
        """
        Print shell commands to set up environment variables.

        Args:
            username: Earthdata Login username
            password: Earthdata Login password
            token: Pre-generated EDL bearer token (optional)
        """
        commands = [
            f"export EARTHDATA_USERNAME={username}",
            f"export EARTHDATA_PASSWORD={password}",
        ]
        if token:
            commands.append(f"export EARTHDATA_TOKEN={token}")

        print("\nAdd these to your shell profile or run directly:")
        print("\n".join(commands))

    def clear_cache(self) -> None:
        """Clear all cached tokens."""
        try:
            self.token_cache_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Could not clear cache: {e}")

        self._cached_token = None
        self._token_expiry = None
        logger.info("Cleared cached tokens")
