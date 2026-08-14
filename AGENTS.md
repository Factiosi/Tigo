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

## Архитектура

```
src/
├── core/           # инфраструктура: paths, settings, admin, debug_log, events
├── kernel/         # ядро: запуск/остановка winws, мониторинг, runtime state
├── modules/        # функциональные модули
│   ├── strategies/       # парсинг .bat, репозиторий, launcher
│   ├── strategy_testing/ # раннер тестов, probe, in-memory journal
│   ├── updates/          # GitHub releases, transformer
│   └── filters/          # game filter, ipset, tcp timestamps
└── ui/             # Flet: pages, components, windows/debug_console
```

### Слои и границы

| Слой | Ответственность | Не знает о |
|------|-----------------|------------|
| **kernel** | `WinwsLaunchSpec` → start/stop winws, PID monitor | стратегиях, UI, тестах |
| **modules/strategies** | `.bat` → args, репозиторий, `build_winws_launch()` | UI |
| **modules/strategy_testing** | start→probe→stop, журнал тестов (RAM) | персистентности результатов |
| **core/debug_log** | always-on журнал, TTL 1 час | UI (только pub/sub) |
| **ui** | страницы, snackbar, debug console window | бизнес-логике |

### Поток запуска winws

```
UI/modules → strategies.launcher.build_winws_launch(strategy) → WinwsLaunchSpec
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
| reference-материалы | `reference/` (не часть приложения, в .gitignore) |

## Ключевые решения

1. **Модульность** — core + kernel + modules + ui. Новый функционал = новый модуль в `modules/`, логирование через `core.debug_log`.
2. **Результаты тестов не сохраняются** — только in-memory журнал на странице «Подбор стратегий» (`modules/strategy_testing/journal.py`). Никакого `test_status.json`.
3. **Debug console** — отдельный процесс (`debug_console_app.py`), лог через `%APPDATA%\\Tigo\\debug.log`, TTL 1 час.
4. **Home page без inline-консоли** — статус через pill + snackbar; детали в debug console.
5. **Unit-тестов в репозитории нет** — проверки стратегий вручную через UI (`modules/strategy_testing/`).

## Осознанные «странности»

- **`kernel/service_api.py`** — legacy Win32 SCM API, используется только в `migrate.py` для удаления старого сервиса `zapret`. Deprecated для обычного запуска.
- **DPI-тест в UI** — radio есть, backend не реализован (`strategy_testing/runner.py` отклоняет `test_type != "standard"`).
- **winws stdout → DEVNULL** — пользователь не видит консоль winws; stderr читается только при immediate exit.
- **`reference/`** — upstream flowseal и zapretgui для справки агентов, не импортируется приложением.
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
- Редизайн UI тестов (запланирован отдельно).
- Переименование Tigo / папки репозитория.

## UI: кастомный select и overlay

**Подробно:** [`docs/AGENTS-UI-SELECT.md`](docs/AGENTS-UI-SELECT.md) — решения, ограничения Flet, мёртвые концы (Stack в `scroll_page`, barrier, hide-on-scroll), чеклист для агентов.

Кратко:

- Select = `make_select()` в `src/ui/components.py`, **не** `ft.Dropdown` (chevron Material).
- Меню в **`page.overlay`**, reposition при scroll через `menu_popup.update()`.
- **Не** оборачивать `scroll_page` во внутренний `Stack` с overlay — ломает layout.
- Flet **не имеет** `LayerLink` / `CompositedTransformFollower` — идеально плавный scroll+dropdown недостижим без SDK.
- Закрытие: Escape, фон `scroll_page`, `bind_select_dismiss`, `close_active_select()` при смене вкладки.
