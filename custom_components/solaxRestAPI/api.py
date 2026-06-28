"""API client for SolaX local inverter data."""

from __future__ import annotations

import json
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout
from yarl import URL

REQUEST_TIMEOUT = ClientTimeout(total=3)


class SolaXRestAPIError(Exception):
    """Raised when the SolaX REST API request fails."""


class SolaXRestAPIClient:
    """Client for the SolaX realtime endpoint."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        password: str,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._host = host
        self._password = password

    @property
    def host(self) -> str:
        """Return configured host."""
        return self._host

    async def async_get_realtime_data(self) -> dict[str, Any]:
        """Fetch realtime data from the inverter."""
        url = URL.build(scheme="http", host=self._host, path="/")
        payload = {
            "optType": "ReadRealTimeData",
            "pwd": self._password,
        }

        try:
            async with self._session.post(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=REQUEST_TIMEOUT,
            ) as response:
                response.raise_for_status()
                raw_json = await response.text()
                payload = json.loads(
                    raw_json.replace(",,", ",0.0,").replace(",,", ",0.0,")
                )
                return {str(key).lower(): value for key, value in payload.items()}
        except (ClientError, TimeoutError, json.JSONDecodeError) as err:
            raise SolaXRestAPIError(f"Could not fetch data from {self._host}") from err
