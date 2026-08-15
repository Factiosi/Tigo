"""DPI TCP 16-20 freeze probes (flowseal test zapret.ps1 parity)."""

from __future__ import annotations

import concurrent.futures
import re
import subprocess
from dataclasses import dataclass

from src.modules.strategy_testing.probe import (
    CREATE_NO_WINDOW,
    MAX_PARALLEL,
    TargetProbeResult,
    format_probe_lines,
)

RANGE_BYTES = 262144
TIMEOUT_SECONDS = 5
WARN_MIN_KB = 14
WARN_MAX_KB = 22

_HTTP_CODE_SIZE = re.compile(r"^(\d{3})\s+(\d+)$")
_UNSUP_PATTERN = re.compile(
    r"not supported|does not support|protocol\s+'.+'\s+not\s+supported|"
    r"unsupported protocol|TLS.not supported|Unrecognized option|Unknown option|"
    r"unsupported option|unsupported feature|schannel|SSL",
    re.I,
)


@dataclass(frozen=True)
class DpiTarget:
    target_id: str
    provider: str
    url: str


def load_dpi_targets() -> list[DpiTarget]:
    raw: list[tuple[str, str, str, int]] = [
        ("US.CF-01", "Cloudflare", "https://cdn.cookielaw.org/scripttemplates/202501.2.0/otBannerSdk.js", 1),
        ("US.CF-02", "Cloudflare", "https://genshin.jmp.blue/characters/all#", 1),
        ("US.CF-03", "Cloudflare", "https://api.frankfurter.dev/v1/2000-01-01..2002-12-31", 1),
        ("US.DO-01", "DigitalOcean", "https://genderize.io/", 2),
        ("DE.HE-01", "Hetzner", "https://j.dejure.org/jcg/doctrine/doctrine_banner.webp", 1),
        ("FI.HE-01", "Hetzner", "https://tcp1620-01.dubybot.live/1MB.bin", 1),
        ("FI.HE-02", "Hetzner", "https://tcp1620-02.dubybot.live/1MB.bin", 1),
        ("FI.HE-03", "Hetzner", "https://tcp1620-05.dubybot.live/1MB.bin", 1),
        ("FI.HE-04", "Hetzner", "https://tcp1620-06.dubybot.live/1MB.bin", 1),
        ("FR.OVH-01", "OVH", "https://eu.api.ovh.com/console/rapidoc-min.js", 1),
        ("FR.OVH-02", "OVH", "https://ovh.sfx.ovh/10M.bin", 1),
        ("SE.OR-01", "Oracle", "https://oracle.sfx.ovh/10M.bin", 1),
        ("DE.AWS-01", "AWS", "https://tms.delta.com/delta/dl_anderson/Bootstrap.js", 1),
        ("US.AWS-01", "AWS", "https://corp.kaltura.com/wp-content/cache/min/1/wp-content/themes/airfleet/dist/styles/theme.css", 1),
        ("US.GC-01", "Google Cloud", "https://api.usercentrics.eu/gvl/v3/en.json", 1),
        ("US.FST-01", "Fastly", "https://openoffice.apache.org/images/blog/rejected.png", 1),
        ("US.FST-02", "Fastly", "https://www.juniper.net/etc.clientlibs/juniper/clientlibs/clientlib-site/resources/fonts/lato/Lato-Regular.woff2", 1),
        ("PL.AKM-01", "Akamai", "https://www.lg.com/lg5-common-gp/library/jquery.min.js", 1),
        ("PL.AKM-02", "Akamai", "https://media-assets.stryker.com/is/image/stryker/gateway_1?$max_width_1410$", 1),
        ("US.CDN77-01", "CDN77", "https://cdn.eso.org/images/banner1920/eso2520a.jpg", 1),
        ("DE.CNTB-01", "Contabo", "https://cloudlets.io/wp-content/themes/Avada/includes/lib/assets/fonts/fontawesome/webfonts/fa-solid-900.woff2", 1),
        ("FR.SW-01", "Scaleway", "https://renklisigorta.com.tr/teklif-al", 1),
        ("US.CNST-01", "Constant", "https://cdn.xuansiwei.com/common/lib/font-awesome/4.7.0/fontawesome-webfont.woff2?v=4.7.0", 1),
    ]
    targets: list[DpiTarget] = []
    for target_id, provider, url, repeat in raw:
        for index in range(repeat):
            suffix = f"@{index}" if repeat > 1 else ""
            targets.append(DpiTarget(f"{target_id}{suffix}", provider, url))
    return targets


def _classify_curl(url: str, extra: list[str]) -> str:
    range_spec = f"0-{RANGE_BYTES - 1}"
    args = [
        "curl.exe",
        "-L",
        "--range",
        range_spec,
        "-m",
        str(TIMEOUT_SECONDS),
        "-w",
        "%{http_code} %{size_download}",
        "-o",
        "NUL",
        "-s",
        *extra,
        url,
    ]
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    text = (result.stdout or "").strip()
    stderr = result.stderr or ""
    code = "NA"
    size_bytes = 0

    match = _HTTP_CODE_SIZE.match(text)
    if match:
        code = match.group(1)
        size_bytes = int(match.group(2))
    elif result.returncode == 35 or _UNSUP_PATTERN.search(stderr):
        return "UNSUP"
    elif text:
        code = "ERR"

    size_kb = size_bytes / 1024
    if code == "UNSUP":
        return "UNSUP"
    if result.returncode != 0 or code in {"ERR", "NA"}:
        status = "FAIL"
    else:
        status = "OK"

    if WARN_MIN_KB <= size_kb <= WARN_MAX_KB and result.returncode != 0:
        return "LIKELY_BLOCKED"
    return status


def _probe_dpi_target(target: DpiTarget) -> TargetProbeResult:
    tokens: list[str] = []
    for label, extra in (
        ("HTTP", ["--http1.1"]),
        ("TLS1.2", ["--tlsv1.2", "--tls-max", "1.2"]),
        ("TLS1.3", ["--tlsv1.3", "--tls-max", "1.3"]),
    ):
        status = _classify_curl(target.url, extra)
        tokens.append(f"{label}:{status}")
    display_name = f"{target.target_id} [{target.provider}]"
    return TargetProbeResult(display_name, tuple(tokens), "n/a")


def probe_dpi_with_callback(on_target) -> list[TargetProbeResult]:
    items = load_dpi_targets()
    if not items:
        return []
    collected: list[TargetProbeResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {pool.submit(_probe_dpi_target, item): item for item in items}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            on_target(result)
            collected.append(result)
    collected.sort(
        key=lambda row: next(
            (index for index, item in enumerate(items) if row.name.startswith(item.target_id)),
            999,
        )
    )
    return collected


def format_dpi_lines(results: list[TargetProbeResult]) -> list[str]:
    return format_probe_lines(results)
