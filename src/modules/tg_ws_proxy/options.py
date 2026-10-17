"""Порт, адреса DC и ссылка Telegram. Остальные параметры прокси сюда не входят."""

from __future__ import annotations

from src.modules.tg_ws_proxy.proxy.config import parse_dc_ip_list

HOST = "127.0.0.1"
DEFAULT_PORT = 1443
DEFAULT_DC_IP = ("2:149.154.167.220", "4:149.154.167.220")


def dc_lines(value: object) -> list[str]:
    if isinstance(value, list):
        lines = [str(item).strip() for item in value if str(item).strip()]
        if lines:
            return lines
    return list(DEFAULT_DC_IP)


def validate_port(value: object) -> str | None:
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError):
        return "Порт должен быть числом от 1 до 65535."
    if not 1 <= port <= 65535:
        return "Порт должен быть числом от 1 до 65535."
    return None


def validate_dc_ip(lines: list[str]) -> str | None:
    if not lines:
        return "Укажите хотя бы один адрес дата-центра."
    try:
        parsed = parse_dc_ip_list(lines)
    except ValueError:
        return "Адрес дата-центра записывается как номер и IPv4, например 2:149.154.167.220."
    if not parsed:
        return "Укажите хотя бы один адрес дата-центра."
    return None


def telegram_link(port: int, secret: str) -> str:
    return f"tg://proxy?server={HOST}&port={port}&secret=dd{secret}"
