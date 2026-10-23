"""Streamlit-дашборд модератора PatternGuard."""

from __future__ import annotations

import hashlib
import html
import os
import re
import uuid
from functools import lru_cache
from typing import Any, Iterable

import requests
import streamlit as st

API_BASE_URL = os.getenv("PATTERNGUARD_API_URL", "http://localhost:8000").rstrip("/")
MODERATE_URL = os.getenv(
    "PATTERNGUARD_MODERATE_URL", f"{API_BASE_URL}/api/v1/moderate"
)
QUEUE_URL = f"{API_BASE_URL}/api/v1/queue"
REQUEST_TIMEOUT = 1.5

VERDICT_STYLES = {
    "approved": {"label": "Одобрено", "bg": "#e6f4ea", "fg": "#137333"},
    "review": {"label": "На проверку", "bg": "#fef7e0", "fg": "#9a6700"},
    "rejected": {"label": "Отклонено", "bg": "#fce8e6", "fg": "#a50e0e"},
}

DECISION_LABELS = {
    "approve": "✅ Одобрено",
    "warn": "⚠️ Предупреждение",
    "block": "🚫 Заблокировано",
}

VERDICT_ALIASES = {
    "approved": "approved",
    "approve": "approved",
    "allow": "approved",
    "allowed": "approved",
    "ok": "approved",
    "clean": "approved",
    "safe": "approved",
    "одобрено": "approved",
    "одобрить": "approved",
    "чисто": "approved",
    "review": "review",
    "needs_review": "review",
    "manual_review": "review",
    "flag": "review",
    "flagged": "review",
    "suspicious": "review",
    "на проверку": "review",
    "проверка": "review",
    "подозрительно": "review",
    "rejected": "rejected",
    "reject": "rejected",
    "block": "rejected",
    "blocked": "rejected",
    "deny": "rejected",
    "denied": "rejected",
    "toxic": "rejected",
    "отклонено": "rejected",
    "отклонить": "rejected",
    "токсично": "rejected",
}

PATTERN_RULES = (
    {
        "label": "Токсичность",
        "explanation": "Оскорбления и уничижительные высказывания в адрес собеседника.",
        "weight": 35,
        "terms": (
            "тупой", "тупая", "тупое", "тупые", "тупых", "тупым", "тупую",
            "тупица", "тупицы", "дурак", "дура", "дураки", "дурака",
            "идиот", "идиотка", "идиоты", "идиота", "дебил", "дебилы",
            "кретин", "кретины", "мразь", "мрази", "ничтожество", "ничтожества",
            "убогий", "убогая", "убогие", "отброс", "отбросы", "лох", "лохи", "чмо",
            "stupid", "idiot", "moron", "loser", "dumb",
        ),
    },
    {
        "label": "Травля и унижение",
        "explanation": "Прямое унижение, буллинг и призывы к социальной изоляции.",
        "weight": 35,
        "terms": (
            "неудачник", "неудачница", "неудачники", "неудачницы",
            "лошара", "лошары", "жирный", "жирная", "жирные", "урод", "уродка", "уроды",
            "заткнись", "заткнитесь", "сдохни", "сдохните",
            "никому не нужен", "никому не нужна", "тебе здесь не место",
            "вам здесь не место", "ненавижу тебя", "ненавижу вас", "травля", "буллинг",
            "bully", "bullying", "kill yourself", "hate you",
        ),
    },
    {
        "label": "Спам и фишинг",
        "explanation": "Навязчивые призывы, обещания выгоды и подозрительные ссылки.",
        "weight": 30,
        "single_hit_score": 20,
        "terms": (
            "переходи по ссылке", "перейдите по ссылке",
            "подписывайся", "подписывайтесь", "розыгрыш", "выиграл", "выиграла",
            "выигрыш", "заработок", "криптовалюта", "инвестируй", "промокод",
            "только сегодня", "не упусти", "http://", "https://",
            "www.", "t.me/", "казино", "лотерея",
            "spam", "free money", "winner",
        ),
    },
    {
        "label": "Угрозы и манипуляции",
        "explanation": "Шантаж, запугивание и попытки принудить человека к действию.",
        "weight": 50,
        "single_hit_score": 55,
        "terms": (
            "угрожаю", "угрожает тебе", "угрожает вам", "я знаю где ты", "я знаю, где ты",
            "пожалеешь", "тебе конец", "тебе не поздоровится", "шантаж",
            "выкуп", "я найду тебя", "я тебя найду", "уничтожу", "сломаю",
            "скомпрометирую", "если не сделаешь", "иначе будет хуже",
            "threat", "blackmail", "i will find you", "you will regret",
        ),
    },
    {
        "label": "Деструктивные призывы",
        "explanation": "Скрытые или явные призывы к насилию, вражде и радикальным действиям.",
        "weight": 60,
        "terms": (
            "призыв к насилию", "разжигание ненависти", "разжигание вражды",
            "экстремизм", "радикализация", "теракт", "взорвать", "свергнуть власть",
        ),
    },
)

