"""Tigo application self-update (placeholder until ~1.0.1)."""

from __future__ import annotations

MSG_APP_UP_TO_DATE = "У вас последняя актуальная версия Tigo"
MSG_APP_UPDATE_AVAILABLE = "Доступна новая версия Tigo"
MSG_APP_DOWNLOADING = "Новая версия Tigo доступна и скачивается"
MSG_APP_UPDATES_UNAVAILABLE = (
    "Обновления приложения пока недоступны. Источник появится в версии 1.0.1."
)


def check_app_only() -> tuple[bool, str, str]:
    return True, MSG_APP_UPDATES_UNAVAILABLE, "info"


def check_and_install_app() -> tuple[bool, str, str]:
    return True, MSG_APP_UPDATES_UNAVAILABLE, "info"
