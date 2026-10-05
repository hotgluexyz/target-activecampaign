"""Tests for ActiveCampaign stream sinks."""

from unittest.mock import Mock, call

from target_activecampaign.sinks import ContactsSink


def contacts_sink(config=None):
    """Create a sink without a target runner for isolated sink tests."""
    sink = object.__new__(ContactsSink)
    sink._config = config or {
        "api_url": "https://example.api-us1.com/api/3",
        "api_token": "token",
        "list_id": "7",
    }
    return sink


def test_contacts_preprocesses_an_etl_contact():
    result = contacts_sink().preprocess_record(
        {
            "externalId": "42",
            "email": "ada@example.org",
            "firstName": "Ada",
            "lastName": "Lovelace",
            "opt_in": True,
        },
        {},
    )

    assert result == {
        "contact": {
            "email": "ada@example.org",
            "firstName": "Ada",
            "lastName": "Lovelace",
        },
        "opt_in": True,
    }


def test_contacts_upsert_sets_the_contact_list_status():
    sink = contacts_sink()
    contact_response = Mock(ok=True)
    contact_response.json.return_value = {"contact": {"id": "99"}}
    list_response = Mock(ok=True)
    sink.request_api = Mock(side_effect=[contact_response, list_response])

    result = sink.upsert_record(
        {
            "contact": {"email": "ada@example.org"},
            "opt_in": False,
        },
        {},
    )

    assert result == ("99", True, {})
    assert sink.request_api.call_args_list == [
        call("POST", endpoint="/contact/sync", request_data={"email": "ada@example.org"}),
        call(
            "POST",
            endpoint="/contactLists",
            request_data={"contactList": {"contact": "99", "list": "7", "status": 2}},
        ),
    ]


def test_contacts_skip_list_update_when_not_configured():
    sink = contacts_sink({"api_url": "https://example.api-us1.com/api/3", "api_token": "token"})
    contact_response = Mock(ok=True)
    contact_response.json.return_value = {"contact": {"id": "99"}}
    sink.request_api = Mock(return_value=contact_response)

    sink.upsert_record({"contact": {"email": "ada@example.org"}, "opt_in": True}, {})

    assert sink.request_api.call_count == 1
