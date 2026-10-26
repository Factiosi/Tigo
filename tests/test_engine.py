from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.modules.updates.engine import _asset_sha256, install_engine_archive, parse_checksums


class EngineArchiveTests(unittest.TestCase):
    NAMES = (
        "binaries/windows-x86_64/winws2.exe",
        "binaries/windows-x86_64/WinDivert.dll",
        "binaries/windows-x86_64/WinDivert64.sys",
        "binaries/windows-x86_64/cygwin1.dll",
    )

    def checksums(self, *, broken: str | None = None) -> dict[str, str]:
        sums = {name: hashlib.sha256(name.encode()).hexdigest() for name in self.NAMES}
        if broken:
            sums[broken] = "0" * 64
        return sums

    def test_parse_checksums_drops_top_folder(self) -> None:
        digest = "a" * 64
        text = f"{digest}  zapret2-v1.0.6/binaries/windows-x86_64/winws2.exe\nnot a checksum line\n"
        self.assertEqual(parse_checksums(text), {"binaries/windows-x86_64/winws2.exe": digest})

    def test_asset_digest(self) -> None:
        self.assertEqual(_asset_sha256({"digest": "sha256:" + "A" * 64}), "a" * 64)
        self.assertEqual(_asset_sha256({"digest": "md5:abc"}), "")
        self.assertEqual(_asset_sha256({}), "")

    def _archive(self, path: Path, *, skip: str | None = None) -> None:
        names = [
            "binaries/windows-x86_64/winws2.exe",
            "binaries/windows-x86_64/WinDivert.dll",
            "binaries/windows-x86_64/WinDivert64.sys",
            "binaries/windows-x86_64/cygwin1.dll",
            "binaries/windows-x86/winws2.exe",
            "lua/zapret-lib.lua",
            "lua/zapret-antidpi.lua",
            "lua/zapret-auto.lua",
        ]
        with zipfile.ZipFile(path, "w") as archive:
            for name in names:
                if name != skip:
                    archive.writestr(f"zapret2-v1.0.6/{name}", name)

    def test_install_copies_only_engine_files_and_removes_winws1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "bin" / "winws.exe").write_bytes(b"old")
            self._archive(root / "z.zip")
            with (
                patch("src.modules.updates.engine.bin_dir", return_value=root / "bin"),
                patch("src.modules.updates.engine.lua_dir", return_value=root / "lua"),
                patch("src.modules.updates.engine.engine_version_path", return_value=root / "engine-version.txt"),
            ):
                install_engine_archive(root / "z.zip", "v1.0.6", self.checksums())
            self.assertEqual(
                (root / "bin" / "winws2.exe").read_text(), "binaries/windows-x86_64/winws2.exe"
            )
            self.assertFalse((root / "bin" / "winws.exe").exists())
            self.assertEqual(sorted(p.name for p in (root / "lua").iterdir()), ["zapret-antidpi.lua", "zapret-lib.lua"])
            self.assertEqual((root / "engine-version.txt").read_text(), "v1.0.6\n")

    def test_incomplete_archive_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._archive(root / "z.zip", skip="lua/zapret-lib.lua")
            with (
                patch("src.modules.updates.engine.bin_dir", return_value=root / "bin"),
                patch("src.modules.updates.engine.lua_dir", return_value=root / "lua"),
                patch("src.modules.updates.engine.engine_version_path", return_value=root / "engine-version.txt"),
            ):
                with self.assertRaises(ValueError):
                    install_engine_archive(root / "z.zip", "v1.0.6", self.checksums())
            self.assertFalse((root / "bin").exists())

    def test_checksum_mismatch_leaves_installed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "bin" / "winws2.exe").write_bytes(b"installed")
            self._archive(root / "z.zip")
            with (
                patch("src.modules.updates.engine.bin_dir", return_value=root / "bin"),
                patch("src.modules.updates.engine.lua_dir", return_value=root / "lua"),
                patch("src.modules.updates.engine.engine_version_path", return_value=root / "engine-version.txt"),
            ):
                with self.assertRaises(ValueError):
                    install_engine_archive(
                        root / "z.zip", "v1.0.6", self.checksums(broken="binaries/windows-x86_64/cygwin1.dll")
                    )
            self.assertEqual((root / "bin" / "winws2.exe").read_bytes(), b"installed")
            self.assertEqual(sorted(p.name for p in (root / "bin").iterdir()), ["winws2.exe"])


if __name__ == "__main__":
    unittest.main()
