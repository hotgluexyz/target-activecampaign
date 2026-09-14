import json
from unittest.mock import MagicMock

from target_activecampaign.target import TargetActiveCampaign
from target_activecampaign.sinks import ContactsSink

cfg = {
    "account_id": "1",
    "event_key": "k",
    "api_url": "https://acct.api-us1.com",
    "api_token": "tok",
    "list_id": "7",
}
t = TargetActiveCampaign(config=cfg)
sink = ContactsSink(t, "contacts", {"type": "object", "properties": {}}, ["id"])

calls = []


def fake(method, endpoint=None, params={}, request_data=None, **kw):
    calls.append((method, endpoint, dict(params), request_data))
    r = MagicMock()
    r.ok = True
    if endpoint == "/fields":
        r.json.return_value = {
            "fields": [{"id": "3", "title": "Favorite Color", "perstag": "FAV"}]
        }
    elif method == "GET" and endpoint == "/contacts":
        hit = params.get("email") == "exists@x.com"
        r.json.return_value = {"contacts": [{"id": "42"}] if hit else []}
    else:
        r.json.return_value = {"contact": {"id": "42"}}
    return r


sink.request_api = fake

cases = [
    (
        "new + subscribed",
        {
            "email": "new@x.com",
            "first_name": "Ada",
            "last_name": "L",
            "subscribe_status": "subscribed",
            "phone_numbers": [{"number": "555-1234"}],
            "custom_fields": [
                {"name": "Favorite Color", "value": "blue"},
                {"name": "Nope", "value": "x"},
            ],
        },
    ),
    ("existing + unsubscribed", {"email": "exists@x.com", "first_name": "Bob", "unsubscribed": True}),
    ("known remote id", {"id": "99", "email": "known@x.com", "first_name": "Cy"}),
    ("no subscription info", {"email": "plain@x.com"}),
]

for label, rec in cases:
    calls.clear()
    payload = sink.preprocess_record(dict(rec), {})
    result = sink.upsert_record(payload, {})
    print(f"\n=== {label} ===")
    print("payload:", json.dumps(payload))
    print("result :", result)
    for method, endpoint, params, data in calls:
        print(f"  {method} {endpoint} {params or ''} {json.dumps(data) if data else ''}")
