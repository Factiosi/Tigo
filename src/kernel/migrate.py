"""Remove legacy Windows SCM zapret service on first run."""

from __future__ import annotations

from src.core.debug_log import debug
from src.core.paths import SERVICE_NAME
from src.kernel import service_api
from src.kernel.process import kill_winws
from src.kernel.windivert_cleanup import cleanup_windivert_services

_migrated = False


def migrate_legacy_service() -> None:
    global _migrated
    if _migrated:
        return
    _migrated = True
    debug("kernel", "migrate_legacy_service running")

    if service_api.service_state(SERVICE_NAME) is not None:
        service_api.delete_service(SERVICE_NAME)
    if kill_winws():
        pass
    cleanup_windivert_services()
