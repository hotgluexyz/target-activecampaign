"""ActiveCampaign target class."""

from __future__ import annotations

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.target_sdk.target import TargetHotglue

from target_activecampaign.sinks import (
    ContactsSink,
    EventsSink,
)


class TargetActiveCampaign(TargetHotglue):
    """Sample target for ActiveCampaign."""

    name = "target-activecampaign"

    SINK_TYPES = [EventsSink, ContactsSink]
    MAX_PARALLELISM = 1

    config_jsonschema = th.PropertiesList(
        th.Property("account_id", th.StringType),
        th.Property("event_key", th.StringType),
        th.Property("api_url", th.StringType, description="ActiveCampaign v3 API URL."),
        th.Property("api_token", th.StringType, description="ActiveCampaign API token."),
        th.Property("list_id", th.StringType, description="Optional list used to apply opt-in status."),
    ).to_dict()

if __name__ == "__main__":
    TargetActiveCampaign.cli()
