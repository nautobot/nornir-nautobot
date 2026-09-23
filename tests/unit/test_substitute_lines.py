"""Pytest for the `_substitute_lines` handling in the default dispatcher."""

from unittest.mock import MagicMock, patch

from nornir_nautobot.plugins.tasks.dispatcher.default import DispatcherMixin

MD5_BAR = "37b51d194a7513e45b56f6524f2d51f2"

PLAIN_SUBS = [{"regex": r"(enable secret 5 ).+", "replace": r"\1<removed>"}]
JINJA_SUBS = [
    {
        "regex": r"^(username \S+ privilege 15 secret 9 )(\S+)$",
        "replace": r"\1{{ \2 | hash_data('md5') }}",
        "render_jinja": True,
    }
]
# A Golden Config postprocessing placeholder, which must reach the backup verbatim.
POSTPROCESSING_SUBS = [
    {
        "regex": r"^(username \S+ password 7 )\S+$",
        "replace": r'\1{{ secrets_group["name"] | get_secret_by_secret_group_name("password") }}',
    }
]


def test_substitute_lines_empty_returns_config_unchanged():
    logger = MagicMock()
    config = "some config"
    assert DispatcherMixin._substitute_lines(logger, config, []) == config


def test_substitute_lines_plain_filter_is_substituted_literally():
    logger = MagicMock()
    config = "enable secret 5 abc"
    assert DispatcherMixin._substitute_lines(logger, config, PLAIN_SUBS) == "enable secret 5 <removed>"


def test_substitute_lines_without_opt_in_never_reaches_the_renderer():
    # Jinja rendering, and with it the optional jinja2 dependency, stays out of the path entirely
    # unless a filter asks for it.
    logger = MagicMock()
    config = "enable secret 5 abc"
    with patch("nornir_nautobot.plugins.tasks.dispatcher.default.sanitize_config_jinja") as mock_jinja:
        result = DispatcherMixin._substitute_lines(logger, config, PLAIN_SUBS + POSTPROCESSING_SUBS)

    assert result == "enable secret 5 <removed>"
    mock_jinja.assert_not_called()


def test_substitute_lines_renders_jinja_when_opted_in():
    logger = MagicMock()
    config = "username foo privilege 15 secret 9 bar"
    result = DispatcherMixin._substitute_lines(logger, config, JINJA_SUBS)
    assert result == f"username foo privilege 15 secret 9 {MD5_BAR}"


def test_substitute_lines_leaves_unflagged_jinja_untouched():
    logger = MagicMock()
    config = "username foo password 7 bar"
    result = DispatcherMixin._substitute_lines(logger, config, POSTPROCESSING_SUBS)
    assert result == 'username foo password 7 {{ secrets_group["name"] | get_secret_by_secret_group_name("password") }}'
