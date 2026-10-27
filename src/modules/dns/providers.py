# dns/dns_providers.py
"""
Список DNS провайдеров для UI
"""

DNS_PROVIDERS = {
    "Обход блокировок": {
        "Zapret DNS": {
            "ipv4": ["83.217.211.149"],
            "ipv6": ["2a03:afc0:9::235d"],
            "desc": "Доступ к заблокированным сервисам",
            "icon": "fa5s.globe",
            "color": "#1f6fd6",
            "doh": "https://dns.zapret.moe/dns-query"
        },
        "Comss DNS": {
            "ipv4": ["83.220.169.155", "212.109.195.93"],
            "ipv6": [],
            "desc": "Доступ к зарубежным сервисам",
            "icon": "fa5s.brain",
            "color": "#673ab7",
            "doh": "https://dns.comss.one/dns-query"
        },
    },
    "Обычные": {
        "Cloudflare": {
            "ipv4": ["1.1.1.1", "1.0.0.1"],
            "ipv6": ["2606:4700:4700::1111", "2606:4700:4700::1001"],
            "desc": "Быстрый, без фильтрации",
            "icon": "fa5s.bolt",
            "color": "#f48120",
            "doh": "https://cloudflare-dns.com/dns-query"
        },
        "Google DNS": {
            "ipv4": ["8.8.8.8", "8.8.4.4"],
            "ipv6": ["2001:4860:4860::8888", "2001:4860:4860::8844"],
            "desc": "Надёжный, без фильтрации",
            "icon": "fa5b.google",
            "color": "#4285f4",
            "doh": "https://dns.google/dns-query"
        },
    },
}
