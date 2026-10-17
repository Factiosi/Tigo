from __future__ import annotations

import unittest

from src.core.settings import AppSettings
from src.modules.tg_ws_proxy.options import (
    DEFAULT_DC_IP,
    dc_lines,
    telegram_link,
    validate_dc_ip,
    validate_port,
)


class TgWsProxyOptionTests(unittest.TestCase):
    def test_defaults_match_upstream(self) -> None:
        settings = AppSettings()
        self.assertFalse(settings.tg_ws_proxy_enabled)
        self.assertEqual(settings.tg_ws_proxy_port, 1443)
        self.assertEqual(settings.tg_ws_proxy_secret, "")
        self.assertEqual(tuple(settings.tg_ws_proxy_dc_ip), DEFAULT_DC_IP)

    def test_link_uses_dd_secret(self) -> None:
        secret = "ab" * 16
        self.assertEqual(
            telegram_link(1443, secret),
            f"tg://proxy?server=127.0.0.1&port=1443&secret=dd{secret}",
        )

    def test_port_and_dc_validation(self) -> None:
        self.assertIsNone(validate_port("1443"))
        self.assertIsNotNone(validate_port("0"))
        self.assertIsNotNone(validate_port("нет"))
        self.assertIsNone(validate_dc_ip(list(DEFAULT_DC_IP)))
        self.assertIsNotNone(validate_dc_ip(["2:not-an-ip"]))
        self.assertEqual(dc_lines([]), list(DEFAULT_DC_IP))
