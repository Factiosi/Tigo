"""Ready-made sets of hosts entries."""

from __future__ import annotations

from dataclasses import dataclass

BLOCKED_IP = "0.0.0.0"
TELEGRAM_WEB_IP = "149.154.167.220"


@dataclass(frozen=True)
class HostsPreset:
    id: str
    title: str
    description: str
    ip: str
    domains: tuple[str, ...]

    def rows(self) -> list[tuple[str, str]]:
        return [(self.ip, domain) for domain in self.domains]


PRESETS: tuple[HostsPreset, ...] = (
    HostsPreset(
        id="telegram-web",
        title="Telegram в браузере",
        description=f"web.telegram.org, t.me и загрузка Telegram Desktop через {TELEGRAM_WEB_IP}.",
        ip=TELEGRAM_WEB_IP,
        domains=(
            "telegram.org",
            "core.telegram.org",
            "my.telegram.org",
            "oauth.telegram.org",
            "desktop.telegram.org",
            "macos.telegram.org",
            "api.telegram.org",
            "td.telegram.org",
            "web.telegram.org",
            "venus.web.telegram.org",
            "venus-1.web.telegram.org",
            "vesta.web.telegram.org",
            "vesta-1.web.telegram.org",
            "kws2.web.telegram.org",
            "kws2-1.web.telegram.org",
            "kws4.web.telegram.org",
            "kws4-1.web.telegram.org",
            "zws2.web.telegram.org",
            "zws2-1.web.telegram.org",
            "zws4.web.telegram.org",
            "zws4-1.web.telegram.org",
            "t.me",
            "telegram.me",
            "telegram.dog",
            "telegram.space",
            "telesco.pe",
            "cdn.telesco.pe",
            "cdn1.telesco.pe",
            "cdn2.telesco.pe",
            "cdn3.telesco.pe",
            "cdn4.telesco.pe",
            "cdn5.telesco.pe",
            "cdn6.telesco.pe",
            "tg.dev",
            "oauth.tg.dev",
        ),
    ),
    HostsPreset(
        id="block-max",
        title="Заблокировать MAX",
        description="Мессенджер MAX не сможет подключиться, обновиться и скачать установщик.",
        ip=BLOCKED_IP,
        domains=(
            "max.ru",
            "web.max.ru",
            "api.max.ru",
            "cdn.max.ru",
            "download.max.ru",
            "update.max.ru",
            "oneme.com",
            "download.oneme.com",
        ),
    ),
    HostsPreset(
        id="block-state-media",
        title="Заблокировать гос. СМИ",
        description="ТАСС, РИА Новости, Sputnik, RT, ВГТРК, «Российская газета», «Звезда», Первый канал.",
        ip=BLOCKED_IP,
        domains=(
            "tass.ru",
            "www.tass.ru",
            "tass.com",
            "www.tass.com",
            "ria.ru",
            "www.ria.ru",
            "radiosputnik.ru",
            "www.radiosputnik.ru",
            "sputnikglobe.com",
            "www.sputnikglobe.com",
            "rt.com",
            "www.rt.com",
            "russian.rt.com",
            "vgtrk.ru",
            "www.vgtrk.ru",
            "vesti.ru",
            "www.vesti.ru",
            "smotrim.ru",
            "www.smotrim.ru",
            "rg.ru",
            "www.rg.ru",
            "pnp.ru",
            "www.pnp.ru",
            "tvzvezda.ru",
            "www.tvzvezda.ru",
            "1tv.ru",
            "www.1tv.ru",
            "1tv.com",
            "www.1tv.com",
        ),
    ),
)
