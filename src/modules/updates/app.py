"""Tigo application updates from verified GitHub release installers."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.core.debug_log import debug, info
from src.core.paths import TIGO_RELEASE_API, is_packaged_app, temp_dir
from src.core.version import __version__

MSG_APP_UP_TO_DATE = "У вас последняя актуальная версия Tigo"
MSG_APP_UPDATE_AVAILABLE = "Доступна новая версия Tigo"
MSG_APP_DOWNLOADING = "Новая версия Tigo доступна и скачивается"
_ASSET_RE = re.compile(r"^Tigo-Setup-(\d+\.\d+\.\d+)\.exe$", re.I)


@dataclass(frozen=True)
class AppUpdate:
    version: str
    installer_url: str
    checksum_url: str
    installer_name: str


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip(), re.I)
    if not match:
        raise ValueError(f"Некорректная версия: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def fetch_app_update() -> AppUpdate | None:
    with httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={"User-Agent": f"Tigo/{__version__}", "Cache-Control": "no-cache"},
        follow_redirects=True,
    ) as client:
        response = client.get(TIGO_RELEASE_API)
        response.raise_for_status()
        payload = response.json()

    assets = payload.get("assets")
    if not isinstance(assets, list):
        return None
    by_name = {
        str(asset.get("name") or ""): str(asset.get("browser_download_url") or "")
        for asset in assets
        if isinstance(asset, dict)
    }
    for name, url in by_name.items():
        match = _ASSET_RE.fullmatch(name)
        if not match or not url:
            continue
        version = match.group(1)
        checksum_name = f"{name}.sha256"
        checksum_url = by_name.get(checksum_name)
        if checksum_url and _version_tuple(version) > _version_tuple(__version__):
            return AppUpdate(version, url, checksum_url, name)
    return None


def _download(client: httpx.Client, url: str, destination: Path) -> None:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


def download_verified_installer(update: AppUpdate) -> Path:
    update_dir = temp_dir() / "app-update"
    update_dir.mkdir(parents=True, exist_ok=True)
    installer = update_dir / update.installer_name
    checksum_file = update_dir / f"{update.installer_name}.sha256"
    with httpx.Client(
        timeout=httpx.Timeout(300.0, connect=15.0),
        headers={"User-Agent": f"Tigo/{__version__}"},
        follow_redirects=True,
    ) as client:
        _download(client, update.installer_url, installer)
        _download(client, update.checksum_url, checksum_file)

    expected = checksum_file.read_text(encoding="utf-8", errors="replace").strip().split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        installer.unlink(missing_ok=True)
        raise ValueError("Файл контрольной суммы релиза повреждён.")
    actual = hashlib.sha256(installer.read_bytes()).hexdigest()
    if actual != expected:
        installer.unlink(missing_ok=True)
        raise ValueError("SHA-256 установщика не совпадает с опубликованной суммой.")
    return installer


def launch_installer(installer: Path) -> None:
    if not is_packaged_app():
        raise RuntimeError("Автоустановка доступна только в собранной версии Tigo.")
    creationflags = (
        subprocess.CREATE_NO_WINDOW
        | getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    )
    subprocess.Popen(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
            "/FORCECLOSEAPPLICATIONS",
            "/TIGORELAUNCH=1",
        ],
        cwd=str(installer.parent),
        creationflags=creationflags,
        close_fds=True,
    )
    info("app_updates", f"launched verified installer {installer.name}")


def check_app_only() -> tuple[bool, str, str]:
    try:
        update = fetch_app_update()
    except Exception as exc:  # noqa: BLE001
        debug("app_updates", f"check failed: {exc}", level="error")
        return False, f"Не удалось проверить обновления Tigo: {exc}", "error"
    if update is None:
        return True, MSG_APP_UP_TO_DATE, "success"
    return True, f"{MSG_APP_UPDATE_AVAILABLE}: {update.version}", "warning"


def check_and_install_app() -> tuple[bool, str, str]:
    try:
        update = fetch_app_update()
        if update is None:
            return True, MSG_APP_UP_TO_DATE, "success"
        installer = download_verified_installer(update)
        launch_installer(installer)
        return True, f"Tigo {update.version} загружен. Запускается установка.", "success"
    except Exception as exc:  # noqa: BLE001
        debug("app_updates", f"install failed: {exc}", level="error")
        return False, f"Не удалось установить обновление Tigo: {exc}", "error"
