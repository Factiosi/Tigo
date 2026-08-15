from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.settings import AppSettings
from src.modules.filters import game_filter as gf


class GameFilterSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.utils = self.tmp / "utils"
        self.utils.mkdir()
        self._settings_patch = patch(
            "src.modules.filters.game_filter.get_settings",
            side_effect=self._load_settings,
        )
        self._save_patch = patch(
            "src.modules.filters.game_filter.save_settings",
            side_effect=self._persist_settings,
        )
        self._utils_patch = patch(
            "src.modules.filters.game_filter.utils_dir",
            return_value=self.utils,
        )
        self._settings_patch.start()
        self._save_patch.start()
        self._utils_patch.start()
        self._settings = AppSettings()

    def tearDown(self) -> None:
        self._utils_patch.stop()
        self._save_patch.stop()
        self._settings_patch.stop()
        self._tmpdir.cleanup()

    def _load_settings(self) -> AppSettings:
        return self._settings

    def _persist_settings(self, settings: AppSettings | None = None) -> None:
        if settings is not None:
            self._settings = settings

    def test_apply_writes_flag_and_settings(self) -> None:
        self._settings.game_filter = "off"
        gf.apply_game_filter("1.0.0", "tcp")
        self.assertEqual(self._settings.game_filter, "tcp")
        self.assertEqual(
            (self.utils / "game_filter.enabled").read_text(encoding="utf-8").strip(),
            "tcp",
        )

    def test_sync_restores_disk_from_settings(self) -> None:
        self._settings.game_filter = "udp"
        mode = gf.ensure_game_filter_synced("1.0.0")
        self.assertEqual(mode, "udp")
        self.assertEqual(
            (self.utils / "game_filter.enabled").read_text(encoding="utf-8").strip(),
            "udp",
        )

    def test_sync_does_not_reset_settings_when_flag_missing(self) -> None:
        self._settings.game_filter = "tcp"
        mode = gf.ensure_game_filter_synced("1.0.0")
        self.assertEqual(mode, "tcp")
        self.assertEqual(self._settings.game_filter, "tcp")

    def test_sync_adopts_disk_when_settings_still_off(self) -> None:
        (self.utils / "game_filter.enabled").write_text("all\n", encoding="utf-8")
        mode = gf.ensure_game_filter_synced("1.0.0")
        self.assertEqual(mode, "all")
        self.assertEqual(self._settings.game_filter, "all")

    def test_apply_off_removes_flag(self) -> None:
        (self.utils / "game_filter.enabled").write_text("tcp\n", encoding="utf-8")
        gf.apply_game_filter("1.0.0", "off")
        self.assertFalse((self.utils / "game_filter.enabled").exists())
        self.assertEqual(self._settings.game_filter, "off")


if __name__ == "__main__":
    unittest.main()
