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


class SyncProbeTests(unittest.TestCase):
    def test_sync_probe_during_tests_marks_running_winws(self) -> None:
        from src.kernel import runtime_state

        runtime_state.mark_stopped()
        runtime_state.set_tests_running(True)
        try:
            runtime_state.sync_probe(True, 4242, strategy_name="General")
            status = runtime_state.get_status()
            self.assertTrue(status.running)
            self.assertEqual(status.pid, 4242)
        finally:
            runtime_state.set_tests_running(False)
            runtime_state.mark_stopped()


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
            patch("src.modules.updates.service.engine_update_available") as check,
            patch("src.modules.updates.service.install_engine") as install,
        ):
            self.assertTrue(ensure_runtime_installed().ok)
            check.assert_not_called()
            install.assert_not_called()

    def test_missing_runtime_is_installed_independently(self) -> None:
        installed = False

        def install(_release) -> str:
            nonlocal installed
            installed = True
            return "v1.0.6"

        with (
            patch("src.modules.updates.service.runtime_installed", side_effect=lambda: installed),
            patch("src.modules.updates.service.install_engine", side_effect=install),
        ):
            result = ensure_runtime_installed()

        self.assertTrue(result.ok)
        self.assertEqual(result.applied_tag, "v1.0.6")

    def test_update_is_skipped_while_winws2_runs(self) -> None:
        with (
            patch("src.modules.updates.service.runtime_installed", return_value=True),
            patch("src.modules.updates.service.is_canonical_winws_running", return_value=(True, 42)),
            patch("src.modules.updates.service.engine_update_available") as check,
        ):
            self.assertTrue(ensure_runtime_installed(allow_update=True).ok)
            check.assert_not_called()

    def test_failed_update_keeps_installed_engine(self) -> None:
        with (
            patch("src.modules.updates.service.runtime_installed", return_value=True),
            patch("src.modules.updates.service.is_canonical_winws_running", return_value=(False, None)),
            patch("src.modules.updates.service.engine_update_available", return_value=object()),
            patch("src.modules.updates.service.install_engine", side_effect=OSError("locked")),
        ):
            result = ensure_runtime_installed(allow_update=True)
        self.assertTrue(result.ok)
        self.assertIn("locked", result.message)


if __name__ == "__main__":
    unittest.main()
