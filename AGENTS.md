# AGENTS.md — Tigo

Документ для AI-агентов: быстрый вход в проект, архитектура и осознанные решения.

Закон имён папок — в соседнем репозитории Factiosi, `docs/STRUCTURE.md`. Здесь второй схемы нет.

## Что это

**Tigo** — десктоп GUI (Flet) для управления zapret/winws на Windows. Пользователь выбирает стратегию flowseal, запускает/останавливает winws без видимых консолей, тестирует стратегии, обновляет runtime с GitHub.

> Имя приложения — **Tigo**. 

## Корень

| Имя | Что это |
|-----|---------|
| `run.py` | Вход: окно, `--daemon`, `--debug-console` |
| `requirements.txt` | Зависимости запуска |
| `requirements-build.txt` | Nuitka |
| `src/` | Весь код |
| `assets/icons/` | Иконки окна, трея и окна обновления (собираются из `assets/brand/sources/`) |
| `assets/brand/sources/` | Белый мастер знака `tigo-simple.svg` |
| `tools/` | Генератор иконок и инсталлятор |
| `scripts/` | Сборка, сплэш обновления, релиз, smoke |
| `docs/` | Сборка и локальные заметки |
| `tests/` | Тесты |

## Точки входа

```
run.py --daemon
  → ensure_layout(), bootstrap_user_lists()
  → kernel.public.initialize_runtime()
  → kernel.process_monitor.start_monitor()
  → run_startup_updates()
  → tray + IPC (winws живёт здесь)

run.py (GUI)
  → ensure_admin() (UAC)
  → require_daemon_for_gui()  # без daemon GUI не стартует
  → ft.run(ui/app.py:main)    # только IPC к daemon
```

**Сборка release:** [`docs/BUILD.md`](docs/BUILD.md) (Nuitka standalone, Windows).
**Локальная автоматизация:** [`docs/AUTOMATION.md`](docs/AUTOMATION.md) (MCP stdio, dev/test only).

## Архитектура

```
src/
├── core/           # инфраструктура: paths, settings, admin, debug_log, events
├── kernel/         # ядро: запуск/остановка winws, мониторинг, runtime state
├── modules/        # функциональные модули
│   ├── strategies/       # парсинг .bat, репозиторий, launcher
│   ├── strategy_testing/ # daemon-раннер тестов, probe, cache результатов
│   ├── updates/          # GitHub releases, transformer
│   └── filters/          # game filter, ipset, tcp timestamps
├── update_splash/  # отдельный процесс окна обновления
└── ui/
    ├── components/ # контролы без знания экрана
    ├── pages/      # экраны основного окна
    ├── features/   # debug console
    └── theme/      # тема на токенах Factiosi Umbrae; umbrae.py — копия, руками не править
```

### Слои и границы

| Слой | Ответственность | Не знает о |
|------|-----------------|------------|
| **kernel** | `WinwsLaunchSpec` → start/stop winws, PID monitor | стратегиях, UI, тестах |
| **modules/strategies** | `.bat` → args, репозиторий, `build_winws_launch()` | UI |
| **modules/strategy_testing** | daemon: start→probe→stop; cache результатов по версии | UI |
| **core/debug_log** | always-on журнал, TTL 1 час | UI (только pub/sub) |
| **ui** | страницы, snackbar, debug console window | бизнес-логике |

### Поток запуска winws

```
GUI → daemon IPC → strategies.launcher.build_winws_launch(strategy)
                → .txt (аргументы winws1) → плейсхолдеры → strategies.winws2.to_winws2_argv → WinwsLaunchSpec
                → kernel.public.start(spec) → winws_runner → bin/winws2.exe (CREATE_NO_WINDOW)
```

Kernel **не** парсит стратегии — только принимает готовый `WinwsLaunchSpec`.

### winws2 и конвертер стратегий

Движок — `winws2.exe` из официального релиза zapret2 (`bol-van/zapret2`). Flowseal по-прежнему выпускает стратегии под winws1, поэтому в `%APPDATA%` хранятся аргументы winws1, а перевод в winws2 делается **при каждом запуске** в `modules/strategies/winws2.py` (обновление конвертера не требует перекачивать Flowseal).

