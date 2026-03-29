# region --- Localization ---
import json
import os
from pathlib import Path

from .constants import DEFAULT_WINDOW_SIZE

LANG_CODE_MAP = {
    "english": "en",
    "en": "en",
    "spanish": "es",
    "es": "es",
    "español": "es",
    "espanol": "es",
    "french": "fr",
    "français": "fr",
    "francais": "fr",
    "fr": "fr",
    "german": "de",
    "deutsch": "de",
    "de": "de",
    "italian": "it",
    "italiano": "it",
    "it": "it",
    "portuguese": "pt",
    "português": "pt",
    "portugues": "pt",
    "pt": "pt",
    "russian": "ru",
    "русский": "ru",
    "ru": "ru",
    "chinese": "zh",
    "中文": "zh",
    "zh": "zh",
    "japanese": "ja",
    "日本語": "ja",
    "ja": "ja",
}

def _guess_lang_code(name: str):
    if not name:
        return "en"
    n = name.lower()
    for k, v in LANG_CODE_MAP.items():
        if k in n:
            return v
    # fallback to first two letters
    return n[:2]

def load_translations_for(language_name: str):
    code = _guess_lang_code(language_name)
    path = Path("lang") / f"{code}.json"
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # fallback to English built-in
    try:
        with open(Path("lang") / "en.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def list_available_languages():
    """Return list of (code, display_name) for available language JSONs in ./lang.
    Falls back to a sensible default list if ./lang is missing or incomplete.
    """
    mapping = {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "it": "Italiano",
        "pt": "Português",
        "ru": "Русский",
        "zh": "中文",
        "ja": "日本語",
    }
    results = []
    try:
        lang_dir = Path("lang")
        if lang_dir.exists():
            for p in sorted(lang_dir.glob("*.json")):
                code = p.stem
                display = mapping.get(code, code)
                results.append((code, display))
    except Exception:
        results = []

    # Ensure common languages exist in the list in a sane order
    for code in ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"]:
        if not any(r[0] == code for r in results):
            results.append((code, mapping.get(code, code)))

    return results

class TranslationManager:
    def __init__(self, initial_language="English"):
        self.translations = load_translations_for(initial_language)
    
    def update_language(self, language_name: str):
        self.translations = load_translations_for(language_name)
    
    def t(self, key: str, **kwargs):
        txt = self.translations.get(key, key)
        try:
            return txt.format(**kwargs) if kwargs else txt
        except Exception:
            return txt

# Global translation manager instance
_translation_manager = None

def init_translations(language_name="English"):
    global _translation_manager
    _translation_manager = TranslationManager(language_name)

def t(key: str, **kwargs):
    global _translation_manager
    if _translation_manager is None:
        init_translations()
    return _translation_manager.t(key, **kwargs)
# endregion
