"""ActiveCampaign target class."""

from __future__ import annotations

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.target_sdk.target import TargetHotglue

from target_activecampaign.sinks import (
    EventsSink,
)


class TargetActiveCampaign(TargetHotglue):
    """Sample target for ActiveCampaign."""

    name = "target-activecampaign"

    SINK_TYPES = [EventsSink]
    MAX_PARALLELISM = 1

    config_jsonschema = th.PropertiesList(
        th.Property("account_id", th.StringType, required=True),
        th.Property("event_key", th.StringType, required=True),
    ).to_dict()

if __name__ == "__main__":
    TargetActiveCampaign.cli()
