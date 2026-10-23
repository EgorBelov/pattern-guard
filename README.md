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
├── .gitignore
├── README.md
└── requirements.txt
```

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Запуск API (после реализации точки входа):

```bash
uvicorn app.api.main:app --reload
```

Запуск дашборда модератора (после реализации точки входа):

```bash
streamlit run app/ui/dashboard.py
```

Проверка тестов:

```bash
pytest
```
