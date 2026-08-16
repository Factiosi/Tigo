# Сборка Tigo (Windows, Nuitka standalone)

## Требования

- Windows 10/11 x64
- Python 3.12 + venv
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) — workload **Desktop development with C++**
- Node.js 20+ (для `tools/generate_icons.mjs`, если нет готовых `app.ico` / `tray-*.png`)
- Один раз запустить `python run.py`, чтобы Flet скачал desktop client в `%USERPROFILE%\.flet\client\`

## Установка зависимостей

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements\base.txt -r requirements\build.txt
```

## Ассеты (ico / tray)

```powershell
cd tools
npm install
node generate_icons.mjs
cd ..
```

## Сборка

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_nuitka.ps1
```

Скрипт пересоздаёт `dist\Tigo\` и после успешной сборки удаляет промежуточный `dist\run.build\`.

Результат: **вся папка** `dist\Tigo\` — `Tigo.exe`, `flet_client\`, `icons\`, DLL и прочие зависимости Nuitka. Локальные `bin\` и `utils\` намеренно не копируются.

> **Важно:** распространяйте или копируйте **целиком папку** `dist\Tigo\`, а не один `Tigo.exe`. Без `flet_client\` и соседних DLL приложение не запустится.

`Tigo.exe` собран с UAC-манifest (запуск от администратора). Двойной клик: UAC → фоновый daemon (трей) → GUI.

## Installer (Inno Setup)

После standalone-сборки скомпилируйте [`tools/tigo_installer.iss`](../tools/tigo_installer.iss):

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" tools\tigo_installer.iss
```

Результат: `dist\installer\Tigo-Setup-X.Y.Z.exe`. Версия в `.iss` должна совпадать с `src\core\version.py`.

Installer устанавливает всю папку standalone в `{autopf}\Tigo`. При удалении он очищает установленный runtime и задачу `Tigo Autostart`, но сохраняет настройки и пользовательские данные в `%APPDATA%\Tigo`.

## Выпуск релиза

Проверка без изменений GitHub:

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy_release.ps1 -Version 1.1.0 -DryRun
```

Публикация выполняется только из чистой ветки `master` после commit:

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy_release.ps1 -Version 1.2.2 -ReleaseNotes "Краткое описание релиза." -Publish
```

Скрипт запускает unit-тесты, пересобирает standalone, проверяет отсутствие MCP и стороннего runtime, создаёт installer и SHA-256, отправляет `master`, tag и GitHub Release.

## Проверка

```powershell
dist\Tigo\Tigo.exe --daemon
dist\Tigo\Tigo.exe
dist\Tigo\Tigo.exe --debug-console
.venv\Scripts\python tools\smoke_ipc_ping.py
```

Дополнительно проверьте: второй `--daemon` не создаёт новый экземпляр; start/stop и подбор стратегий выполняются без консольных окон; debug console открывается из GUI.

## winws runtime

`bin\` и `utils\` **не входят** в git, standalone и installer. При первом запуске daemon независимо от настроек стратегий получает обязательный runtime из официального релиза Flowseal. Перед распространением проверьте, что installer не содержит сторонний runtime.

## Архитектура

- **Daemon** (`Tigo.exe --daemon`) — tray, IPC, winws, обновления
- **GUI** (`Tigo.exe`) — только Flet UI, управление через IPC; без daemon не стартует
