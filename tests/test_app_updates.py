from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.modules.updates.app import (
    AppUpdate,
    _version_tuple,
    download_verified_installer,
    fetch_app_update,
    launch_installer,
)


class AppUpdateTests(unittest.TestCase):
    def test_semver_comparison_is_numeric(self) -> None:
        self.assertGreater(_version_tuple("1.10.0"), _version_tuple("1.9.9"))

    def test_release_requires_installer_and_checksum(self) -> None:
        response = MagicMock()
        response.json.return_value = {
            "assets": [
                {
                    "name": "Tigo-Setup-9.9.9.exe",
                    "browser_download_url": "https://example.test/setup.exe",
                },
                {
                    "name": "Tigo-Setup-9.9.9.exe.sha256",
                    "browser_download_url": "https://example.test/setup.sha256",
                },
            ]
        }
        client = MagicMock()
        client.__enter__.return_value.get.return_value = response
        client.__exit__.return_value = None
        with patch("src.modules.updates.app.httpx.Client", return_value=client):
            update = fetch_app_update()

        self.assertIsNotNone(update)
        self.assertEqual(update.version, "9.9.9")

    def test_download_rejects_invalid_checksum(self) -> None:
        update = AppUpdate(
            "9.9.9",
            "https://example.test/setup.exe",
            "https://example.test/setup.sha256",
            "Tigo-Setup-9.9.9.exe",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_download(_client, url: str, destination: Path) -> None:
                destination.write_bytes(b"installer" if url.endswith(".exe") else b"0" * 64)

            with (
                patch("src.modules.updates.app.temp_dir", return_value=root),
                patch("src.modules.updates.app._download", side_effect=fake_download),
            ):
                with self.assertRaises(ValueError):
                    download_verified_installer(update)

    def test_download_accepts_matching_checksum(self) -> None:
        payload = b"verified installer"
        digest = hashlib.sha256(payload).hexdigest()
        update = AppUpdate(
            "9.9.9",
            "https://example.test/setup.exe",
            "https://example.test/setup.sha256",
            "Tigo-Setup-9.9.9.exe",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_download(_client, url: str, destination: Path) -> None:
                destination.write_bytes(payload if url.endswith(".exe") else digest.encode())

            with (
                patch("src.modules.updates.app.temp_dir", return_value=root),
                patch("src.modules.updates.app._download", side_effect=fake_download),
            ):
                installer = download_verified_installer(update)

            self.assertEqual(installer.read_bytes(), payload)

    def test_installer_launch_uses_silent_update_flags(self) -> None:
        installer = Path("Tigo-Setup-9.9.9.exe")
        with (
            patch("src.modules.updates.app.is_packaged_app", return_value=True),
            patch("src.modules.updates.app.subprocess.Popen") as popen,
        ):
            launch_installer(installer)

        args = popen.call_args.args[0]
        self.assertIn("/VERYSILENT", args)
        self.assertIn("/TIGORELAUNCH=1", args)


if __name__ == "__main__":
    unittest.main()
