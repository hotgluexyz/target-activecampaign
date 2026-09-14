"""ActiveCampaign target sink class, which handles writing streams."""

from __future__ import annotations

import json
from typing import Any, Optional

from target_activecampaign.client import ActiveCampaignSink, ActiveCampaignTrackingSink

SUBSCRIBED = 1
UNSUBSCRIBED = 2

FIELDS_PAGE_SIZE = 100


def parse_json_field(value: Any) -> Any:
    """Parse a field that may arrive stringified after record flattening."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


class EventsSink(ActiveCampaignTrackingSink):
    """ActiveCampaign target sink class."""

    endpoint = "/event"
    name = "events"
    available_names = ["events", "event"]

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
    """Upsert contacts and keep their list subscription in sync."""

    endpoint = "/contacts"
    name = "contacts"
    available_names = ["contacts", "contact", "customer", "customers"]

    _custom_field_ids: Optional[dict] = None

    def preprocess_record(self, record: dict, context: dict) -> dict:
        contact = {
            "email": record.get("email"),
            "firstName": record.get("first_name"),
            "lastName": record.get("last_name"),
            "phone": self.get_phone(record),
        }
        if record.get("id"):
            contact["id"] = str(record["id"])

        field_values = self.map_custom_fields(record.get("custom_fields"))
        if field_values:
            contact["fieldValues"] = field_values

        payload = {"contact": self.clean_dict_items(contact)}

        status = self.subscription_status(record)
        if status is not None:
            payload["status"] = status

        return payload

    def upsert_record(self, record: dict, context: dict):
        contact = record["contact"]
        contact_id = contact.pop("id", None) or self.get_contact_id(contact.get("email"))

        if contact_id:
            response = self.request_api(
                "PUT",
                endpoint=f"{self.endpoint}/{contact_id}",
                request_data={"contact": contact},
            )
        else:
            response = self.request_api(
                "POST", endpoint=self.endpoint, request_data={"contact": contact}
            )

        is_updated = contact_id is not None
        contact_id = response.json()["contact"]["id"]
        self.sync_list_status(contact_id, record.get("status"))

        return contact_id, response.ok, {"is_updated": is_updated}

    def get_contact_id(self, email: Optional[str]) -> Optional[str]:
        """Look up an existing contact by email address."""
        if not email:
            return None

        response = self.request_api("GET", endpoint=self.endpoint, params={"email": email})
        contacts = response.json().get("contacts") or []

        return contacts[0]["id"] if contacts else None

    def sync_list_status(self, contact_id: str, status: Optional[int]) -> None:
        """Subscribe or unsubscribe the contact from the configured list."""
        list_id = self.config.get("list_id")
        if status is None:
            return
        if not list_id:
            self.logger.warning(
                "Skipping list subscription for contact "
                f"{contact_id}: no list_id configured"
            )
            return

        self.request_api(
            "POST",
            endpoint="/contactLists",
            request_data={
                "contactList": {
                    "list": int(list_id),
                    "contact": int(contact_id),
                    "status": status,
                }
            },
        )

    @staticmethod
    def subscription_status(record: dict) -> Optional[int]:
        """Translate the unified subscription fields into a contactList status."""
        if record.get("unsubscribed") is not None:
            return UNSUBSCRIBED if record["unsubscribed"] else SUBSCRIBED

        status = record.get("subscribe_status")
        if isinstance(status, bool):
            return SUBSCRIBED if status else UNSUBSCRIBED
        if isinstance(status, str):
            return SUBSCRIBED if status.lower() == "subscribed" else UNSUBSCRIBED

        return None

    @staticmethod
    def get_phone(record: dict) -> Optional[str]:
        if record.get("phone"):
            return record["phone"]

        phone_numbers = parse_json_field(record.get("phone_numbers")) or []
        if not isinstance(phone_numbers, list) or not phone_numbers:
            return None

        return phone_numbers[0].get("number")

    @property
    def custom_field_ids(self) -> dict:
        """Map of lowercased custom field title and personalization tag to field id."""
        if self._custom_field_ids is None:
            self._custom_field_ids = self.fetch_custom_field_ids()
        return self._custom_field_ids

    def fetch_custom_field_ids(self) -> dict:
        field_ids = {}
        offset = 0

        while True:
            response = self.request_api(
                "GET",
                endpoint="/fields",
                params={"limit": FIELDS_PAGE_SIZE, "offset": offset},
            )
            fields = response.json().get("fields") or []

            for field in fields:
                for key in (field.get("title"), field.get("perstag")):
                    if key:
                        field_ids[key.lower()] = field["id"]

            if len(fields) < FIELDS_PAGE_SIZE:
                return field_ids
            offset += FIELDS_PAGE_SIZE

    def map_custom_fields(self, custom_fields: Any) -> list:
        """Resolve unified custom fields to the fieldValues the API expects."""
        custom_fields = parse_json_field(custom_fields)
        if not custom_fields:
            return []

        field_values = []
        for field in custom_fields:
            name = field.get("name") or field.get("label")
            field_id = self.custom_field_ids.get(str(name).lower()) if name else None

            if not field_id:
                self.logger.warning(f"Skipping unknown ActiveCampaign field '{name}'")
                continue

            field_values.append({"field": field_id, "value": field.get("value")})

        return field_values
