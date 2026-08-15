"""Windows administrator elevation."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from src.core.debug_log import debug
from src.core.paths import APP_NAME


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def _build_elevated_launch(*, include_elevated_flag: bool = True) -> tuple[str, str]:
    args = [arg for arg in sys.argv[1:] if arg != "--elevated"]
    if include_elevated_flag:
        args.append("--elevated")
    arg_text = " ".join(f'"{arg}"' if " " in arg else arg for arg in args)

    from src.core.paths import is_packaged_app

    if is_packaged_app():
        return sys.executable, arg_text

    script = Path(sys.argv[0]).resolve()
    params = f'"{script}"'
    if arg_text:
        params = f"{params} {arg_text}"
    return sys.executable, params


def _shell_execute_runas(executable: str, params: str) -> bool:
    ret = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        params,
        None,
        1,
    )
    return ret > 32


def request_admin_restart() -> bool:
    if is_admin():
        return True

    if "--elevated" in sys.argv:
        debug("bootstrap", "elevation failed after --elevated; retrying runas once", level="warn")
        executable, params = _build_elevated_launch(include_elevated_flag=False)
        if _shell_execute_runas(executable, params):
            return True
        ctypes.windll.user32.MessageBoxW(
            None,
            f"Установка завершена.\n\n"
            f"Запустите {APP_NAME} из меню «Пуск» или с рабочего стола.",
            f"{APP_NAME}",
            0x40,
        )
        return False

    result = ctypes.windll.user32.MessageBoxW(
        None,
        f"{APP_NAME} требует права администратора для управления сервисом zapret.\n\n"
        "Нажмите OK для перезапуска с правами администратора.",
        f"{APP_NAME} — требуются права администратора",
        0x41,
    )
    if result != 1:
        return False

    executable, params = _build_elevated_launch()
    return _shell_execute_runas(executable, params)


def ensure_admin() -> bool:
    if is_admin():
        return True
    return request_admin_restart()
