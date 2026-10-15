import logging

import anthropic
from pydantic import ValidationError

import db
from config import ANTHROPIC_API_KEY, KEYWORDS_COLLECTION, SUGGESTION_MODEL, get_mongo_collection
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
    "Você é um curador de cinema especializado em encontrar filmes que contenham, de forma "
    "literal e explícita, as palavras-chave fornecidas. Porém não seja óbvio indicando somente "
    "filmes muito conhecidos, pois a vantagem desta sugestão é conhecer o novo.\n"
    "Só sugira filmes que realmente apresentem personagens, cenas, profissões, temas ou "
    "elementos diretamente relacionados às palavras-chave, de maneira objetiva.\n"
    "Sugira apenas filmes que existem e estão listados no IMDb; nunca invente títulos. "
    "Informe sempre o título original exatamente como aparece no IMDb.\n"
    "Não faça interpretações metafóricas, filosóficas ou subjetivas das palavras-chave. Se não "
    "encontrar filmes suficientes, retorne apenas os que realmente se encaixam."
)

SUGGESTION_USER_PROMPT = (
    "Com base nas palavras-chave: {keywords},\n"
    "sugira até 5 filmes em que as palavras-chave estejam presentes de forma literal.\n"
    "Para cada filme, forneça:\n"
    "- Título\n"
    "- Título original, como listado no IMDb\n"
    "- Ano de lançamento\n"
    "- ID do IMDb (tconst) no formato 'tt1234567' ou 'tt12345678'\n"
    "- Uma breve descrição (2-3 linhas)\n"
    "- Explique de forma objetiva como as palavras-chave aparecem no filme\n\n"
    "Se não houver filmes suficientes, retorne apenas os que realmente se encaixam. "
    "Não force relação!"
)


def suggest_movies_by_keywords(keywords):
    """Asks Claude for up to five movies that literally feature the keywords.

    `output_format` makes the answer come back already validated against the
    MovieSuggestions pydantic schema.
    """
    try:
        response = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.parse(
            model=SUGGESTION_MODEL,
            # Thinking tokens share this budget with the answer; too low a value
            # truncates the JSON mid-string and the schema validation fails.
            max_tokens=16000,
            output_config={"effort": "low"},
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
    """Keeps only the suggestions IMDB knows, with the real tconst.

    The model's tconst is a guess and is replaced by the one IMDB returns for
    the title + year; suggestions IMDB cannot find are dropped and logged.
    """
    verified = []
    for suggestion in suggestions:
        match = find_imdb_title(suggestion.title, suggestion.year, suggestion.original_title)
        if not match:
            logger.info(
                "Dropping suggestion not found on IMDB: %r (%s)", suggestion.title, suggestion.year
            )
            continue
        movie = suggestion.model_dump()
        movie.update(tconst=match["tconst"], original_title=match["title"], year=match["year"])
        verified.append(movie)
    return verified
