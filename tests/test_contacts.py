from unittest.mock import Mock, call

from target_activecampaign.sinks import ContactsSink


def contacts_sink():
    sink = object.__new__(ContactsSink)
    sink._config = {
        "api_url": "https://example.api-us1.com",
        "api_token": "token",
        "list_id": "5",
    }
    return sink


def test_contact_sync_upserts_existing_contact_and_applies_subscription():
    sink = contacts_sink()
    contact_response = Mock(ok=True)
    contact_response.json.return_value = {"contact": {"id": "99"}}
    list_response = Mock(ok=True)
    sink.request_api = Mock(side_effect=[contact_response, list_response])

    result = sink.upsert_record(
        {
            "contact": {"email": "ada@example.org"},
            "status": 1,
        },
        {},
    )

    assert result == ("99", True, {})
    assert sink.request_api.call_args_list == [
        call(
            "POST",
            endpoint="/contact/sync",
            request_data={"contact": {"email": "ada@example.org"}, "status": 1},
        ),
        call(
            "POST",
            endpoint="/contactLists",
            request_data={"contactList": {"list": 5, "contact": 99, "status": 1}},
        ),
    ]
