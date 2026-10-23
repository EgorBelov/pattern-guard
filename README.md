# PatternGuard — AI Content Moderation Assistant

Ассистент поддержки принятия решений для модераторов UGC-платформ. Выявляет токсичность, травлю, спам и скрытые деструктивные паттерны в пользовательском контенте, помогая модератору быстрее и обоснованнее принимать решения.

Учебный проект по курсу «Системы ИИ».

## Архитектура

Система разделена на четыре зоны ответственности:

| Модуль | Ответственность |
| --- | --- |
| `app/preprocessor` | Очистка текста, эвристики, нормализация |
| `app/detector` | ML/LLM-инференс детекции негативных паттернов |
| `app/core`, `app/api` | FastAPI-бэкенд, агрегация скоров, правила принятия решений |
| `app/ui` | Streamlit-дашборд модератора (Human-in-the-loop) |

## Структура проекта

```
pattern-guard/
├── app/
│   ├── __init__.py
│   ├── schemas.py          # Pydantic-схемы запросов/ответов
│   ├── preprocessor/       # очистка, нормализация, эвристики
│   ├── detector/           # ML/LLM-детекция негативных паттернов
│   ├── core/               # агрегация скоров, правила решений
│   ├── api/                # FastAPI-бэкенд
│   └── ui/                 # Streamlit-дашборд модератора
├── tests/                  # unit- и integration-тесты
├── main.py                 # точка входа FastAPI
├── .gitignore
├── README.md
└── requirements.txt
```

## Участники команды

- **osheeat — Олег Галинов** — модуль детекции паттернов (`app/detector`): эвристики токсичности, спама, пассивной агрессии и агрессивного тона.
- **Dinana03 — Диана Туксаитова** — препроцессинг (`app/preprocessor`): очистка текста, нормализация гомоглифов, извлечение метаданных и тесты.
- **kkotenochek — Лиза Каправлова** — Pydantic-схемы, бизнес-логика политик и FastAPI-маршруты (`app/schemas.py`, `app/core`, `app/api`).
- **EgorBelov — Егор Белов** — каркас проекта, Streamlit-дашборд, интеграция сквозного pipeline, сквозные тесты и документация.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Запуск API:

```bash
uvicorn main:app --reload
```

Запуск дашборда модератора:

```bash
streamlit run app/ui/dashboard.py
```

API и дашборд запускаются в отдельных терминалах. Эндпоинты:
`POST /api/v1/moderate` — сквозная модерация, `GET /api/v1/queue` — очередь
комментариев. Если API недоступен, дашборд использует локальный fallback.

Проверка тестов:

```bash
pytest
```
