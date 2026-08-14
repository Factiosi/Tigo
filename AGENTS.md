# AGENTS.md — Tigo

Документ для AI-агентов: быстрый вход в проект, архитектура и осознанные решения.

## Что это

**Tigo** — десктоп GUI (Flet) для управления zapret/winws на Windows. Пользователь выбирает стратегию flowseal, запускает/останавливает winws без видимых консолей, тестирует стратегии, обновляет runtime с GitHub.

> Имя приложения — **Tigo**. Папка репозитория может называться `Z2UI` — историческое именование, не переименовывать без явного запроса.

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
└── ui/             # Flet: pages, components, windows/debug_console
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
GUI → daemon IPC → strategies.launcher.build_winws_launch(strategy) → WinwsLaunchSpec
                → kernel.public.start(spec) → winws_runner → subprocess (CREATE_NO_WINDOW)
```

Kernel **не** парсит стратегии — только принимает готовый `WinwsLaunchSpec`.

**Daemon vs GUI:** winws, tray, IPC и bootstrap (обновления, монитор) живут только в `run.py --daemon`. GUI без daemon не запускается; управление zapret — только через IPC.

## Пути данных

| Что | Где |
|-----|-----|
| winws, utils | `{program_root}/bin`, `{program_root}/utils` |
| flowseal strategies | `%APPDATA%\Tigo\strategies\flowseal\{version}\*.txt` |
| versioned lists | `%APPDATA%\Tigo\strategies\flowseal\{version}\lists\` |
| user lists | `%APPDATA%\Tigo\strategies\flowseal\user_lists\` |
| fake bins | `%APPDATA%\Tigo\strategies\flowseal\bin\` |
| settings | `%APPDATA%\Tigo\settings.json` |
| результаты тестов | `%APPDATA%\Tigo\cache\test_results.json` |

## Ключевые решения

1. **Модульность** — core + kernel + modules + ui. Новый функционал = новый модуль в `modules/`, логирование через `core.debug_log`.
2. **Результаты тестов сохраняются по версии Flowseal** — daemon пишет `%APPDATA%\Tigo\cache\test_results.json`, GUI перечитывает cache через IPC polling. Журнал текущего запуска остаётся in-memory.
3. **Debug console** — отдельный процесс (`run.py --debug-console`), UI entrypoint в `src/ui/windows/debug_console_app.py`, лог через `%APPDATA%\\Tigo\\debug.log`, TTL 1 час.
4. **Home page без inline-консоли** — статус через pill + snackbar; детали в debug console.
5. **winws принадлежит только daemon** — GUI не запускает и не завершает процесс напрямую, включая подбор стратегий.
6. **Automation ограничена** — source daemon разрешает MCP-команды; compiled daemon требует `TIGO_AUTOMATION=1`.
7. **Runtime обязателен и независим от стратегий** — при отсутствии `bin/winws.exe` daemon скачивает официальный релиз Flowseal независимо от `strategy_source` и настроек автообновления.
8. **Самообновление Tigo** — проверка GitHub Releases (`Tigo-Setup-X.Y.Z.exe` + `.sha256`); автопроверка включена, автоустановка выключена.
9. **Массовые тесты** — daemon владеет probe snapshot; GUI раскрывает только текущую стратегию, пауза 2 с, затем все завершённые.

## Осознанные «странности»

- **`kernel/service_api.py`** — legacy Win32 SCM API, используется только в `migrate.py` для удаления старого сервиса `zapret`. Deprecated для обычного запуска.
- **DPI-тест** — backend пока не реализован; radio в UI отключён.
- **winws stdout → DEVNULL** — пользователь не видит консоль winws; stderr читается только при immediate exit.
- **Имя repo Z2UI vs app Tigo** — намеренно не синхронизировано.

## Как добавить модуль

1. Создать `src/modules/<name>/` с `__init__.py`.
2. Логировать действия через `from src.core.debug_log import debug, info, warn, error`.
3. Опционально: pub/sub через `src.core.events`.
4. UI-страницу — в `src/ui/pages/`, регистрация в `ui/app.py`.
5. **Не** импортировать ui из modules (journal — исключение для рендеринга, постепенно вынесется).

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

- Select = `make_select()` в `src/ui/components.py`, **не** `ft.Dropdown` (chevron Material).
- Меню в **`page.overlay`**, reposition при scroll через `menu_popup.update()`.
- **Не** оборачивать `scroll_page` во внутренний `Stack` с overlay — ломает layout.
- Flet **не имеет** `LayerLink` / `CompositedTransformFollower` — идеально плавный scroll+dropdown недостижим без SDK.
- Закрытие: Escape, фон `scroll_page`, `bind_select_dismiss`, `close_active_select()` при смене вкладки.
