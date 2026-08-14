# Tigo

Десктопное приложение (Flet) для управления zapret/winws на Windows: выбор стратегии Flowseal, запуск/остановка, подбор стратегий, обновления.

## Архитектура

- **Daemon** (`python run.py --daemon`) — tray, IPC, winws, обновления стратегий. Может работать без окна.
- **GUI** (`python run.py`) — только интерфейс; **без daemon не запускается**.

Стратегии Flowseal **не входят** в репозиторий — скачиваются с GitHub при первом запуске (см. настройки).

## Разработка

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py --daemon   # в отдельном терминале (или автозапуск)
.venv\Scripts\python run.py            # GUI
```

Требуется UAC (администратор). Данные: `%APPDATA%\Tigo\`.

## Сборка (Nuitka)

См. [`docs/BUILD.md`](docs/BUILD.md).

```powershell
.venv\Scripts\python -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File tools\build_nuitka.ps1
```

Результат: `dist\Tigo\Tigo.exe`.

## winws runtime

`bin\winws.exe` и `utils\` не в git. Для dev-окружения — установите runtime рядом с репозиторием или получите через обновление Flowseal в приложении.

## Версия

1.0.0
