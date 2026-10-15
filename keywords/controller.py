import logging

from openai import OpenAI

import db
from config import KEYWORDS_COLLECTION, OPENAI_API_KEY, get_mongo_collection
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


def suggest_movies_by_keywords(keywords):
    """Sugere filmes baseado em uma lista de palavras-chave usando OpenAI"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um curador de cinema especializado em encontrar filmes que contenham, de forma literal e explícita, as palavras-chave fornecidas. Porém não seja óbvio indicando somente filmes muito conhecidos, pois a vantagem desta sugestão é conhecer o novo.\n"
                        "Só sugira filmes que realmente apresentem personagens, cenas, profissões, temas ou elementos diretamente relacionados às palavras-chave, de maneira objetiva.\n"
                        "Não faça interpretações metafóricas, filosóficas ou subjetivas das palavras-chave. Se não encontrar filmes suficientes, retorne apenas os que realmente se encaixam."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Com base nas palavras-chave: {', '.join(keywords)},\n"
                        "sugira até 5 filmes em que as palavras-chave estejam presentes de forma literal.\n"
                        "Para cada filme, forneça:\n"
                        "- Título\n"
                        "- Ano de lançamento\n"
                        "- ID do IMDb (tconst) no formato 'tt1234567' ou 'tt12345678'\n"
                        "- Uma breve descrição (2-3 linhas)\n"
                        "- Explique de forma objetiva como as palavras-chave aparecem no filme\n\n"
                        "Se não houver filmes suficientes, retorne apenas os que realmente se encaixam. Não force relação!"
                    ),
                },
            ],
            response_format=MovieSuggestions,
        )

        return {"data": response.choices[0].message.parsed.model_dump()}, 200

    except Exception as e:
        logger.error("OpenAI suggestion failed: %s", e)
        return error("Falha ao gerar sugestões de filmes", 502)
