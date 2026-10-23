import re
from dataclasses import dataclass


@dataclass
class TextMetadata:
    clean_text: str
    caps_ratio: float
    has_links: bool
    has_contacts: bool


LATIN_TO_CYR = str.maketrans({"a": "а", "o": "о", "c": "с", "e": "е", "p": "р", "x": "х",
                               "A": "А", "O": "О", "C": "С", "E": "Е", "P": "Р", "X": "Х"})
ALLOWED_DOUBLES = {"л", "н", "с", "р", "т"}


class TextCleaner:
    def clean(self, raw_text: str) -> tuple[str, TextMetadata]:
        caps_letters = [c for c in raw_text if c.isalpha()]
        caps_ratio = (sum(1 for c in caps_letters if c.isupper()) / len(caps_letters)) if caps_letters else 0.0
        has_links = bool(re.search(r"https?://\S+|www\.\S+|t\.me/\S+", raw_text, re.IGNORECASE))
        has_contacts = bool(re.search(r"@\w{3,}|(?:\+?\d[\d\s\-()]{7,})", raw_text))

        text = self._normalize_homoglyphs(raw_text)
        text = self._compress_repeats(text)
        text = text.lower()
        text = re.sub(r"\s+", " ", text).strip()
        return text, TextMetadata(clean_text=text, caps_ratio=round(caps_ratio, 3),
                                 has_links=has_links, has_contacts=has_contacts)

    def _normalize_homoglyphs(self, text: str) -> str:
        # Replace latin look-alikes only inside cyrillic words
        def repl(m):
            word = m.group(0)
            return word.translate(LATIN_TO_CYR)
        # match words containing both scripts
        return re.sub(r"[A-Za-zА-Яа-яЁё]+", lambda m: m.group(0).translate(LATIN_TO_CYR) if any("\u0400" <= c <= "\u04ff" for c in m.group(0)) and any("A" <= c <= "z" and c.isalpha() for c in m.group(0)) else m.group(0), text)

    def _compress_repeats(self, text: str) -> str:
        def repl(m):
            ch = m.group(1)
            if ch.lower() in ALLOWED_DOUBLES:
                return ch * 2
            return ch
        return re.sub(r"(.)\1+", repl, text)
