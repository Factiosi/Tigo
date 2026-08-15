from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.modules.strategy_testing.runner import (
    StrategyTestJob,
    StrategyTestRunner,
    _FilterSnapshot,
    _restore_filter_snapshot,
)


class FilterRestoreTests(unittest.TestCase):
    def test_restore_reapplies_filters_and_restarts_strategy(self) -> None:
        snapshot = _FilterSnapshot(
            version="1.0.0",
            game_filter="tcp",
            ipset_filter="loaded",
            was_running=True,
            selected_strategy="general",
            strategy_source="flowseal",
            custom_strategy_args="",
        )
        with patch("src.modules.strategy_testing.runner.apply_game_filter") as apply_gf, patch(
            "src.modules.strategy_testing.runner.apply_ipset_mode"
        ) as apply_ip, patch(
            "src.modules.strategy_testing.runner.list_strategies",
            return_value=[MagicMock(id="general")],
        ), patch(
            "src.modules.strategy_testing.runner.start_strategy",
            return_value=(True, "ok"),
        ) as start:
            _restore_filter_snapshot(snapshot)

        apply_gf.assert_called_once_with("1.0.0", "tcp")
        apply_ip.assert_called_once_with("1.0.0", "loaded")
        start.assert_called_once()

    def test_run_job_captures_filter_snapshot(self) -> None:
        runner = StrategyTestRunner()
        job = StrategyTestJob("1.0.0", "standard", ["general"])
        strategy = MagicMock(id="general", display_name="General")
        with patch(
            "src.modules.strategy_testing.runner.list_strategies",
            return_value=[strategy],
        ), patch(
            "src.modules.strategy_testing.runner.ensure_runtime_preflight",
            return_value=(True, ""),
        ), patch(
            "src.modules.strategy_testing.runner._capture_filter_snapshot",
            return_value=_FilterSnapshot(
                version="1.0.0",
                game_filter="off",
                ipset_filter="loaded",
                was_running=False,
                selected_strategy=None,
                strategy_source="flowseal",
                custom_strategy_args="",
            ),
        ) as capture, patch(
            "src.modules.strategy_testing.runner.runtime_state.set_tests_running"
        ), patch(
            "src.modules.strategy_testing.runner.stop_strategy"
        ), patch(
            "src.modules.strategy_testing.runner.tr.begin_test_run"
        ), patch(
            "src.modules.strategy_testing.runner.read_game_filter_mode",
            return_value="off",
        ), patch(
            "src.modules.strategy_testing.runner.get_runner"
        ) as get_runner, patch(
            "src.modules.strategy_testing.runner.build_winws_launch",
            return_value=(None, "stop early"),
        ):
            runner._stop_requested = True
            runner._run_job(job)

        capture.assert_called_once_with("1.0.0")
        self.assertEqual(runner._filter_snapshot.version, "1.0.0")
