from __future__ import annotations

import unittest
from unittest.mock import patch

from src.core.process_label import label_flet_view_process, set_process_description_for_pid


class ProcessLabelTests(unittest.TestCase):
    def test_label_flet_view_process_targets_flet_child(self) -> None:
        with (
            patch("src.core.process_label.sys.platform", "win32"),
            patch(
                "src.core.process_label._iter_child_processes",
                return_value=[(111, "flet.exe"), (222, "Tigo.exe")],
            ),
            patch("src.core.process_label.set_process_description_for_pid") as set_pid,
        ):
            labeled = label_flet_view_process("Tigo GUI", parent_pid=99)

        self.assertTrue(labeled)
        set_pid.assert_called_once_with(111, "Tigo GUI")

    def test_label_flet_view_process_ignores_non_flet_children(self) -> None:
        with (
            patch("src.core.process_label.sys.platform", "win32"),
            patch(
                "src.core.process_label._iter_child_processes",
                return_value=[(222, "Tigo.exe")],
            ),
            patch("src.core.process_label.set_process_description_for_pid") as set_pid,
        ):
            labeled = label_flet_view_process("Tigo GUI")

        self.assertFalse(labeled)
        set_pid.assert_not_called()

    def test_set_process_description_for_pid_rejects_invalid_pid(self) -> None:
        with patch("src.core.process_label.sys.platform", "win32"):
            self.assertFalse(set_process_description_for_pid(0, "Tigo GUI"))


if __name__ == "__main__":
    unittest.main()
