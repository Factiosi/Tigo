"""Tigo entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _require_dependencies(*, include_flet: bool = True) -> None:
    try:
        import httpx  # noqa: F401
        if include_flet:
            import flet as ft  # noqa: F401
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        print(
            f"Не найден модуль '{missing}' для {sys.executable}\n\n"
            "Зависимости, скорее всего, установлены в другой версии Python.\n"
            "Используйте один из вариантов:\n"
            f"  {sys.executable} -m pip install -r requirements.txt\n"
            "  py -3.12 -m venv .venv && .venv\\Scripts\\python -m pip install -r requirements.txt\n"
            f"  {sys.executable} run.py\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def _configure_flet_desktop() -> None:
    """Point Flet at bundled desktop client in standalone Nuitka builds."""
    if not getattr(sys, "frozen", False):
        return
    from src.core.paths import program_root

    flet_view = program_root() / "flet"
    if (flet_view / "flet.exe").exists():
        os.environ.setdefault("FLET_VIEW_PATH", str(flet_view))


def _is_daemon_mode(argv: list[str]) -> bool:
    return "--daemon" in argv


def _is_debug_console_mode(argv: list[str]) -> bool:
    return "--debug-console" in argv


def main() -> None:
    argv = sys.argv
    if _is_debug_console_mode(argv):
        _require_dependencies(include_flet=True)
        import flet as ft

        _configure_flet_desktop()
        from debug_console_app import main as debug_console_main

        ft.run(debug_console_main)
        return

    if _is_daemon_mode(argv):
        _require_dependencies(include_flet=False)
        try:
            import pystray  # noqa: F401
            from PIL import Image  # noqa: F401
        except ModuleNotFoundError as exc:
            print(
                f"Для daemon нужны pystray и Pillow: {exc.name}\n"
                f"  {sys.executable} -m pip install -r requirements.txt",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        from src.core.admin import ensure_admin, is_admin
        from src.core.paths import APP_NAME
        from src.core.debug_log import info as log_info

        log_info("bootstrap", f"starting {APP_NAME} daemon")
        if not is_admin():
            if not ensure_admin():
                sys.exit(0)
            sys.exit(0)
        from src.daemon.main import run_daemon

        run_daemon()
        return

    _require_dependencies(include_flet=True)
    import flet as ft

    from src.core.admin import ensure_admin, is_admin
    from src.core.debug_log import info as log_info
    from src.core.paths import APP_NAME, ensure_layout, program_root
    from src.core.settings import get_settings
    from src.daemon.ipc import register_gui_with_daemon
    from src.modules.lifecycle.public import require_daemon_for_gui
    from src.ui.app import main as ui_main

    log_info("bootstrap", f"starting {APP_NAME} GUI")
    get_settings()
    ensure_layout()

    if not is_admin():
        log_info("bootstrap", "elevation required")
        if not ensure_admin():
            sys.exit(0)
        sys.exit(0)

    require_daemon_for_gui()
    log_info("bootstrap", "daemon ready")
    register_gui_with_daemon(os.getpid())

    _configure_flet_desktop()
    log_info("bootstrap", "launching UI")
    ft.run(ui_main, assets_dir=str(program_root()))


if __name__ == "__main__":
    main()
