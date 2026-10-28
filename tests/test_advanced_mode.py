from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.core.settings import AppSettings


class AdvancedModeDefaultTests(unittest.TestCase):
    def test_fresh_install_starts_simple(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(AppSettings.load(Path(tmp) / "settings.json").advanced_mode)

    def test_settings_from_an_older_version_keep_the_full_interface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"selected_strategy": "general"}), encoding="utf-8")
            self.assertTrue(AppSettings.load(path).advanced_mode)

    def test_saved_choice_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            AppSettings(advanced_mode=False).save(path)
            self.assertFalse(AppSettings.load(path).advanced_mode)


if __name__ == "__main__":
    unittest.main()
