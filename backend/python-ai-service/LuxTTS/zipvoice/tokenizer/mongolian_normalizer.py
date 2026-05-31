"""
Mongolian Text Normalizer for LuxTTS
Монгол текстийг TTS-д бэлтгэх normalizer

Handles:
- Cyrillic Mongolian (Кирилл)
- Number → word expansion (тоо → үг)
- Abbreviation expansion
- Punctuation mapping
"""
import re
from typing import Dict


# Mongolian digits 0-9
MN_DIGITS = {
    "0": "тэг",
    "1": "нэг",
    "2": "хоёр",
    "3": "гурав",
    "4": "дөрөв",
    "5": "тав",
    "6": "зургаа",
    "7": "долоо",
    "8": "найм",
    "9": "ес",
}

MN_TENS = {
    1: "арав",
    2: "хорь",
    3: "гуч",
    4: "дөч",
    5: "тавь",
    6: "жар",
    7: "дал",
    8: "ная",
    9: "ер",
}

MN_HUNDREDS = {
    1: "нэг зуу",
    2: "хоёр зуу",
    3: "гурван зуу",
    4: "дөрвөн зуу",
    5: "таван зуу",
    6: "зургаан зуу",
    7: "долоон зуу",
    8: "найман зуу",
    9: "есөн зуу",
}

# Common abbreviations
MN_ABBREVIATIONS: Dict[str, str] = {
    "гэх мэт": "гэх мэт",
    "г.м": "гэх мэт",
    "г.м.": "гэх мэт",
    "ж.нь": "жишээ нь",
    "ж.нь.": "жишээ нь",
    "тэд": "тэд",
    "д-р": "доктор",
    "проф": "профессор",
    "хот": "хот",
    "МУ": "Монгол улс",
    "УБ": "Улаанбаатар",
    "ТВ": "телевиз",
    "утас": "утас",
    "№": "дугаар ",
    "©": "",
    "®": "",
    "™": "",
}


def number_to_mongolian(n: int) -> str:
    """Convert integer to Mongolian words."""
    if n == 0:
        return "тэг"
    if n < 0:
        return "хасах " + number_to_mongolian(-n)

    parts = []

    if n >= 1_000_000:
        m = n // 1_000_000
        parts.append(number_to_mongolian(m) + " сая")
        n %= 1_000_000

    if n >= 1_000:
        m = n // 1_000
        parts.append(number_to_mongolian(m) + " мянга")
        n %= 1_000

    if n >= 100:
        m = n // 100
        parts.append(MN_HUNDREDS.get(m, number_to_mongolian(m) + " зуу"))
        n %= 100

    if n >= 10:
        m = n // 10
        parts.append(MN_TENS.get(m, ""))
        n %= 10

    if n > 0:
        parts.append(MN_DIGITS.get(str(n), str(n)))

    return " ".join(p for p in parts if p)


class MongolianTextNormalizer:
    """Normalize Mongolian Cyrillic text for TTS."""

    def __init__(self):
        # Compile abbreviation patterns (longest first)
        self._abbrev_patterns = [
            (re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), v)
            for k, v in sorted(MN_ABBREVIATIONS.items(), key=lambda x: -len(x[0]))
        ]
        self._number_re = re.compile(r"\d+(?:[.,]\d+)?")
        self._ordinal_re = re.compile(r"(\d+)-р\b")  # 5-р сар → тавдугаар сар

    def normalize(self, text: str) -> str:
        # Ordinals first: 5-р → тавдугаар
        text = self._ordinal_re.sub(lambda m: self._ordinal(int(m.group(1))), text)

        # Abbreviations
        for pattern, replacement in self._abbrev_patterns:
            text = pattern.sub(replacement, text)

        # Numbers
        text = self._number_re.sub(lambda m: self._normalize_number(m.group()), text)

        # Clean up extra spaces
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _normalize_number(self, s: str) -> str:
        """Handle integers and decimals."""
        s = s.replace(",", ".")
        try:
            if "." in s:
                int_part, dec_part = s.split(".", 1)
                result = number_to_mongolian(int(int_part)) + " цэг "
                result += " ".join(MN_DIGITS.get(d, d) for d in dec_part)
                return result
            else:
                return number_to_mongolian(int(s))
        except ValueError:
            return s

    def _ordinal(self, n: int) -> str:
        """Convert ordinal number: 5 → тавдугаар"""
        ordinal_map = {
            1: "нэгдүгээр", 2: "хоёрдугаар", 3: "гуравдугаар",
            4: "дөрөвдүгөөр", 5: "тавдугаар", 6: "зургаадугаар",
            7: "долоодугаар", 8: "наймдугаар", 9: "есдүгөөр",
            10: "аравдугаар", 11: "арван нэгдүгээр", 12: "арван хоёрдугаар",
        }
        return ordinal_map.get(n, number_to_mongolian(n) + "дугаар")


if __name__ == "__main__":
    norm = MongolianTextNormalizer()
    tests = [
        "2024 онд 5-р сарын 15-нд",
        "1000000 төгрөг",
        "3.14 тоо",
        "УБ хотод 12 цаг болоход",
    ]
    for t in tests:
        print(f"{t!r} → {norm.normalize(t)!r}")
