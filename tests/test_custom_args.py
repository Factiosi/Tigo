from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.settings import AppSettings
from src.modules.strategies.launcher import resolve_custom_args


class CustomArgsTests(unittest.TestCase):
    def test_user_lists_absolute_paths_and_fakes(self) -> None:
        settings = AppSettings(active_version="1.10.4", game_filter="all")
        with (
            patch("src.modules.strategies.launcher.get_settings", return_value=settings),
            patch("src.modules.strategies.launcher.flowseal_user_lists_dir", return_value=Path(r"C:\U")),
            patch("src.modules.strategies.launcher.flowseal_version_lists_dir", return_value=Path(r"C:\V")),
            patch("src.modules.strategies.launcher.flowseal_fake_bin_dir", return_value=Path(r"C:\B")),
            patch("src.modules.strategies.launcher.get_game_filter_ports", return_value=("1024-65535", "12")),
        ):
            args = resolve_custom_args(
                '--hostlist="%LISTS%list-general-user.txt" --hostlist="%LISTS%list-general.txt" '
                '--hostlist="C:\\Users\\User\\Documents\\zapret\\list-general-user.txt" '
                '--dpi-desync-fake-tls="%BIN%stun.bin" --filter-tcp=%GameFilterTCP%'
            )
        self.assertIn(r'--hostlist="C:\U\list-general-user.txt"', args)
        self.assertIn(r'--hostlist="C:\V\list-general.txt"', args)
        self.assertIn(r'--hostlist="C:\Users\User\Documents\zapret\list-general-user.txt"', args)
        self.assertIn(r'--dpi-desync-fake-tls="C:\B\stun.bin"', args)
        self.assertIn("--filter-tcp=1024-65535", args)


if __name__ == "__main__":
    unittest.main()