MOCK_QUEUE = (
    {
        "id": "q-1042",
        "author": "@night_owl",
        "text": "Ты такой тупой, тебе вообще нельзя ничего доверять. Уйди отсюда.",
        "toxicity_score": 86,
        "reason": "Личные оскорбления",
        "created_at": "сегодня, 12:04",
    },
    {
        "id": "q-1043",
        "author": "@bonus_hunter",
        "text": (
            "Срочно переходи по ссылке http://promo-win.example и получи 5000 рублей "
            "бесплатно! Только сегодня!"
        ),
        "toxicity_score": 78,
        "reason": "Спам и подозрительная ссылка",
        "created_at": "сегодня, 12:11",
    },
    {
        "id": "q-1044",
        "author": "@shadow_voice",
        "text": "Если не сделаешь, как я сказал, пожалеешь. Я знаю, где ты живёшь.",
        "toxicity_score": 94,
        "reason": "Угроза и шантаж",
        "created_at": "сегодня, 12:19",
    },
    {
        "id": "q-1045",
        "author": "@critic_99",
        "text": "Только полные неудачники смотрят этот канал. Вам здесь не место.",
        "toxicity_score": 71,
        "reason": "Травля и унижение",
        "created_at": "сегодня, 12:27",
    },
)


@lru_cache(maxsize=1024)
def _term_regex(term: str) -> re.Pattern[str]:
    term = term.strip()
    prefix = r"(?<!\w)" if term and term[0].isalnum() else ""
    suffix = r"(?!\w)" if term and term[-1].isalnum() else ""
    return re.compile(prefix + re.escape(term) + suffix, re.IGNORECASE)


def _find_term_ranges(text: str, term: str) -> list[tuple[int, int]]:
    if not text or not term or not term.strip():
        return []
    return [(match.start(), match.end()) for match in _term_regex(term).finditer(text)]


