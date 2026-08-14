# AGENTS: кастомный select, overlay и скролл (Z1UI)

Документ для AI-агентов: решения, ограничения Flet и **что не делать повторно**.  
Связан с `src/ui/components.py` (`make_select`, `scroll_page`) и страницами в `src/ui/pages/`.

---

## Зачем кастомный select

`ft.Dropdown` **не используется** намеренно:

- Material подменяет `trailing_icon` при открытии (chevron → другая иконка).
- Нужен Factiosi-стиль: `EXPAND_MORE` + `animate_rotation` 180 ms, scale/opacity меню ~160 ms, hover на всю ширину пункта.

Реализация: **`make_select()`** в `src/ui/components.py`.

---

## Архитектура `make_select`

```
Column
├── label (ui_text)
└── GestureDetector → field (Container + value + chevron EXPAND_MORE)

menu_popup (Container) — НЕ в Column, живёт в page.overlay при открытии
├── menu_col (Column, height фиксирован)
└── items (Container height=40, ink/hover)
```

### Глобальное состояние (один открытый select на страницу)

| Символ | Назначение |
|--------|------------|
| `_active_select_close` | callback закрытия текущего меню |
| `_select_scroll_reposition` | callback пересчёта top/left при scroll |
| `_page_keyboard_saved` | цепочка `on_keyboard_event` для Escape |

Публичный API: **`close_active_select(refresh=True)`** — вызывать при смене вкладки (`app.py` → `_navigate`).

### Открытие / закрытие

1. `open_menu`: `_close_active_select(refresh=False)` → позиция из `TapEvent.global_position` → `page.overlay.append(menu_popup)` → `_attach_page_keyboard`.
2. `close_menu`: снять overlay, сброс chevron/border, `_detach_page_keyboard`.
3. **Escape** — глобальный `_global_keyboard_handler` (не per-select `on_keyboard`, иначе был `RecursionError`).

### Анимации

- Открытие: `animate_opacity` / `animate_scale` (ANIM_FAST), затем **`_freeze_menu_animations()`** — отключить animate, `opacity=1`, чтобы scroll не давал полупрозрачные кадры.
- Chevron: `CHEVRON_ANIM` 180 ms, rotate π при open.
- Flip вверх: scale origin `BOTTOM_CENTER`; вниз: `TOP_CENTER`.

---

## Позиционирование и flip

Координаты — **оконные** (`global_position` минус `local_position` на tap).

| Константа | Значение | Смысл |
|-----------|----------|--------|
| `MENU_GAP` | 8 | зазор поле ↔ меню |
| `MENU_ITEM_HEIGHT` | 40 | высота строки |
| `MENU_POPUP_VPAD` | 8 | vertical padding popup |
| `_content_bottom(page)` | `window.height - 8` | низ body (без нижнего padding) |

**Flip вверх** (`_should_open_upward`): если снизу не хватает места под `menu_height`, а сверху больше — открыть вверх.  
**Не использовать** `bottom` для overlay — только `top` + `left` (старый `bottom`-anchor давал «оторванное» меню).

**Ширина меню** — **всегда задавать** (`_resolve_field_width()`, fallback 280).  
Без `width` popup в overlay растягивался на всю ширину и **перехватывал все клики** (кнопки «не работали»).

---

## Скролл и overlay

### Текущее решение (зафиксировано)

- `scroll_page(..., page=...)` регистрирует `ListView.on_scroll` → обновляет `page._z1ui_page_scroll_offset`.
- При scroll вызывается `reposition_menu`:  
  `field_top = anchor_field_top - (scroll - anchor_scroll)` → `menu_popup.update()`.
- Меню **остаётся открытым** при прокрутке.
- `scroll_page` — **простой ListView**, без внутреннего `Stack` (см. «Мёртвые концы»).

### Ограничение Flet (критично)

В **Flutter** anchored overlay делают через `CompositedTransformTarget` + `CompositedTransformFollower` + `LayerLink` (или `OverlayPortal.overlayChildLayoutBuilder`). Меню двигается на **compositor layer**, без ручного `on_scroll`.

В **Flet Python API** (проверено в `.venv`):

- нет `LayerLink`, `CompositedTransformTarget/Follower`, `OverlayPortal`.

Поэтому `page.overlay` + ручной reposition **всегда** уязвим к рассинхрону на 1–2 кадра при быстром колёсике (кнопка может «просветить»).  
`on_scroll` throttled (`scroll_interval` ≈ 10 ms у `ScrollableControl`).

