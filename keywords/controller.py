import logging

import anthropic
from pydantic import ValidationError

import db
from config import ANTHROPIC_API_KEY, KEYWORDS_COLLECTION, SUGGESTION_MODEL, get_mongo_collection
from favorites.scrapper import clear_soup_cache, get_movie_genres
from keywords.imdb import find_imdb_title
from keywords.schemas import MovieSuggestions
from utils import error

logger = logging.getLogger(__name__)


def keywords():
    return get_mongo_collection(KEYWORDS_COLLECTION)


def add_keyword(keyword):
    keyword = str(keyword or "").strip()
    if not keyword:
        return error("Keyword is required", 400)

    collection = keywords()
    if collection.find_one({"keyword": keyword}):
        return error("Keyword already listed", 409)

    return {"data": db.insert(collection, {"keyword": keyword})}, 201


def get_favorited_keywords():
    _, entries = db.search(keywords(), projection={"keyword": 1}, sort=("keyword", 1))
    return {"data": entries}, 200


def delete_favorited_keyword(keyword):
    if not db.delete(keywords(), {"keyword": keyword}):
        return error("Keyword not found", 404)
    return {"data": "Keyword deleted successfully"}, 200


SUGGESTION_SYSTEM_PROMPT = (
    "Você é um curador de cinema especializado em encontrar filmes em que as palavras-chave "
    "fornecidas aparecem de forma literal e explícita: personagens, cenas, profissões, objetos, "
    "lugares, temas ou elementos diretamente relacionados a elas.\n"
    "Evite o óbvio: não indique só filmes muito conhecidos, pois a vantagem desta sugestão é "
    "descobrir títulos novos. Varie épocas, países e gêneros.\n"
    "Um filme não precisa conter todas as palavras-chave. Basta casar fortemente com uma delas; "
    "liste primeiro os que casam com várias.\n"
    "Sugira apenas filmes que existem e estão listados no IMDb; nunca invente títulos. "
    "Informe sempre o título original exatamente como aparece no IMDb.\n"
    "Não faça interpretações metafóricas ou subjetivas das palavras-chave."
)

SUGGESTION_USER_PROMPT = (
    "Com base nas palavras-chave: {keywords},\n"
    "sugira de 10 a 15 filmes em que ao menos uma das palavras-chave esteja presente de forma "
    "literal. Comece pelos filmes que combinam mais palavras-chave.\n"
    "Para cada filme, forneça:\n"
    "- Título\n"
    "- Título original, como listado no IMDb\n"
    "- Ano de lançamento\n"
    "- ID do IMDb (tconst) no formato 'tt1234567' ou 'tt12345678'\n"
    "- Uma breve descrição (2-3 linhas)\n"
    "- Explique de forma objetiva quais palavras-chave aparecem no filme e como"
)


def suggest_movies_by_keywords(keywords):
    """Asks Claude for 10 to 15 movies that literally feature the keywords.

    More than the client needs on purpose: `_verified_on_imdb` drops the ones
    IMDB does not recognise.

    `output_format` makes the answer come back already validated against the
    MovieSuggestions pydantic schema.
    """
    try:
        response = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.parse(
            model=SUGGESTION_MODEL,
            # Thinking tokens share this budget with the answer; too low a value
            # truncates the JSON mid-string and the schema validation fails.
            max_tokens=16000,
            output_config={"effort": "medium"},
            system=SUGGESTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": SUGGESTION_USER_PROMPT.format(keywords=", ".join(keywords)),
                }
            ],
            output_format=MovieSuggestions,
        )
    except anthropic.APIError as e:
        logger.error("Claude suggestion failed: %s", e)
        return error("Falha ao gerar sugestões de filmes", 502)
    except ValidationError as e:
        # The answer came back but does not fit MovieSuggestions (truncated or
        # off-schema); the client can simply try again.
        logger.error("Claude suggestion did not match the schema: %s", e)
        return error("A sugestão veio em formato inválido, tente novamente", 502)

    return {"data": {"movies": _verified_on_imdb(response.parsed_output.movies)}}, 200


def _verified_on_imdb(suggestions):
    """Keeps only the suggestions IMDB knows, with the real tconst and genres.

    The model's tconst is a guess and is replaced by the one IMDB returns for
    the title + year; suggestions IMDB cannot find are dropped and logged.
    Genres come from the IMDB title page through the favorites scraper, since
    the suggestion API does not list them; when a page fails to load the
    genres stay empty and the remaining pages are not even tried.
    """
    verified = []
    genres_available = True
    for suggestion in suggestions:
        match = find_imdb_title(suggestion.title, suggestion.year, suggestion.original_title)
        if not match:
            logger.info(
                "Dropping suggestion not found on IMDB: %r (%s)", suggestion.title, suggestion.year
            )
            continue
        movie = suggestion.model_dump()
        movie.update(tconst=match["tconst"], original_title=match["title"], year=match["year"])
        # One page that fails to load almost always means the WAF session
        # expired, and every other page would fail (and retry) the same way.
        genres = _genres(match["tconst"]) if genres_available else None
        if genres is None:
            genres_available = False
        movie["genres"] = genres or []
        verified.append(movie)
    clear_soup_cache()
    return verified


def _genres(tconst):
    """Genres from the IMDB title page, or None when the page did not load."""
    try:
        return get_movie_genres(tconst)
    except Exception as e:
        logger.warning("Could not fetch genres for %s: %s", tconst, e)
        return None