def _merge_ranges(ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    ordered = sorted(ranges)
    if not ordered:
        return []
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def verdict_from_score(score: float) -> str:
    if score >= 60:
        return "rejected"
    if score >= 25:
        return "review"
    return "approved"


def _normalize_verdict(value: Any, score: float) -> str:
    if isinstance(value, str):
        verdict = VERDICT_ALIASES.get(value.strip().lower())
        if verdict:
            return verdict
    return verdict_from_score(score)


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _normalize_score(value: Any, default: float = 0.0) -> int:
    number = _to_number(value)
    if number is None:
        return int(round(default))
    if 0.0 <= number <= 1.0:
        number *= 100
    return int(round(min(100.0, max(0.0, number))))


def _first_value(data: dict[str, Any], keys: Iterable[str], default: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return default


def _as_terms(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def _normalize_patterns(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, (list, tuple)):
        return []
    patterns = []
    for entry in raw:
        if isinstance(entry, str):
            label = entry.strip()
            if label:
                patterns.append(
                    {"label": label, "explanation": "", "matched_terms": []}
                )
        elif isinstance(entry, dict):
            pattern = {
                "label": str(
                    _first_value(
                        entry,
                        (
                            "label",
                            "name",
                            "pattern",
                            "pattern_name",
                            "type",
                            "category",
                            "title",
                        ),
                        "Паттерн",
                    )
                ),
                "explanation": str(
                    _first_value(
                        entry,
                        ("explanation", "description", "reason", "details", "message"),
                        "",
                    )
                ),
                "matched_terms": _as_terms(
                    _first_value(
                        entry,
                        (
                            "matched_terms",
                            "terms",
                            "matches",
                            "words",
                            "highlights",
                            "highlighted_spans",
                            "keywords",
                        ),
                        [],
                    )
                ),
            }
            raw_score = _first_value(entry, ("score", "confidence", "risk"), None)
            if raw_score is not None:
                pattern["score"] = _normalize_score(raw_score)
            patterns.append(pattern)
    return patterns


def _normalize_api_result(payload: dict[str, Any], text: str) -> dict[str, Any]:
    score = _normalize_score(
        _first_value(
            payload,
            (
                "overall_risk_score",
                "risk_score",
                "score",
                "toxicity_score",
                "toxicity",
                "risk",
            ),
            0,
        )
    )
    patterns = _normalize_patterns(
        _first_value(payload, ("patterns", "findings", "matches", "labels"), [])
    )
    verdict = _normalize_verdict(
        _first_value(
            payload,
            (
                "recommended_action",
                "verdict",
                "decision",
                "status",
                "label",
            ),
            "",
        ),
        score,
    )
    return {
        "verdict": verdict,
        "risk_score": score,
        "patterns": patterns,
        "text": text,
    }


def analyze_locally(text: str) -> dict[str, Any]:
    findings = []
    total = 0
    for rule in PATTERN_RULES:
        matched_terms = []
        hit_count = 0
        for term in rule["terms"]:
            count = len(_find_term_ranges(text, term))
            if count:
                matched_terms.append(term)
                hit_count += count
        if not matched_terms:
            continue
        pattern_score = min(
            100,
            int(rule.get("single_hit_score", rule["weight"]))
            + 5 * max(0, hit_count - 1),
        )
        total += pattern_score
        findings.append(
            {
                "label": rule["label"],
                "explanation": rule["explanation"],
                "matched_terms": matched_terms,
                "score": pattern_score,
            }
        )
    score = max(0, min(100, total))
    return {
        "verdict": verdict_from_score(score),
        "risk_score": score,
        "patterns": findings,
        "text": text,
    }


def analyze_comment(text: str) -> tuple[dict[str, Any], str]:
    try:
        response = requests.post(
            MODERATE_URL,
            json={
                "comment_id": f"live-{uuid.uuid4().hex[:10]}",
                "text": text,
                "author_id": "sandbox-user",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected analyze response")
        return _normalize_api_result(payload, text), "api"
    except Exception:
        return analyze_locally(text), "fallback"


def _stable_id(text: str, author: str, index: int) -> str:
    digest = hashlib.sha1(
        f"{author}|{text}|{index}".encode("utf-8")
    ).hexdigest()[:12]
    return f"queue-{digest}"


def _normalize_queue_item(item: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    text = str(_first_value(item, ("text", "comment", "content", "message"), "")).strip()
    if not text:
        return None
    author = (
        str(
            _first_value(
                item,
                ("author", "username", "user", "user_name", "nickname", "author_id"),
                "Аноним",
            )
        ).strip()
        or "Аноним"
    )
    raw_id = _first_value(item, ("id", "comment_id", "uuid", "key"), "")
    item_id = (
        str(raw_id).strip()
        if raw_id not in (None, "")
        else _stable_id(text, author, index)
    )
    return {
        "id": item_id,
        "author": author,
        "text": text,
        "toxicity_score": _normalize_score(
            _first_value(
                item,
                ("toxicity_score", "risk_score", "score", "toxicity"),
                0,
            )
        ),
        "reason": str(
            _first_value(item, ("reason", "category", "label", "explanation"), "")
        ).strip(),
        "created_at": str(
            _first_value(item, ("created_at", "timestamp", "time", "date"), "")
        ).strip(),
    }


def _extract_queue(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = None
        for key in ("items", "queue", "data", "results", "comments"):
            value = payload.get(key)
            if isinstance(value, list):
                raw_items = value
                break
            if isinstance(value, dict):
                nested = _extract_queue(value)
                if nested is not None:
                    return nested
        if raw_items is None:
            return None
    else:
        return None
    items = []
    for index, raw_item in enumerate(raw_items):
        normalized = _normalize_queue_item(raw_item, index)
        if normalized is not None:
            items.append(normalized)
    if raw_items and not items:
        return None
    return items


def load_queue() -> tuple[list[dict[str, Any]], str]:
    try:
        response = requests.get(QUEUE_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        items = _extract_queue(response.json())
        if items is None:
            raise ValueError("Unexpected queue response")
        return items, "api"
    except Exception:
        return [dict(item) for item in MOCK_QUEUE], "fallback"


def _highlight_fragment(text: str, ranges: Iterable[tuple[int, int]]) -> str:
    merged = _merge_ranges(ranges)
    if not merged:
        return html.escape(text)
    parts = []
    position = 0
    for start, end in merged:
        parts.append(html.escape(text[position:start]))
        parts.append(
            '<mark style="background:#ffd7d5;color:#7a1212;border-radius:3px;'
            'padding:0 2px;font-weight:600;">'
            f"{html.escape(text[start:end])}</mark>"
        )
        position = end
    parts.append(html.escape(text[position:]))
    return "".join(parts)


def _highlight_text(text: str, patterns: Iterable[dict[str, Any]]) -> str:
    ranges = []
    for pattern in patterns:
        for term in pattern.get("matched_terms", []) or []:
            ranges.extend(_find_term_ranges(text, str(term)))
    body = _highlight_fragment(text, ranges)
    return (
        '<div style="background:#f7f7f9;border:1px solid #e3e3e8;border-radius:10px;'
        'padding:1rem;white-space:pre-wrap;line-height:1.65;">'
        f"{body}</div>"
    )


def _verdict_badge(verdict: str) -> str:
    style = VERDICT_STYLES.get(verdict, VERDICT_STYLES["review"])
    background = style["bg"]
    foreground = style["fg"]
    label = style["label"]
    return (
        '<span style="display:inline-block;padding:0.45rem 0.9rem;'
        'border-radius:999px;'
        f'background:{background};color:{foreground};font-weight:700;'
        f'font-size:1rem;">{label}</span>'
    )


def _toxicity_badge(score: int) -> str:
    if score >= 60:
        background, foreground = "#fce8e6", "#a50e0e"
    elif score >= 25:
        background, foreground = "#fef7e0", "#9a6700"
    else:
        background, foreground = "#e6f4ea", "#137333"
    return (
        '<span style="display:inline-block;padding:0.3rem 0.65rem;'
        f'border-radius:999px;background:{background};color:{foreground};'
        f'font-weight:600;white-space:nowrap;">Токсичность: {score}%</span>'
    )


def _plain_block(text: str) -> str:
    return (
        '<div style="white-space:pre-wrap;line-height:1.55;margin:0.35rem 0;">'
        f"{html.escape(text)}</div>"
    )


def _shorten(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _init_state() -> None:
    defaults = {
        "queue_items": None,
        "queue_source": "",
        "queue_decisions": {},
        "live_result": None,
        "live_text": "",
        "live_source": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_decision(item_id: str, action: str) -> None:
    st.session_state.queue_decisions[item_id] = action


def _reset_decisions() -> None:
    st.session_state.queue_decisions = {}


def _refresh_queue() -> None:
    st.session_state.queue_items = None
    st.session_state.queue_source = ""


def _render_analysis(
    result: dict[str, Any],
    text: str,
    source: str,
) -> None:
    score = int(result.get("risk_score", 0))
    verdict = str(result.get("verdict", "review"))
    badge_column, progress_column = st.columns([1, 3])
    with badge_column:
        st.markdown(_verdict_badge(verdict), unsafe_allow_html=True)
    with progress_column:
        st.progress(
            min(1.0, max(0.0, score / 100.0)),
            text=f"Общий скор риска: {score}%",
        )
    if source == "api":
        st.caption(f"Источник: FastAPI · {MODERATE_URL}")
    else:
        st.caption(
            "Источник: локальный fallback (FastAPI недоступен) · "
            "эвристические паттерны"
        )

    patterns = result.get("patterns") or []
    st.markdown("#### Сработавшие паттерны")
    if patterns:
        for index, pattern in enumerate(patterns):
            label = str(pattern.get("label", "Паттерн"))
            contribution = pattern.get("score")
            title = (
                f"{label} · вклад {contribution}%"
                if contribution is not None
                else label
            )
            with st.expander(title, expanded=index == 0):
                explanation = str(pattern.get("explanation") or "").strip()
                if explanation:
                    st.write(explanation)
                terms = [str(term) for term in pattern.get("matched_terms") or []]
                if terms:
                    st.caption("Совпадения: " + ", ".join(terms))
    else:
        st.success("Негативные паттерны не обнаружены.")

    st.markdown("#### Подсветка проблемных фрагментов")
    if text:
        st.markdown(_highlight_text(text, patterns), unsafe_allow_html=True)
    else:
        st.info("Нет текста для подсветки.")


def _render_live_tab() -> None:
    st.subheader("Песочница / Live-тест")
    st.caption(
        "Введите любой комментарий и проверьте, какие негативные паттерны "
        "сработают. Результат носит рекомендательный характер."
    )
    text = st.text_area(
        "Комментарий пользователя",
        height=150,
        placeholder="Вставьте комментарий для проверки...",
        key="live_input",
    )
    if st.button("Проверить комментарий", type="primary", key="check_comment"):
        if not text.strip():
            st.warning("Введите текст комментария.")
        else:
            with st.spinner("Анализирую комментарий..."):
                result, source = analyze_comment(text)
            st.session_state.live_result = result
            st.session_state.live_text = text
            st.session_state.live_source = source

    result = st.session_state.live_result
    if result is None:
        return
    st.divider()
    _render_analysis(result, st.session_state.live_text, st.session_state.live_source)


def _render_queue_card(item: dict[str, Any]) -> None:
    item_id = str(item["id"])
    with st.container(border=True):
        author_column, score_column = st.columns([3, 1])
        with author_column:
            st.markdown(f"**{item.get('author', 'Аноним')}**")
            details = [
                str(value)
                for value in (item.get("created_at"), item.get("reason"))
                if value
            ]
            if details:
                st.caption(" · ".join(details))
        with score_column:
            st.markdown(
                _toxicity_badge(int(item.get("toxicity_score", 0))),
                unsafe_allow_html=True,
            )
        st.markdown(
            _plain_block(str(item.get("text", ""))),
            unsafe_allow_html=True,
        )
        approve_column, warn_column, block_column = st.columns(3)
        with approve_column:
            st.button(
                "✅ Одобрить",
                key=f"approve_{item_id}",
                on_click=_set_decision,
                args=(item_id, "approve"),
            )
        with warn_column:
            st.button(
                "⚠️ Предупредить",
                key=f"warn_{item_id}",
                on_click=_set_decision,
                args=(item_id, "warn"),
            )
        with block_column:
            st.button(
                "🚫 Заблокировать",
                key=f"block_{item_id}",
                on_click=_set_decision,
                args=(item_id, "block"),
            )


def _render_queue_tab() -> None:
    st.subheader("Очередь модерации")
    st.button(
        "🔄 Обновить очередь",
        key="refresh_queue",
        on_click=_refresh_queue,
    )

    if st.session_state.queue_items is None:
        with st.spinner("Загружаю очередь..."):
            items, source = load_queue()
        st.session_state.queue_items = items
        st.session_state.queue_source = source

    items = st.session_state.queue_items
    source = st.session_state.queue_source
    decisions = st.session_state.queue_decisions

    if source == "api":
        st.caption(f"Источник: FastAPI · {QUEUE_URL}")
    else:
        st.info(
            "FastAPI недоступен — используется локальный fallback "
            "с демонстрационными комментариями."
        )

    active = [item for item in items if str(item["id"]) not in decisions]
    processed = [item for item in items if str(item["id"]) in decisions]
    st.caption(
        f"На рассмотрении: {len(active)} · Обработано: {len(processed)}"
    )

    if not items:
        st.info("Очередь пуста.")
    elif not active:
        st.success("Все комментарии обработаны.")

    for item in active:
        _render_queue_card(item)

    if processed:
        with st.expander(f"Обработанные комментарии ({len(processed)})"):
            for item in processed:
                action = decisions.get(str(item["id"]), "")
                label = DECISION_LABELS.get(action, action)
                st.markdown(f"**{item.get('author', 'Аноним')}** — {label}")
                st.caption(_shorten(str(item.get("text", "")), 180))
                if item.get("reason"):
                    st.caption(f"Причина: {item['reason']}")
            st.button(
                "↩️ Сбросить обработку",
                key="reset_decisions",
                on_click=_reset_decisions,
            )


def main() -> None:
    st.set_page_config(
        page_title="PatternGuard — модерация UGC",
        page_icon="🛡️",
        layout="wide",
    )
    _init_state()

    with st.sidebar:
        st.title("🛡️ PatternGuard")
        st.caption(
            "Ассистент модерации UGC-контента. "
            "Финальное решение остаётся за человеком."
        )
        st.divider()
        st.caption("API")
        st.code(API_BASE_URL, language=None)
        st.caption(
            "Если API недоступен, дашборд автоматически переключается "
            "на локальный эвристический fallback."
        )

    st.title("PatternGuard — AI Content Moderation Assistant")
    st.caption(
        "Human-in-the-loop: ИИ подсвечивает риски, "
        "а решение принимает модератор."
    )

    live_tab, queue_tab = st.tabs(
        ["Песочница / Live-тест", "Очередь модерации"]
    )
    with live_tab:
        _render_live_tab()
    with queue_tab:
        _render_queue_tab()


if __name__ == "__main__":
    main()
