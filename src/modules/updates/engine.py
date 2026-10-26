"""Install the winws2 engine from the official zapret2 release (bol-van/zapret2).

Flowseal still ships strategies, lists and fake .bin files for winws1; the engine
itself (winws2.exe, the patched WinDivert.dll, cygwin and the Lua library)
comes from zapret2. The archive is checked against the sha256 digest GitHub
publishes for the asset, the binaries also against the release's sha256sum.txt.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from src.core.debug_log import debug, info
from src.core.paths import (
    ENGINE_BIN_FILES,
    ENGINE_LUA_FILES,
    LEGACY_ENGINE_EXE,
    ZAPRET2_RELEASE_API,
    bin_dir,
    engine_version_path,
    lua_dir,
    temp_dir,
)
from src.modules.updates.github import _client, is_remote_newer

MAX_ENGINE_ARCHIVE_BYTES = 64 * 1024 * 1024
_BIN_PREFIX = "binaries/windows-x86_64/"
_LUA_PREFIX = "lua/"


@dataclass(frozen=True)
class EngineRelease:
    tag: str
    archive_url: str
    archive_name: str
    archive_sha256: str
    checksums_url: str


def installed_engine_version() -> str | None:
    try:
        return engine_version_path().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def fetch_engine_release() -> EngineRelease | None:
    try:
        with _client() as client:
            response = client.get(ZAPRET2_RELEASE_API)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # noqa: BLE001
        debug("engine", f"release lookup failed: {exc}", level="error")
        return None
    tag = str(data.get("tag_name") or "").strip()
    archive: tuple[str, str, str] | None = None
    checksums: str | None = None
    for asset in data.get("assets", []):
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        lowered = name.lower()
        if lowered == "sha256sum.txt":
            checksums = url
        elif lowered.endswith(".zip") and lowered.startswith("zapret2-") and "openwrt" not in lowered:
            archive = (name, url, _asset_sha256(asset))
    if not tag or archive is None or checksums is None or not archive[2]:
        return None
    return EngineRelease(
        tag=tag,
        archive_url=archive[1],
        archive_name=archive[0],
        archive_sha256=archive[2],
        checksums_url=checksums,
    )


def _asset_sha256(asset: dict) -> str:
    """GitHub publishes ``digest: "sha256:<hex>"`` for every release asset."""
    algorithm, _, value = str(asset.get("digest") or "").partition(":")
    value = value.strip().lower()
    if algorithm.lower() == "sha256" and _is_sha256(value):
        return value
    return ""


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def engine_update_available() -> EngineRelease | None:
    release = fetch_engine_release()
    if release and is_remote_newer(installed_engine_version(), release.tag):
        return release
    return None


def parse_checksums(text: str) -> dict[str, str]:
    """``sha256sum`` output of the files inside the archive, keyed without the top folder."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        digest, _, path = line.strip().partition(" ")
        path = path.strip().lstrip("*")
        if _is_sha256(digest.lower()) and path:
            result["/".join(PurePosixPath(path).parts[1:])] = digest.lower()
    return result


def _download(release: EngineRelease, destination: Path) -> dict[str, str]:
    """Download the archive, check it against the GitHub digest, return the per-file sums."""
    with _client() as client:
        checksums = client.get(release.checksums_url)
        checksums.raise_for_status()
        digest = hashlib.sha256()
        size = 0
        with client.stream("GET", release.archive_url) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_ENGINE_ARCHIVE_BYTES:
                        raise ValueError("Архив zapret2 превышает допустимый размер.")
                    digest.update(chunk)
                    handle.write(chunk)
    if digest.hexdigest() != release.archive_sha256:
        raise ValueError("Контрольная сумма архива zapret2 не совпала.")
    return parse_checksums(checksums.text)


def _engine_members(archive: zipfile.ZipFile) -> dict[Path, tuple[str, zipfile.ZipInfo]]:
    """Map destination paths to (archive path without top folder, entry)."""
    wanted = {_BIN_PREFIX + name: bin_dir() / name for name in ENGINE_BIN_FILES}
    wanted.update({_LUA_PREFIX + name: lua_dir() / name for name in ENGINE_LUA_FILES})
    found: dict[Path, tuple[str, zipfile.ZipInfo]] = {}
    for item in archive.infolist():
        parts = PurePosixPath(item.filename.replace("\\", "/")).parts
        relative = "/".join(parts[1:])
        if relative in wanted and not item.is_dir():
            found[wanted[relative]] = (relative, item)
    missing = sorted(key for key, path in wanted.items() if path not in found)
    if missing:
        raise ValueError(f"В архиве zapret2 нет файлов: {', '.join(missing)}.")
    return found


def install_engine_archive(archive_path: Path, tag: str, checksums: dict[str, str]) -> None:
    """Replace engine files atomically per file; old winws.exe is removed afterwards.

    Binaries must match the author's sha256sum.txt; the Lua files are not listed
    there and rely on the archive digest checked in _download.
    """
    with zipfile.ZipFile(archive_path, "r") as archive:
        members = _engine_members(archive)
        staged: list[tuple[Path, Path]] = []
        try:
            for target, (relative, item) in members.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                partial = target.with_name(target.name + ".partial")
                digest = hashlib.sha256()
                with archive.open(item, "r") as source, partial.open("wb") as output:
                    while chunk := source.read(1024 * 1024):
                        digest.update(chunk)
                        output.write(chunk)
                staged.append((partial, target))
                if relative.startswith(_BIN_PREFIX) and checksums.get(relative) != digest.hexdigest():
                    raise ValueError(f"Контрольная сумма {relative} не совпадает с sha256sum.txt.")
            for partial, target in staged:
                os.replace(partial, target)
        finally:
            for partial, _target in staged:
                partial.unlink(missing_ok=True)
    (bin_dir() / LEGACY_ENGINE_EXE).unlink(missing_ok=True)
    engine_version_path().write_text(tag + "\n", encoding="utf-8")


def install_engine(release: EngineRelease | None = None) -> str:
    """Download and install the engine; return the installed tag."""
    release = release or fetch_engine_release()
    if release is None:
        raise RuntimeError("Не удалось найти релиз zapret2 на GitHub.")
    work = temp_dir() / "engine"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    try:
        archive_path = work / release.archive_name
        checksums = _download(release, archive_path)
        install_engine_archive(archive_path, release.tag, checksums)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    info("engine", f"installed zapret2 {release.tag}")
    return release.tag
