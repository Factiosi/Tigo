from __future__ import annotations

import sqlite3
import tempfile
from contextlib import closing
import unittest
from pathlib import Path
from unittest.mock import patch

from src.modules.hosts.catalog import CatalogError, catalog_version, load_catalog, service_rows
from src.modules.hosts.hosts_file import set_block, summarize
from src.modules.hosts.service import _services_text, service_block_id

SCHEMA = """
CREATE TABLE catalog_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE services(service_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
    kind TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1,
    icon_name TEXT NOT NULL DEFAULT '', icon_color TEXT);
CREATE TABLE dns_profiles(profile_id TEXT PRIMARY KEY, name TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1);
CREATE TABLE domains(domain_id INTEGER PRIMARY KEY, service_id TEXT NOT NULL, hostname TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0);
CREATE TABLE dns_answers(domain_id INTEGER NOT NULL, profile_id TEXT NOT NULL, ip_address TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0);
CREATE TABLE hosts_entries(entry_id INTEGER PRIMARY KEY, service_id TEXT NOT NULL, hostname TEXT NOT NULL,
    ip_address TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 0);
"""


def build_catalog(path: Path, *, version: str = "2026.10.21.1", schema: str = "1") -> Path:
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(SCHEMA)
        db.executemany("INSERT INTO catalog_meta VALUES (?, ?)", [("schema_version", schema), ("catalog_version", version)])
        db.executemany(
            "INSERT INTO dns_profiles VALUES (?, ?, ?, 1)",
            [("zapret_dns", "Zapret DNS", -1), ("xbox_dns", "XBOX DNS", 0), ("comss_dns", "Comss DNS", 2)],
        )
        db.executemany(
            "INSERT INTO services VALUES (?, ?, ?, ?, ?, ?, '', NULL)",
            [
                ("dns.chat", "Chat", "ai", "dns", 0, 1),
                ("dns.off", "Disabled", "other", "dns", 1, 0),
                ("dns.comss_only", "Comss only", "other", "dns", 2, 1),
                ("hosts.direct", "Direct", "direct", "hosts", 3, 1),
            ],
        )
        db.executemany(
            "INSERT INTO domains VALUES (?, ?, ?, ?)",
            [(1, "dns.chat", "chat.example", 0), (2, "dns.chat", "api.chat.example", 1), (3, "dns.chat", "staging.chat.example", 2),
             (4, "dns.comss_only", "c.example", 0)],
        )
        db.executemany(
            "INSERT INTO dns_answers VALUES (?, ?, ?, ?)",
            [
                (1, "zapret_dns", "83.217.211.149", 0),
                (1, "xbox_dns", "104.18.22.222", 1),
                (1, "xbox_dns", "104.18.23.222", 0),
                (2, "zapret_dns", "83.217.211.149", 0),  # no xbox answer -> falls back
                (3, "zapret_dns", "10.0.0.5", 0),  # private -> dropped
                (4, "comss_dns", "91.132.224.167", 0),
            ],
        )
        db.executemany(
            "INSERT INTO hosts_entries VALUES (?, ?, ?, ?, ?)",
            [
                (1, "hosts.direct", "d.example", "23.227.38.74", 1),
                (2, "hosts.direct", "d.example", "23.227.38.75", 0),
                (3, "hosts.direct", "d.example", "2606:4700::1", 0),
            ],
        )
    return path


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = build_catalog(Path(self._tmp.name) / "c.sqlite3")
        self.catalog = load_catalog(self.path)

    def test_disabled_services_are_skipped(self) -> None:
        self.assertEqual([pid for pid, _ in self.catalog.profiles], ["zapret_dns", "xbox_dns", "comss_dns"])
        self.assertEqual([s.id for s in self.catalog.services], ["dns.chat", "dns.comss_only", "hosts.direct"])
        self.assertEqual(self.catalog.service("dns.chat").domains, 3)
        self.assertEqual(self.catalog.service("dns.comss_only").profiles, ("comss_dns",))

    def test_profile_rows_with_fallback_and_private_filter(self) -> None:
        rows = service_rows(self.catalog, "dns.chat", "xbox_dns", ipv6=False)
        self.assertEqual(rows, [("104.18.23.222", "chat.example"), ("83.217.211.149", "api.chat.example")])

    def test_direct_rows_take_best_priority_and_gate_ipv6(self) -> None:
        self.assertEqual(service_rows(self.catalog, "hosts.direct", "hosts", ipv6=False), [("23.227.38.75", "d.example")])
        self.assertEqual(
            service_rows(self.catalog, "hosts.direct", "hosts", ipv6=True),
            [("23.227.38.75", "d.example"), ("2606:4700::1", "d.example")],
        )

    def test_unsupported_schema_is_rejected(self) -> None:
        other = build_catalog(Path(self._tmp.name) / "o.sqlite3", schema="2")
        with self.assertRaises(CatalogError):
            catalog_version(other)

    def test_services_text_replaces_and_drops_stale_blocks(self) -> None:
        text = set_block("127.0.0.1 local.test\r\n", service_block_id("dns.gone"), [("1.2.3.4", "gone.example")])
        text, written, empty = _services_text(text, {"dns.chat": "zapret_dns"}, self.catalog, ipv6=False)
        blocks = summarize(text).blocks
        self.assertNotIn(service_block_id("dns.gone"), blocks)
        self.assertEqual(blocks[service_block_id("dns.chat")], 2)
        self.assertEqual((written, empty), (2, []))
        self.assertIn("127.0.0.1 local.test", text)

    def test_catalog_file_is_closed_after_reading(self) -> None:
        load_catalog(self.path)
        service_rows(self.catalog, "dns.chat", "zapret_dns", ipv6=False)
        moved = self.path.with_suffix(".moved")
        self.path.replace(moved)  # fails on Windows while a connection is open
        self.assertTrue(moved.exists())


class SettingsFieldTests(unittest.TestCase):
    def test_hosts_selection_round_trips(self) -> None:
        from src.core.settings import AppSettings

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            AppSettings(hosts_services={"dns.chat": "zapret_dns"}, hosts_profile="xbox_dns").save(path)
            loaded = AppSettings.load(path)
            self.assertEqual(loaded.hosts_services, {"dns.chat": "zapret_dns"})
            self.assertEqual(loaded.hosts_profile, "xbox_dns")


if __name__ == "__main__":
    unittest.main()
