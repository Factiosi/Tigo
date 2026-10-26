# Tigo

Tigo — приложение для Windows: запуск и проверка стратегий [Flowseal](https://github.com/Flowseal/zapret-discord-youtube) (zapret / winws). Фоновый процесс держит winws, значок в трее и служебные задачи; окно только управляет ими.

## Требования

- Windows 10 или 11, x64
- Права администратора (запрос UAC при старте)

## Установка

1. На странице [релизов](https://github.com/Factiosi/Tigo/releases/latest) скачайте `Tigo-Setup-<версия>.exe`.
2. Установите программу и откройте Tigo из меню «Пуск».
3. Подтвердите запрос UAC.

При первом запуске Tigo скачает движок winws2 из релиза [zapret2](https://github.com/bol-van/zapret2) и стратегии Flowseal; стратегии Flowseal для winws1 Tigo переводит в формат winws2 сам. На главном экране выберите стратегию и нажмите **Запуск**. Для подбора откройте **Подбор стратегий**, отметьте варианты и запустите тест — результаты сохраняются по версии Flowseal.

## Обновления

Проверка обновлений Tigo включена по умолчанию; установка — вручную в **Настройках**. Стратегии и файлы Flowseal обновляются отдельно.

## Данные

Настройки, стратегии, списки, кэш и результаты тестов: `%APPDATA%\Tigo`.

## Разработка

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py --daemon   # отдельный терминал с правами администратора
.venv\Scripts\python run.py            # окно
```

Сборка и релиз: [`docs/BUILD.md`](docs/BUILD.md).

## Ограничения

Установщик не подписан кодом; при первом запуске Windows может показать предупреждение SmartScreen.
