# Автоматизация Tigo через MCP

Tigo предоставляет локальный MCP-сервер по stdio для разработки и автоматизированных smoke-тестов. Он не входит в Nuitka artifact и не открывает дополнительный сетевой порт: инструменты обращаются к существующему daemon IPC на `127.0.0.1:51731`.

## Установка

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements\dev.txt
```

## Cursor

Добавьте локальный stdio-сервер в проектный `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tigo": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/Scripts/pythonw.exe",
      "args": ["${workspaceFolder}/tools/tigo_mcp.py"],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

Dev daemon, запущенный из исходников, разрешает automation автоматически.

Для тестирования compiled-сборки флаг должен присутствовать **в окружении daemon до его запуска**:

```powershell
$env:TIGO_AUTOMATION = "1"
.\dist\Tigo\Tigo.exe --daemon
```

Обычный compiled daemon без этого флага отклоняет чтение лога, изменение настроек и обновление стратегий.

## Инструменты

- `tigo_ping`, `tigo_status`
- `tigo_start`, `tigo_stop`
- `tigo_list_strategies`
- `tigo_start_tests`, `tigo_test_status`, `tigo_stop_tests`
- `tigo_get_settings`, `tigo_update_settings`
- `tigo_read_debug_log`
- `tigo_update_strategies`

`storage_root` намеренно нельзя менять через MCP: перенос хранилища требует интерактивной миграции. Все остальные значения проходят проверку типов и допустимых вариантов в daemon.

## Безопасность

MCP предназначен только для доверенного локального агента. Инструменты могут запускать и останавливать winws, менять настройки и скачивать Flowseal. Не запускайте MCP-сервер из недоверенного клиента и не включайте `TIGO_AUTOMATION` постоянно в пользовательском окружении.
