from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.migrations.v131_remove_appdata_tigo_update import run as run_v131


class V131MigrationTests(unittest.TestCase):
    def test_skips_when_not_packaged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "TigoUpdate.exe"
            legacy.write_bytes(b"legacy")
            with patch("src.core.migrations.v131_remove_appdata_tigo_update.is_packaged_app", return_value=False):
                with patch("src.core.migrations.v131_remove_appdata_tigo_update.app_data_root", return_value=root):
                    run_v131()
            self.assertTrue(legacy.is_file())

    def test_removes_legacy_appdata_copy_when_packaged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "TigoUpdate.exe"
            legacy.write_bytes(b"legacy")
            with patch("src.core.migrations.v131_remove_appdata_tigo_update.is_packaged_app", return_value=True):
                with patch("src.core.migrations.v131_remove_appdata_tigo_update.app_data_root", return_value=root):
                    run_v131()
            self.assertFalse(legacy.exists())

    def test_no_op_when_legacy_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("src.core.migrations.v131_remove_appdata_tigo_update.is_packaged_app", return_value=True):
                with patch("src.core.migrations.v131_remove_appdata_tigo_update.app_data_root", return_value=root):
                    run_v131()


if __name__ == "__main__":
    unittest.main()
