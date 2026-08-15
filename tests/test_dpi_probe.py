from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.modules.strategy_testing.dpi_probe import _classify_curl


class DpiProbeClassificationTests(unittest.TestCase):
    def test_likely_blocked_in_warn_window_with_nonzero_exit(self) -> None:
        with patch("src.modules.strategy_testing.dpi_probe.subprocess.run") as run:
            run.return_value = MagicMock(
                returncode=18,
                stdout="200 18432",
                stderr="",
            )
            self.assertEqual(_classify_curl("https://example.com", ["--http1.1"]), "LIKELY_BLOCKED")

    def test_ok_on_success(self) -> None:
        with patch("src.modules.strategy_testing.dpi_probe.subprocess.run") as run:
            run.return_value = MagicMock(
                returncode=0,
                stdout="200 65536",
                stderr="",
            )
            self.assertEqual(_classify_curl("https://example.com", ["--http1.1"]), "OK")

    def test_unsup_on_tls_error(self) -> None:
        with patch("src.modules.strategy_testing.dpi_probe.subprocess.run") as run:
            run.return_value = MagicMock(
                returncode=35,
                stdout="",
                stderr="unsupported protocol",
            )
            self.assertEqual(_classify_curl("https://example.com", ["--tlsv1.3"]), "UNSUP")
