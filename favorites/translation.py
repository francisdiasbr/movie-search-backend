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
from concurrent.futures import ThreadPoolExecutor

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


def _translate_list(translator, items):
    """Translates the items (keywords, genres) in a single model call.

    Every call pays for sentence splitting and model warm-up, so 50 keywords
    one by one cost about six times more than the same keywords joined by
    newlines, which Argos keeps in place. Falls back to item by item when the
    line count does not match, so no keyword ever maps to the wrong one.
    """
    items = [str(item).replace("\n", " ") for item in items]
    lines = translator.translate("\n".join(items)).split("\n")
    if len(lines) != len(items):
        logger.warning(
            "Batched translation returned %d lines for %d items, retrying one by one",
            len(lines),
            len(items),
        )
        lines = [translator.translate(item) for item in items]
    return [line.lower() for line in lines]


def _translate_value(translator, field, value):
    if isinstance(value, list):
        return _translate_list(translator, value)
    if field == "quote":
        return _translate_quote(translator, str(value))
    return _translate_text(translator, str(value))


def translate_field(field, value):
    """The Portuguese version of one field, or None when it is not translated."""
    if field not in TRANSLATED_FIELDS or not value:
        return None
    return _translate_value(_get_translator(), field, value)


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


class BackgroundTranslation:
    """Translates fields on a worker thread while the caller keeps scraping.

    Translation is the single most expensive step of a favorite (about 10 s,
    mostly trivia) and each field only depends on its own IMDB page, so the
    text is handed over as soon as it is scraped and the model runs while the
    next pages load. One worker, because the Argos pipeline is not known to be
    thread-safe; the fields queue up and still finish long before the pages.
    """

    def __init__(self, tconst):
        self._tconst = tconst
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._futures = {}

    def submit(self, field, value):
        if field in TRANSLATED_FIELDS and value:
            self._futures[field] = self._executor.submit(translate_field, field, value)

    def cancel(self):
        """Drops the queued fields; whatever is being translated finishes alone."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def result(self):
        """Waits for the queue and returns the translation, or None on failure.

        Same contract as `translate_movie`: a failed field drops the whole
        Portuguese version, the favorite is saved in English and
        POST /<tconst>/translate can retry later.
        """
        self._executor.shutdown(wait=True)
        translated = {}
        for field, future in self._futures.items():
            try:
                translated[field] = future.result()
            except Exception as e:
                logger.error("Translation failed for %s: %s", self._tconst, e)
                return None
        if translated:
            logger.info("Translated %s: %s", self._tconst, sorted(translated))
        return translated or None


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
