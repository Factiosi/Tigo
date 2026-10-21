from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.settings import AppSettings
from src.modules.filters import ipset_filter as ipf


class IpsetModeAcrossUpdatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.settings = AppSettings(ipset_filter="any")
        self._patches = [
            patch.object(ipf, "flowseal_version_lists_dir", side_effect=lambda v: self.root / v / "lists"),
            patch.object(ipf, "get_settings", side_effect=lambda: self.settings),
            patch.object(ipf, "save_settings", side_effect=lambda s=None: None),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _fresh_version(self, version: str) -> Path:
        lists = self.root / version / "lists"
        lists.mkdir(parents=True)
        (lists / "ipset-all.txt").write_text("1.2.3.0/24\n", encoding="utf-8")
        return lists

    def test_all_ip_survives_new_flowseal_version(self) -> None:
        lists = self._fresh_version("1.10.4")
        self.assertEqual(ipf.keep_ipset_mode("1.10.4"), "any")
        self.assertEqual((lists / "ipset-all.txt").read_text(encoding="utf-8"), "")
        self.assertEqual(self.settings.ipset_filter, "any")
        # Лист сохранён в резерв, «Из листа» потом возвращается.
        ipf.apply_ipset_mode("1.10.4", "loaded")
        self.assertIn("1.2.3.0/24", (lists / "ipset-all.txt").read_text(encoding="utf-8"))

    def test_disabled_survives_new_flowseal_version(self) -> None:
        self.settings.ipset_filter = "none"
        lists = self._fresh_version("1.10.4")
        self.assertEqual(ipf.keep_ipset_mode("1.10.4"), "none")
        self.assertIn(ipf.DUMMY_IP, (lists / "ipset-all.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
