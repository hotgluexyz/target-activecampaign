"""ActiveCampaign target sink class, which handles writing streams."""

from __future__ import annotations

import backoff
import requests

from hotglue_singer_sdk.exceptions import RetriableAPIError
from hotglue_singer_sdk.target_sdk.client import HotglueSink


class ActiveCampaignSink(HotglueSink):
    """Base sink for the ActiveCampaign v3 REST API."""

    # Streams this sink accepts, in addition to `name`.
    available_names: list[str] = []

    @property
    def base_url(self) -> str:
        api_url = (self.config.get("api_url") or "").rstrip("/")
        api_version = self.config.get("api_version") or 3
        return f"{api_url}/api/{api_version}"

    @property
    def http_headers(self) -> dict:
        return {"Api-Token": self.config.get("api_token")}


class ActiveCampaignTrackingSink(ActiveCampaignSink):
    """Base sink for the ActiveCampaign event tracking API.

    Unlike the REST API this host is unauthenticated, shared across accounts and
    expects form encoded bodies rather than JSON.
    """

    base_url = "https://trackcmp.net"
    http_headers: dict = {}

    @backoff.on_exception(
        backoff.expo,
        (RetriableAPIError, requests.exceptions.ReadTimeout),
        max_tries=5,
        factor=2,
    )
    def _request(
        self, http_method, endpoint, params={}, request_data=None, headers={}, verify=True
    ) -> requests.PreparedRequest:
        """Prepare a request object."""
        url = self.url(endpoint)
        headers = self.http_headers

        response = requests.request(
            method=http_method,
            url=url,
            params=params,
            headers=headers,
            data=request_data,
        )
        self.validate_response(response)
        return response