- Перевод сохраняет семантику nfqws1, а не стиль PR Flowseal#18202: каждый фейк — отдельный `fake`-инстанс в группе своего `--payload` (tls/http/quic/discord/stun…), неявные умолчания nfqws1 прописаны явно (`fake_default_tls` с `rnd,rndsni,dupsid`, нулевые фейки 64/256 байт), `--dpi-desync-any-protocol` → группа «всё, что nfqws1 считал unknown» (`--payload=all` + Lua-фильтр `~…,empty`), `--dpi-desync-cutoff=nN` → `--out-range=<nN`, `multidisorder` → `multidisorder_legacy`.
- Fooling (`tcp_ts`, `tcp_seq`/`tcp_ack`/`tcp_ts_up` для badseq, `tcp_md5`) и `repeats` идут только в инстансы, шлющие фейки: в winws2 fooling у `multisplit`/`multidisorder` портил бы настоящие сегменты.
- Фейки подключаются через `--blob=fs_<имя файла>:@<путь>`, `blobs.lua` не нужен.
- Опции без точного аналога в winws2 → `ConversionError`, стратегия не запускается. Единственное, что теряется молча с предупреждением в лог, — `altorder` у `hostfakesplit`/`fakedsplit` (в winws2 его нет).
- «Своя стратегия»: аргументы winws1 конвертируются, аргументы winws2 (`--lua-desync`, `--payload`…) передаются как есть, библиотека Lua подключается автоматически.

**Daemon vs GUI:** winws, tray, IPC и bootstrap (обновления, монитор) живут только в `run.py --daemon`. GUI без daemon не запускается; управление zapret — только через IPC.

## Пути данных

