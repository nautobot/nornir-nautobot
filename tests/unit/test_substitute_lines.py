"""Pytest for the `_substitute_lines` routing in the default dispatcher."""

from unittest.mock import MagicMock, patch

from nornir_nautobot.plugins.tasks.dispatcher.default import DispatcherMixin

PLAIN_SUBS = [{"regex": r"(enable secret 5 ).+", "replace": r"\1<removed>"}]
JINJA_SUBS = [
    {
        "regex": r"^username (\S+) privilege 15 secret 9 (\S+)$",
        "replace": r"username {{ \1 }} privilege 15 secret 9 {{ \2 | hash_data('md5') }}",
    }
]


def test_substitute_lines_empty_returns_config_unchanged():
    logger = MagicMock()
    config = "some config"
    assert DispatcherMixin._substitute_lines(logger, config, []) == config


def test_substitute_lines_plain_routes_to_sanitize_config():
    logger = MagicMock()
    config = "enable secret 5 abc"
    with (
        patch(
            "nornir_nautobot.plugins.tasks.dispatcher.default.sanitize_config",
            return_value="sanitized",
        ) as mock_sanitize,
        patch("nornir_nautobot.plugins.tasks.dispatcher.default.sanitize_config_jinja") as mock_jinja,
    ):
        result = DispatcherMixin._substitute_lines(logger, config, PLAIN_SUBS)

    assert result == "sanitized"
    mock_sanitize.assert_called_once_with(config, PLAIN_SUBS)
    mock_jinja.assert_not_called()


def test_substitute_lines_jinja_routes_to_sanitize_config_jinja():
    logger = MagicMock()
    config = "username foo privilege 15 secret 9 bar"
    with (
        patch(
            "nornir_nautobot.plugins.tasks.dispatcher.default.sanitize_config_jinja",
            return_value="hashed",
        ) as mock_jinja,
        patch("nornir_nautobot.plugins.tasks.dispatcher.default.sanitize_config") as mock_sanitize,
    ):
        result = DispatcherMixin._substitute_lines(logger, config, JINJA_SUBS)

    assert result == "hashed"
    mock_jinja.assert_called_once_with(config, JINJA_SUBS)
    mock_sanitize.assert_not_called()
