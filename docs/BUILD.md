# Сборка Tigo (Windows, Nuitka standalone)

## Требования

- Windows 10/11 x64
- Python 3.12 + venv
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) — workload **Desktop development with C++**
- Node.js 20+ (для `tools/generate_logos.mjs`, если нет готовых `tigo.ico` / `tigo-tray.png`)
- Один раз запустить `python run.py`, чтобы Flet скачал desktop client в `%USERPROFILE%\.flet\client\`

## Установка зависимостей

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-build.txt
```

## Ассеты (ico / tray)

```powershell
cd tools
npm install
node generate_logos.mjs
cd ..
```

## Сборка

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_nuitka.ps1
```

Результат: `dist\Tigo\Tigo.exe` + `dist\Tigo\flet\flet.exe` + `dist\Tigo\logos\`.

## Проверка

```powershell
dist\Tigo\Tigo.exe --daemon
dist\Tigo\Tigo.exe
dist\Tigo\Tigo.exe --debug-console
```

## winws runtime

`bin\` и `utils\` **не входят** в git и не встраиваются в exe. Для локального теста скопируйте их рядом с `Tigo.exe` или получите через обновление стратегий Flowseal в настройках (файлы в `%APPDATA%\Tigo\`).

## Архитектура

- **Daemon** (`Tigo.exe --daemon`) — tray, IPC, winws, обновления
- **GUI** (`Tigo.exe`) — только Flet UI, управление через IPC; без daemon не стартует
