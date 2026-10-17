"""DNS settings for Windows."""

from src.modules.dns import service
from src.modules.dns.providers import DNS_PROVIDERS

__all__ = ["service", "DNS_PROVIDERS"]
