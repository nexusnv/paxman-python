"""Language display name → canonical code mappings.

Source: ISO 639 English Description + IANA Registry
Reference: https://www.iso.org/standard/22109.html
CLDR Source: https://www.unicode.org/cldr/charts/46/summary/root.html

Keys are normalize_name() output (lower, accent-stripped, space-collapsed).
Values are lower canonical language codes (alpha-2 when available, else alpha-3 Term).

Separation: authority-backed tables serving rules only; grammar/data imports keys only.
"""

from __future__ import annotations

# English language names → canonical code (ISO 639 English)
NAME_TO_CANONICAL: dict[str, str] = {
    "english": "en",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "japanese": "ja",
    "chinese": "zh",
    "arabic": "ar",
    "russian": "ru",
    "portuguese": "pt",
    "italian": "it",
    "dutch": "nl",
    "korean": "ko",
    "hindi": "hi",
    "turkish": "tr",
    "polish": "pl",
    "swedish": "sv",
    "danish": "da",
    "norwegian": "no",
    "finnish": "fi",
    "czech": "cs",
    "hebrew": "he",
    "indonesian": "id",
    "yiddish": "yi",
    "moldavian": "ro",
    "cherokee": "chr",
    "bihari": "bih",
    "serbo croatian": "sh",
    "moldovan": "ro",
    "afrikaans": "af",
    "albanian": "sq",
    "amharic": "am",
    "armenian": "hy",
    "azerbaijani": "az",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "bulgarian": "bg",
    "catalan": "ca",
    "croatian": "hr",
    "estonian": "et",
    "georgian": "ka",
    "greek": "el",
    "gujarati": "gu",
    "icelandic": "is",
    "irish": "ga",
    "macedonian": "mk",
    "malay": "ms",
    "maltese": "mt",
    "norwegian bokmal": "nb",
    "persian": "fa",
    "romanian": "ro",
    "serbian": "sr",
    "slovak": "sk",
    "slovenian": "sl",
    "swahili": "sw",
    "thai": "th",
    "ukrainian": "uk",
    "urdu": "ur",
    "vietnamese": "vi",
    "welsh": "cy",
}

# Localized (CLDR) language display names → canonical code (e.g., Deutsch→de)
# Single source for grammar/data/localized_names.py
LOCALIZED_NAME_TO_CANONICAL: dict[str, str] = {
    "deutsch": "de",
    "francais": "fr",
    "espanol": "es",
    "italiano": "it",
    "portugues": "pt",
    "nederlands": "nl",
    "polski": "pl",
    "cesky": "cs",
    "svenska": "sv",
    "dansk": "da",
    "norsk": "no",
    "suomi": "fi",
    "magyar": "hu",
    "greek": "el",
    "russian": "ru",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh",
    "arabic": "ar",
    "hebrew": "he",
    "allemand": "de",
    "anglais": "en",
    "chino": "zh",
    "japones": "ja",
}

# Alias for task description: cldr_map == LOCALIZED_NAME_TO_CANONICAL normalized keys
CLDR_MAP: dict[str, str] = LOCALIZED_NAME_TO_CANONICAL
