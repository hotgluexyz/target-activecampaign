"""ActiveCampaign target sink class, which handles writing streams."""

from __future__ import annotations
import json

import requests
from typing_extensions import override

from target_activecampaign.client import ActiveCampaignSink

class EventsSink(ActiveCampaignSink):
    """ActiveCampaign target sink class."""    
    endpoint = "/event"
    name = "events"

    def preprocess_record(self, record: dict, context: dict):
        record["key"] = self.config.get("event_key")
        record["actid"] = self.config.get("account_id")
        record["visit"] = json.dumps(record.get("visit")) if type(record.get("visit")) == dict else record.get("visit")

        return record

    def upsert_record(self, record: dict, context: dict):
        response = self.request_api(
            "POST", endpoint=self.endpoint, request_data=record
        )

        # NOTE: hardcoded to return id as 1 because the API does not return an id
        return 1, response.ok, dict()


class ContactsSink(ActiveCampaignSink):
    """Upsert contacts through ActiveCampaign's v3 contact sync endpoint."""

    endpoint = "/contact/sync"
    name = "contacts"

    @property
    def base_url(self) -> str:
        """Return the configured ActiveCampaign v3 API root."""
        return self.config["api_url"].rstrip("/")

    @property
    def http_headers(self) -> dict:
        """Return headers for the ActiveCampaign v3 API."""
        return {"Api-Token": self.config["api_token"], "Content-Type": "application/json"}

    @override
    def preprocess_record(self, record: dict, context: dict) -> dict:
        """Wrap the normalized ETL record in ActiveCampaign's contact payload."""
        return {
            "contact": {
                "email": record["email"],
                "firstName": record.get("firstName"),
                "lastName": record.get("lastName"),
            },
            "opt_in": record.get("opt_in", False),
        }

    @override
    def _request(
        self, http_method, endpoint, params={}, request_data=None, headers={}, verify=True
    ) -> requests.Response:
        """Send JSON to ActiveCampaign's v3 API."""
        response = requests.request(
            method=http_method,
            url=self.url(endpoint),
            params=params,
            headers=self.http_headers,
            json=request_data,
        )
        self.validate_response(response)
        return response

    @override
    def upsert_record(self, record: dict, context: dict):
        """Create or update the contact, then set its configured list status."""
        response = self.request_api("POST", endpoint=self.endpoint, request_data=record["contact"])
        contact = response.json()["contact"]

        if self.config.get("list_id"):
            self.request_api(
                "POST",
                endpoint="/contactLists",
                request_data={
                    "contactList": {
                        "contact": contact["id"],
                        "list": self.config["list_id"],
                        "status": 1 if record["opt_in"] else 2,
                    }
                },
            )

        return contact["id"], response.ok, dict()
