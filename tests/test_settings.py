from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.settings import AppSettings, get_settings, reload_settings, save_settings


class SettingsMergeSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "settings.json"
        self._path_patch = patch(
            "src.core.settings.bootstrap_settings_path",
            return_value=self.path,
        )
        self._path_patch.start()
        reload_settings()

    def tearDown(self) -> None:
        self._path_patch.stop()
        self._tmpdir.cleanup()

    def test_daemon_save_does_not_overwrite_unrelated_gui_field(self) -> None:
        gui = get_settings()
        gui.auto_install_app_updates = True
        save_settings(gui)

        reload_settings()
        daemon = get_settings()
        self.assertTrue(daemon.auto_install_app_updates)
        daemon.selected_strategy = "other-strategy"
        save_settings(daemon)

        disk = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertTrue(disk["auto_install_app_updates"])
        self.assertEqual(disk["selected_strategy"], "other-strategy")

    def test_only_changed_fields_are_written(self) -> None:
        base = AppSettings()
        base.auto_check_app_updates_on_startup = False
        base.save(self.path)
        reload_settings()

        stale = get_settings()
        stale.auto_install_app_updates = True
        save_settings(stale)

        disk = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertTrue(disk["auto_install_app_updates"])
        self.assertFalse(disk["auto_check_app_updates_on_startup"])
