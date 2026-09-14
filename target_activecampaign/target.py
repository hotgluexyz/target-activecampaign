"""ActiveCampaign target class."""

from __future__ import annotations

from typing import Type

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.sinks import Sink
from hotglue_singer_sdk.target_sdk.target import TargetHotglue

from target_activecampaign.sinks import (
    ContactsSink,
    EventsSink,
)


class TargetActiveCampaign(TargetHotglue):
    """Sample target for ActiveCampaign."""

    name = "target-activecampaign"

    SINK_TYPES = [ContactsSink, EventsSink]
    MAX_PARALLELISM = 1

    config_jsonschema = th.PropertiesList(
        th.Property("account_id", th.StringType, required=True),
        th.Property("event_key", th.StringType, required=True),
        th.Property("api_url", th.StringType, required=True),
        th.Property("api_token", th.StringType, required=True),
        th.Property("api_version", th.StringType, default="3"),
        th.Property("list_id", th.StringType),
    ).to_dict()

    def get_sink_class(self, stream_name: str) -> Type[Sink]:
        """Resolve a sink by its name or any of its accepted aliases."""
        return next(
            (
                sink_class
                for sink_class in self.SINK_TYPES
                if stream_name.lower()
                in [name.lower() for name in sink_class.available_names or [sink_class.name]]
            ),
            self.default_sink_class,
        )


if __name__ == "__main__":
    TargetActiveCampaign.cli()
