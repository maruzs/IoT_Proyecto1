import pytest

from coap_bridge.coap_server import validate_json


def test_validate_json_returns_dict_for_valid_payload():
    payload = b'{"temperatura": 29.5}'
    result = validate_json(payload, "temperatura")
    assert result == {"temperatura": 29.5}


def test_validate_json_raises_on_missing_field():
    payload = b'{}'
    with pytest.raises(ValueError, match="Missing required field: humedad"):
        validate_json(payload, "humedad")


def test_validate_json_raises_on_non_json_payload():
    payload = b"not json"
    with pytest.raises(ValueError, match="Payload is not valid JSON"):
        validate_json(payload, "gas")
