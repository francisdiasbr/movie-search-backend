"""Portuguese translation of the text a favorite carries, done offline.

IMDB serves trivia, quotes and keywords in English only, so the translation
happens here, once, when the favorite is created (or on demand for older
favorites). The result is stored under `translations.pt` and the client picks
the language on read with `?lang=pt`.

Argos Translate runs a local model (no API key, no network after the first
run). The en->pt package (~100 MB) is downloaded to
~/.local/share/argos-translate the first time a translation is requested.
"""

import logging
import re
import threading

import argostranslate.package
import argostranslate.translate

logger = logging.getLogger(__name__)
# Argos logs every token of every sentence at INFO, on a logger that sets
# its own level, so the parent logger would not silence it.
logging.getLogger("argostranslate.utils").setLevel(logging.WARNING)
logging.getLogger("stanza").setLevel(logging.ERROR)

# Languages the client may ask for. "en" is what IMDB gives; "pt" is translated.
LANGUAGES = ("en", "pt")

# Fields translated. Lists are translated item by item.
TRANSLATED_FIELDS = ("plot", "trivia", "quote", "genres", "plot_keywords")

_translator = None
_translator_lock = threading.Lock()


def _get_translator():
    """The en->pt Argos translation, installing the package on first use."""
    global _translator
    with _translator_lock:
        if _translator is None:
            codes = {
                lang.code for lang in argostranslate.translate.get_installed_languages()
            }
            if not {"en", "pt"} <= codes:
                logger.info("Downloading the Argos en->pt package (first run)")
                argostranslate.package.update_package_index()
                package = next(
                    pkg
                    for pkg in argostranslate.package.get_available_packages()
                    if pkg.from_code == "en" and pkg.to_code == "pt"
                )
                argostranslate.package.install_from_path(package.download())
            _translator = argostranslate.translate.get_translation_from_codes(
                "en", "pt"
            )
        return _translator


# "Character : speech Character : speech" as the scraper stores a quote and
# the frontend's formatQuote parses it. Same expression on both sides.
QUOTE_LINE = re.compile(
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:\s*(.*?)"
    r"(?=\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*:|$)",
    re.DOTALL,
)


def _translate_quote(translator, quote):
    """Translates only the speeches; the character names stay as they are."""
    lines = QUOTE_LINE.findall(quote)
    if not lines:
        return translator.translate(quote)
    return " ".join(
        f"{character} : {translator.translate(speech)}" for character, speech in lines
    )


def _translate_text(translator, text):
    # Line by line keeps the blank line between trivia entries exactly as the
    # scraper produced it.
    return "\n".join(
        translator.translate(line) if line.strip() else line
        for line in text.split("\n")
    )


def _translate_value(translator, field, value):
    if isinstance(value, list):
        return [translator.translate(str(item)).lower() for item in value]
    if field == "quote":
        return _translate_quote(translator, str(value))
    return _translate_text(translator, str(value))


def translate_movie(movie):
    """Returns the Portuguese version of the text fields of `movie`.

    Returns None when there is nothing to translate or when the translator
    fails: the favorite is still worth saving in English, so the caller only
    logs it.
    """
    fields = {
        field: movie.get(field) for field in TRANSLATED_FIELDS if movie.get(field)
    }
    if not fields:
        return None

    try:
        translator = _get_translator()
        translated = {
            field: _translate_value(translator, field, value)
            for field, value in fields.items()
        }
    except Exception as e:
        logger.error("Translation failed for %s: %s", movie.get("tconst"), e)
        return None

    logger.info("Translated %s: %s", movie.get("tconst"), sorted(translated))
    return translated


def localize(movie, lang):
    """`movie` with the `lang` translation applied over the English fields.

    Fields without a translation stay in English. The `translations` map is
    dropped from the answer; the client asked for one language and `lang`
    says which one it got.
    """
    translations = movie.pop("translations", None) or {}
    translation = translations.get(lang) if lang != "en" else None
    movie.update(translation or {})
    # Tells the client which language it actually got: "en" when the
    # translation does not exist yet, so it can ask for one.
    movie["lang"] = lang if translation else "en"
    return movie
