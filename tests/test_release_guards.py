from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.core.settings import AppSettings
from src.daemon.protocol import DaemonStatus, status_from_dict, status_to_dict
from src.kernel.public import get_effective_runtime_status
from src.modules.lifecycle.public import should_launch_gui, should_start_hidden
from src.modules.updates.github import _safe_extract_zip
from src.modules.updates.service import ensure_runtime_installed


class SafeZipTests(unittest.TestCase):
    def _archive(self, entries: dict[str, bytes]) -> zipfile.ZipFile:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, payload in entries.items():
                archive.writestr(name, payload)
        buffer.seek(0)
        archive = zipfile.ZipFile(buffer, "r")
        archive._test_buffer = buffer  # type: ignore[attr-defined]
        return archive

    def test_extracts_regular_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self._archive(
            {"flowseal/bin/winws.exe": b"ok"}
        ) as archive:
            root = Path(tmp)
            _safe_extract_zip(archive, root)
            self.assertEqual((root / "flowseal/bin/winws.exe").read_bytes(), b"ok")

    def test_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self._archive(
            {"../outside.txt": b"bad"}
        ) as archive:
            with self.assertRaises(ValueError):
                _safe_extract_zip(archive, Path(tmp))

    def test_rejects_windows_drive_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self._archive(
            {"C:/outside.txt": b"bad"}
        ) as archive:
            with self.assertRaises(ValueError):
                _safe_extract_zip(archive, Path(tmp))


class SettingsTests(unittest.TestCase):
    def test_save_is_valid_json_and_leaves_no_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            AppSettings(selected_strategy="general").save(path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["selected_strategy"], "general")
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_non_object_json_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(AppSettings.load(path), AppSettings())


class ProtocolTests(unittest.TestCase):
    def test_test_state_round_trip(self) -> None:
        original = DaemonStatus(True, "running", "General", "", 42, tests_running=True)
        self.assertEqual(status_from_dict(status_to_dict(original)), original)

    def test_effective_status_uses_daemon_test_state(self) -> None:
        remote = DaemonStatus(False, "idle", "", "", None, tests_running=True)
        with (
            patch("src.daemon.ipc.is_daemon_running", return_value=True),
            patch("src.daemon.ipc.daemon_status", return_value=remote),
        ):
            self.assertTrue(get_effective_runtime_status().tests_running)


class WindowLaunchTests(unittest.TestCase):
    def test_tray_flag_starts_hidden(self) -> None:
        self.assertTrue(should_start_hidden(["run.py", "--ui", "--tray"]))

    def test_explicit_ui_flag_starts_visible(self) -> None:
        self.assertFalse(should_start_hidden(["run.py", "--ui"]))

    def test_start_minimized_skips_gui_without_ui_flag(self) -> None:
        settings = AppSettings(start_minimized_to_tray=True)
        with (
            patch("src.modules.lifecycle.public.is_runtime_available", return_value=True),
            patch("src.core.settings.get_settings", return_value=settings),
        ):
            self.assertFalse(should_launch_gui(["Tigo.exe"]))


class RuntimeBootstrapTests(unittest.TestCase):
    def test_existing_runtime_skips_download(self) -> None:
        with (
            patch("src.modules.updates.service.runtime_installed", return_value=True),
            patch("src.modules.updates.service.fetch_latest_release_asset_url") as fetch,
        ):
            self.assertTrue(ensure_runtime_installed().ok)
            fetch.assert_not_called()

    def test_missing_runtime_is_installed_independently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = root / "staging"
            source = staging / "source"
            source.mkdir(parents=True)
            runtime_version = root / "runtime-version.txt"
            installed = False

            def install_runtime(_source: Path) -> None:
                nonlocal installed
                installed = True

            with (
                patch(
                    "src.modules.updates.service.runtime_installed",
                    side_effect=lambda: installed,
                ),
                patch(
                    "src.modules.updates.service.fetch_latest_release_asset_url",
                    return_value=("1.10.1", "https://example.invalid/release.zip"),
                ),
                patch(
                    "src.modules.updates.service.download_release_to_staging",
                    return_value=source,
                ),
                patch(
                    "src.modules.updates.service.transform_runtime",
                    side_effect=install_runtime,
                ),
                patch("src.modules.updates.service.staging_dir", return_value=staging),
                patch(
                    "src.modules.updates.service.runtime_version_path",
                    return_value=runtime_version,
                ),
            ):
                result = ensure_runtime_installed()

            self.assertTrue(result.ok)
            self.assertEqual(runtime_version.read_text(encoding="utf-8"), "1.10.1\n")


if __name__ == "__main__":
    unittest.main()