Открытый issue: [flet-dev/flet#5485](https://github.com/flet-dev/flet/issues/5485) — anchored overlay в SDK.

---

## Закрытие по клику снаружи

| Механизм | Где |
|----------|-----|
| Клик по фону страницы | `scroll_page` → `Container.on_click` → `_close_active_select` |
| Кнопки / pill | `pill_button` → `_wrap_click` |
| Чекбоксы settings | `bind_select_dismiss(on_change=...)` |
| Кнопки обновлений home | `_update_action_button` → `bind_select_dismiss` |
| Строки стратегий | `bind_select_dismiss(toggle_select/expand)` |
| Другой select | `open_menu` → `_close_active_select(refresh=False)` |
| Смена вкладки | `Z1UIApp._navigate` → `close_active_select(refresh=False)` |
| Escape | глобальный keyboard handler |

**Важно:** `close_menu(refresh=False)` + **один** `page.update()` в конце handler — иначе Flet «съедает» клик по кнопке.

**Не использовать** полноэкранный barrier в overlay — блокировал scroll (осознанно убран).

---

## `scroll_page`

```python
scroll_page(*sections, page=self.page)  # page обязателен для scroll-sync select
```

- Простой `ListView` → один `Container` → `Column` секций.
- `on_click` на контейнере — dismiss select (клик по «пустому» фону колонки).
- **`page` нужен** на home, settings, strategies, dns, lists — иначе нет `_z1ui_page_scroll_offset` и reposition.

---

## Мёртвые концы (НЕ повторять без явного запроса)

### 1. Overlay внутри `scroll_page` (`Stack` + overlay layer)

Пробовалось **дважды**: меню в `Stack` внутри `ListView`, координаты относительно контента.

**Симптом:** при открытии select **весь интерфейс схлопывается** в узкую колонку, элементы наезжают друг на друга.

**Причина:** добавление positioned popup в overlay-layer ломает layout Stack/ListView в Flet.

**Вывод:** не оборачивать `scroll_page` во внутренний `Stack` с overlay.

### 2. Закрытие select при каждом scroll

Стабильно, как Material Dropdown, но пользователь **хотел** оставить меню открытым при прокрутке. Сейчас **не закрываем** на scroll.

### 3. Hide/show меню на scroll + debounce reveal

Убирало просвет, но меню **дёргалось** (мигание). Отклонено.

### 4. `page.update()` на каждый scroll при reposition

Усиливало flicker. Сейчас: **`menu_popup.update()`** только.

### 5. Per-select inline `Stack` (меню рядом с полем, без page.overlay)

Теоретически плавный scroll, но:

- z-order: блоки **ниже** по Column перекрывают меню при открытии вниз;
- не заменяет page.overlay для перекрытия соседних секций.

### 6. Полный рефакторинг UI

**Не оправдан** ради dropdown: Flet не даст Flutter-smooth без SDK. Достаточно правок в `make_select` / политике scroll.

---

## Другие UI-изменения в этой ветке обсуждения

### `strategies.py` — expandable rows

- Chevron `EXPAND_MORE` + `CHEVRON_ANIM` / `EXPAND_ANIM`.
- In-place toggle высоты/opacity (не полный `_refresh_list` на каждый toggle).
- Lazy `build_probe_table`; массовый запуск тестов без `_refresh_list` на каждый статус.

### `home.py` — кнопки обновлений

- `_update_action_button` + spinner (`factiosi_spinner`) на время `_updates_busy`.

### `settings.py` — поле «Место хранения»

- `make_text_field`: label сверху, высота 40, `border_radius=12`.
- Убрана строка «По умолчанию»; показывается `current_storage_display()`.

---

## Константы анимации (`components.py`)

| Имя | ms | Где |
|-----|-----|-----|
| `CHEVRON_ANIM` | 180 | select, strategies chevron |
| `ANIM_FAST` | 160 | open/close menu |
| `EXPAND_ANIM` | 220 | раскрытие плашек стратегий |
| `ANIM` | 280 | block_section opacity |

---

## Чеклист для агента при изменении select

- [ ] Не возвращать `ft.Dropdown` без запроса (chevron).
- [ ] Не добавлять `Stack` overlay в `scroll_page`.
- [ ] Всегда задавать `menu_popup.width` при open.
- [ ] Новые кликабельные элементы на scroll-страницах — через `_wrap_click` / `bind_select_dismiss` или dismiss через фон.
- [ ] При новой странице с select — `scroll_page(..., page=self.page)`.
- [ ] При навигации — `close_active_select` (уже в `_navigate`).
- [ ] Не цеплять per-control `on_keyboard` на select.
- [ ] После open вызывать `_freeze_menu_animations()`.
- [ ] `close_menu(refresh=False)` перед handler + один `page.update()` в конце.

---

## Если пользователь снова жалуется на scroll + dropdown

1. **Layout съехал** → проверить, не вернулся ли `Stack` в `scroll_page`.
2. **Клики не проходят** → проверить `menu_popup.width` и z-order в overlay.
3. **Меню исчезает при scroll** → проверить, не добавили `_close_active_select` в `track_scroll`.
4. **Просвет кнопки** → inherent Flet limit; варианты: закрывать при scroll (компромисс A) или ждать Flet #5485.

**Не предлагать** «переписать весь интерфейс» — избыточно и рискованно.

---

## Эталоны

- Factiosi web `Select.tsx`: chevron rotate ~140 ms, menu scale-in.
- Factiosi Python reference: custom select без `ft.Dropdown`.
- Flutter: [Floating overlay over transformed widget](https://flutter.dev/blog/how-to-float-an-overlay-widget-over-a-possibly-transformed-ui-widget).

---

## Файлы

| Файл | Роль |
|------|------|
| `src/ui/components.py` | `make_select`, `scroll_page`, `pill_button`, `bind_select_dismiss`, `close_active_select` |
| `src/ui/app.py` | `_navigate` → `close_active_select` |
| `src/ui/pages/home.py` | selects, update spinners |
| `src/ui/pages/settings.py` | selects, checkboxes dismiss |
| `src/ui/pages/strategies.py` | expand rows, lazy probe, dismiss на row click |
| `src/theme.py` | `T.OVERLAY`, `T.FIELD_HEIGHT`, палитра |
