# Zapret DNS

Zapret DNS — DNS-сервер проекта Zapret в Нидерландах. Он открывает сервисы, которые не пускают пользователей из России по адресу: на домены из своего списка отвечает адресом, через который сервис доступен, остальные сайты отдаёт как есть. Рекламу не режет, ничего не подменяет, какие сайты вы открываете, не записывает.

Состояние сервера и живая статистика: [dns.zapret.moe](https://dns.zapret.moe/).

Если сайт в России режут по имени (DPI), смена DNS не поможет — для этого и служит сам обход Tigo.

## Как включить в Tigo

- **«Изменение DNS»** → «Zapret DNS» → «Применить»: сервер ставится для всего компьютера.
- **«Редактирование hosts»** → «Сервисы» → DNS «Zapret DNS», отметить нужные сервисы → «Применить»: адреса пишутся в hosts только для этих сервисов. Так Zapret DNS работает, даже если провайдер перехватывает сторонние DNS-запросы.

## Адреса

| Способ | Адрес |
|--------|-------|
| DNS, IPv4 | `83.217.211.149` |
| DNS, IPv6 | `2a03:afc0:9::235d` |
| DoH | `https://dns.zapret.moe/dns-query` |
| DoT, «Частный DNS» | `dns.zapret.moe` |

## Сервисы

Список снят с сервера 2026-10-27, всего сервисов: 92. Сервер дополняет его сам, актуальный список — на [dns.zapret.moe](https://dns.zapret.moe/).

### Нейросети (20)

| Сервис | Основной домен |
|--------|----------------|
| ChatGPT & Sora (OpenAI) | `chatgpt.com` |
| Gemini AI | `gemini.google.com` |
| Claude | `claude.ai` |
| OpenRouter | `openrouter.ai` |
| Microsoft (Copilot, Designer, Xbox) | `copilot.microsoft.com` |
| Grok | `grok.com` |
| Manus | `manus.im` |
| Meta AI | `meta.ai` |
| Trae.ai | `trae.ai` |
| Windsurf | `windsurf.com` |
| GitHub Copilot | `github.com` |
| Adobe AI | `adobe.com` |
| Cerebras | `cerebras.ai` |
| Cursor | `cursor.com` |
| Groq | `groq.com` |
| Camel AI | `camelai.com` |
| Dola (Cici) | `cici.com` |
| Hume AI | `hume.ai` |
| Monica | `monica.im` |
| OpenCode | `opencode.ai` |

### Остальные (72)

| Сервис | Основной домен |
|--------|----------------|
| Spotify | `spotify.com` |
| Twitch | `twitch.tv` |
| Notion | `notion.com` |
| DeepL | `deepl.com` |
| ElevenLabs | `elevenlabs.io` |
| JetBrains | `jetbrains.com` |
| MangaLib | `mangalib.me` |
| Parsec | `parsec.app` |
| Square | `squareup.com` |
| AMD | `amd.com` |
| Autodesk | `autodesk.com` |
| Badoo | `badoo.com` |
| Broadcom | `broadcom.com` |
| Chess | `chess.com` |
| Deezer | `deezer.com` |
| Dyson | `dyson.se` |
| Elgato | `elgato.com` |
| Fitbit | `fitbit.com` |
| Framer | `framer.com` |
| Guidedhacking | `guidedhacking.com` |
| Guilded | `guilded.gg` |
| Imgur | `imgur.com` |
| Linear.app | `linear.app` |
| Make | `make.com` |
| Naukri | `naukri.com` |
| Nvidia | `nvidia.com` |
| Oracle | `oracle.com` |
| Posthog | `posthog.com` |
| Pump.fun | `pump.fun` |
| Qwant | `qwant.com` |
| Reve | `reve.art` |
| SketchUp | `trimble.com` |
| Strava | `strava.com` |
| Tableau | `tableau.com` |
| Tailscale | `tailscale.com` |
| TeamViewer | `teamviewer.com` |
| Tria.ge | `tria.ge` |
| Truth Social | `truthsocial.com` |
| Weather Underground | `wunderground.com` |
| Weather.com | `weather.com` |
| Web Archive | `archive.org` |
| WorkOS | `workos.com` |
| Xerox | `xerox.com` |
| 37signals (Basecamp) | `basecamp.com` |
| Aave | `aave.com` |
| Affinity Studio | `affinity.studio` |
| Analog Devices | `analog.com` |
| Arduino | `arduino.cc` |
| Arkose Labs | `arkoselabs.com` |
| Arrow Electronics | `arrow.com` |
| Avast | `avast.ru` |
| Best Buy | `bestbuy.com` |
| Bike24 | `bike24.com` |
| Brave | `brave.com` |
| Chaos (V-Ray, Enscape) | `chaos.com` |
| MongoDB | `mongodb.com` |
| ZeroSSL | `zerossl.com` |
| CapCut | `capcut.com` |
| ClickUp | `clickup.com` |
| CoreWeave | `coreweave.com` |
| Corsair | `corsair.com` |
| Crunchyroll | `crunchyroll.com` |
| Cummins | `cummins.com` |
| Formula 1 | `formula1.com` |
| Game8 | `game8.co` |
| IKEA | `ikea.com` |
| Modivo | `modivo.pl` |
| LEGO | `lego.com` |
| Makita | `makita.com` |
| Microchip | `microchip.com` |
| Scribd | `scribd.com` |
| Wix | `wix.com` |
