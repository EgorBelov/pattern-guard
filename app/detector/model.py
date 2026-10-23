"""Модуль детекции деструктивных паттернов."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.schemas import PatternDetectionResult


class BaseDetector(ABC):
    """Абстрактный интерфейс для подключения внешних детекторов."""

    @abstractmethod
    def detect(self, text: str, metadata: Optional[Dict] = None) -> List[PatternDetectionResult]:
        raise NotImplementedError


class PatternDetector(BaseDetector):
    """Базовый эвристический детектор негативных паттернов."""

    def __init__(self):
        # Токсичность/мат/оскорбления
        self.toxic_roots = [
            "идиот",
            "дурак",
            "дебил",
            "кретин",
            "туп",
            "мразь",
            "урод",
            "гнид",
            "сволоч",
            "сука",
            "бляд",
            "хуй",
            "пидор",
            "мудак",
            "придурок",
        ]
        # Пассивная агрессия/сарказм
        self.passive_aggr_patterns = [
            r"с\s+твоим[^\.\!\?]*умом",
            r"умный\s+нашелся",
            r"ясно,\s*автор",
            r"ну\s+конечно",
            r"не\s+подумаешь",
            r"как\s+всегда",
            r"оригинально",
        ]
        # Спам/увод аудитории
        self.spam_patterns = [
            r"пишите\s+в\s+лс",
            r"пиши\s+в\s+лс",
            r"переходи\s+по\s+ссылке",
            r"переходите\s+по\s+ссылке",
            r"легкий\s+заработок",
            r"быстрый\s+заработок",
            r"заработок\s+без\s+вложений",
            r"бесплатн.*деньги",
            r"крипт.*бесплатн",
        ]

    def detect(self, text: str, metadata: Optional[Dict] = None) -> List[PatternDetectionResult]:
        results: List[PatternDetectionResult] = []
        if not text:
            return results

        text_lower = text.lower()

        # 1) Токсичность
        results.extend(self._detect_toxicity(text, text_lower))

        # 2) Пассивная агрессия
        results.extend(self._detect_passive_aggression(text, text_lower))

        # 3) Спам
        results.extend(self._detect_spam(text, text_lower))

        # 4) Капс/агрессивный тон
        results.extend(self._detect_shouting(text, text_lower, metadata))

        return results

    def _detect_toxicity(self, text: str, text_lower: str) -> List[PatternDetectionResult]:
        matches = []
        for root in self.toxic_roots:
            if root in text_lower:
                matches.append(root)

        if not matches:
            return []

        # Выделим фрагменты с найденными триггерами
        highlighted = []
        for root in set(matches):
            # Найдем вхождения в исходном тексте (простая эвристика)
            pattern = re.compile(re.escape(root), re.IGNORECASE)
            for m in pattern.finditer(text):
                highlighted.append(m.group(0))

        score = min(1.0, 0.4 + 0.1 * len(set(matches)))
        return [
            PatternDetectionResult(
                pattern_name="toxicity",
                score=round(score, 3),
                detected=True,
                explanation="Обнаружены прямые оскорбления/нецензурная лексика.",
                highlighted_spans=highlighted[:10],
            )
        ]

    def _detect_passive_aggression(self, text: str, text_lower: str) -> List[PatternDetectionResult]:
        highlighted = []
        for pat in self.passive_aggr_patterns:
            for m in re.finditer(pat, text_lower):
                highlighted.append(text[m.start() : m.end()])

        if not highlighted:
            return []

        score = min(1.0, 0.5 + 0.05 * len(highlighted))
        return [
            PatternDetectionResult(
                pattern_name="passive_aggression",
                score=round(score, 3),
                detected=True,
                explanation="Обнаружены шаблоны пассивной агрессии/сарказма.",
                highlighted_spans=highlighted[:10],
            )
        ]

    def _detect_spam(self, text: str, text_lower: str) -> List[PatternDetectionResult]:
        highlighted = []
        for pat in self.spam_patterns:
            for m in re.finditer(pat, text_lower):
                highlighted.append(text[m.start() : m.end()])

        if not highlighted:
            return []

        score = min(1.0, 0.6 + 0.05 * len(highlighted))
        return [
            PatternDetectionResult(
                pattern_name="spam_invite",
                score=round(score, 3),
                detected=True,
                explanation="Обнаружены признаки спама/увода аудитории.",
                highlighted_spans=highlighted[:10],
            )
        ]

    def _detect_shouting(self, text: str, text_lower: str, metadata: Optional[Dict] = None) -> List[PatternDetectionResult]:
        # Игнорируем короткие тексты
        letters = [c for c in text if c.isalpha()]
        if len(letters) < 5:
            return []

        upper = sum(1 for c in letters if c.isupper())
        ratio = upper / len(letters)

        # Также проверим метаданные
        if metadata and metadata.get("caps_ratio") is not None:
            try:
                ratio = max(ratio, float(metadata["caps_ratio"]))
            except Exception:
                pass

        if ratio < 0.5:
            return []

        highlighted = []
        # Выделим слова в капсе
        for m in re.finditer(r"\b[А-ЯA-Z]{4,}\b", text):
            highlighted.append(m.group(0))

        score = min(1.0, ratio)
        return [
            PatternDetectionResult(
                pattern_name="shouting",
                score=round(score, 3),
                detected=True,
                explanation="Высокая доля заглавных букв / агрессивный тон.",
                highlighted_spans=highlighted[:10],
            )
        ]


if __name__ == "__main__":
    detector = PatternDetector()

    examples = [
        "Ты просто идиот, как можно так думать?",
        "С твоим-то умом мне вас учить...",
        "Пишите в лс за БЕСПЛАТНЫЙ заработок без вложений!",
        "ЭТО ПРОСТО НЕВЕРОЯТНО!! КАК ТАК МОЖНО!!!",
    ]

    for ex in examples:
        print("=" * 60)
        print("Текст:", ex)
        results = detector.detect(ex)
        for r in results:
            print(f"- {r.pattern_name}: score={r.score}, detected={r.detected}")
            print(f"  explanation: {r.explanation}")
            print(f"  highlighted: {r.highlighted_spans}")