| Что | Где |
|-----|-----|
| winws2, WinDivert, cygwin | `{program_root}/bin` (версия zapret2 — `{program_root}/engine-version.txt`) |
| Lua-библиотека zapret2 | `{program_root}/lua` (`zapret-lib.lua`, `zapret-antidpi.lua`) |
| utils Flowseal | `{program_root}/utils` |
| иконки | `{program_root}/assets/icons` |
| flowseal strategies | `%APPDATA%\Tigo\strategies\flowseal\{version}\*.txt` |
| versioned lists | `%APPDATA%\Tigo\strategies\flowseal\{version}\lists\` |
| user lists | `%APPDATA%\Tigo\strategies\flowseal\user_lists\` |
| fake bins | `%APPDATA%\Tigo\strategies\flowseal\bin\` |
| settings | `%APPDATA%\Tigo\settings.json` |
| результаты тестов | `%APPDATA%\Tigo\cache\test_results.json` |

## Ключевые решения

1. **Модульность** — core + kernel + modules + ui. Новый функционал = новый модуль в `modules/`, логирование через `core.debug_log`.
2. **Результаты тестов сохраняются по версии Flowseal** — daemon пишет `%APPDATA%\Tigo\cache\test_results.json`, GUI перечитывает cache через IPC polling. Журнал текущего запуска остаётся in-memory.
3. **Debug console** — отдельный процесс (`run.py --debug-console`), вход в `src/ui/features/debug_console/app.py`, лог через `%APPDATA%\Tigo\debug.log`, TTL 1 час.
4. **Home page без inline-консоли** — статус через бейдж + тост; детали в debug console.
5. **winws принадлежит только daemon** — GUI не запускает и не завершает процесс напрямую, включая подбор стратегий.
6. **Automation ограничена** — source daemon разрешает MCP-команды; compiled daemon требует `TIGO_AUTOMATION=1`.
7. **Движок обязателен и независим от стратегий** — при отсутствии файлов winws2 daemon скачивает официальный релиз zapret2 (проверка по `sha256sum.txt`) независимо от `strategy_source` и настроек автообновления; при `auto_promote_updates` и остановленном winws2 обновляет его на старте. Из архива Flowseal берутся только стратегии, листы, фейки `.bin` и `utils` — его `winws.exe` и `WinDivert.dll` не ставятся (у zapret2 свой пропатченный DLL). Оставшийся от старых версий `bin/winws.exe` считается своим: его гасит stop и удаляет установка движка.
8. **Самообновление Tigo** — проверка GitHub Releases (`Tigo-Setup-X.Y.Z.exe` + `.sha256`); автопроверка включена, автоустановка выключена.
9. **Массовые тесты** — daemon владеет probe snapshot; GUI раскрывает только текущую стратегию, пауза 2 с, затем все завершённые.

## Осознанные «странности»

- **`kernel/service_api.py`** — legacy Win32 SCM API, используется только в `migrate.py` для удаления старого сервиса `zapret`. Deprecated для обычного запуска.
- **DPI-тест** — backend пока не реализован; radio в UI отключён.
- **winws2 stdout → DEVNULL** — пользователь не видит консоль winws2; stderr читается только при immediate exit.
- **Имя repo Z2UI vs app Tigo** — намеренно не синхронизировано.
- **Исключения программ по `.exe` нет — и это осознанно.** Пробовали: монитор WinDivert SOCKET (PID → локальный порт) + Lua-фильтр первым в профиле winws2. На сетевом уровне WinDivert PID недоступен, события SOCKET/FLOW приходят асинхронно, а `connect()` драйвер не придерживает (без sniff сразу `FWP_ACTION_BLOCK`). Итог — гонка: первые пакеты (QUIC Initial, часть ClientHello) успевают в обработку. Без гонки и без задержки это делает только свой подписанный WFP-драйвер. Не возвращаться без нового механизма.

## Как добавить модуль

1. Создать `src/modules/<name>/` с `__init__.py`.
2. Логировать действия через `from src.core.debug_log import debug, info, warn, error`.
3. Опционально: pub/sub через `src.core.events`.
4. UI-страницу — в `src/ui/pages/`, регистрация в `ui/app.py`.
5. **Не** импортировать ui из modules. Журнал тестов — исключение: цвета строк берутся из `src.ui.theme`.

## Запуск

```bash
python run.py
```

## Что не трогать без запроса

- DNS — `modules/dns/`, UI-страница `ui/pages/dns.py`.
- Режим «Своя стратегия» — `settings.strategy_source == "custom"`, скрывает подбор стратегий и редактирование листов.
- Переименование Tigo / папки репозитория.

## UI: кастомный select и overlay

**Подробно:** [`docs/AGENTS-UI-SELECT.md`](docs/AGENTS-UI-SELECT.md) — решения, ограничения Flet, мёртвые концы (Stack в `scroll_page`, barrier, hide-on-scroll), чеклист для агентов.

Кратко:

- Select = `make_select()` в `src/ui/components/`, **не** `ft.Dropdown` (chevron Material).
- Меню в **`page.overlay`**, reposition при scroll через `menu_popup.update()`.
- **Не** оборачивать `scroll_page` во внутренний `Stack` с overlay — ломает layout.
- Flet **не имеет** `LayerLink` / `CompositedTransformFollower` — идеально плавный scroll+dropdown недостижим без SDK.
- Закрытие: Escape, фон `scroll_page`, `bind_select_dismiss`, `close_active_select()` при смене вкладки.

## Дизайн: Factiosi Umbrae

Язык — `docs/UMBRAE.md` в соседнем репозитории Factiosi. Здесь его не пересказывают.

- Числа темы (цвета Nox/Lux, радиусы, размеры, периоды блика) — только из `src/ui/theme/umbrae.py`. Это копия `python/umbrae.py` из Factiosi: обновляется `scripts/sync_umbrae.ps1`, руками не правится. `src/ui/theme/__init__.py` раскладывает её в `T.*`.
- Акцент один — фиолетовый. Пилюль нет: кнопки, поля, карточки, пункт рельса — радиус 6, панели и меню — 8, бейджи — 4.
- Рельс: вверху знак в хроме и «TIGO», пункты одного кегля; активный — плашка с обводкой по контуру, по ней раз в период проходит блик (один таймер на окно, смена пункта его не перезапускает).
- Иконки рельса — Lucide (`assets/icons/lucide/*.svg`, ISC, лицензия рядом), через `lucide_icon()` из `ui/components`; цвет задаётся тонировкой. Новая иконка — тот же SVG из `lucide-static`, не Material.
- Знаки: `tools/build_brand.py` собирает из `assets/brand/sources/tigo-simple.svg` и токенов SVG окна, трея и окна обновления; в сайдбаре знака нет — это для веба; растры и `app.ico` — `tools/generate_icons.mjs`. Трей «работа» светится цветом успеха, «покой» — фиолетовым неоном.

