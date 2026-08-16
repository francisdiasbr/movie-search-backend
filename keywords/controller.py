import logging

from openai import OpenAI

from config import get_mongo_collection, OPENAI_API_KEY
from keywords.schemas import MovieSuggestions

logger = logging.getLogger(__name__)

COLLECTION_NAME = "favorites_keywords"


def add_keyword(keyword):
    """Adiciona uma palavra-chave aos favoritos"""
    if not keyword:
        return {"data": "Keyword is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    if collection.find_one({"keyword": keyword}):
        return {"data": "Keyword already listed"}, 409

    try:
        inserted_id = collection.insert_one({"keyword": keyword}).inserted_id
        return {"data": {"_id": str(inserted_id), "keyword": keyword}}, 201
    except Exception as e:
        logger.error("Error: %s", e)
        return {"data": "Failed to add keyword"}, 500


def get_favorited_keywords():
    """Recupera todas as palavras-chave favoritas"""
    collection = get_mongo_collection(COLLECTION_NAME)
    try:
        keywords = list(collection.find({}, {"_id": 1, "keyword": 1}))
        # Converte ObjectId para string
        for keyword in keywords:
            keyword["_id"] = str(keyword["_id"])
        return {"data": keywords}, 200
    except Exception as e:
        logger.error("Error: %s", e)
        return {"data": "Failed to retrieve keywords"}, 500


def delete_favorited_keyword(keyword):
    """Remove uma palavra-chave dos favoritos"""
    if not keyword:
        return {"data": "Keyword is required"}, 400

    collection = get_mongo_collection(COLLECTION_NAME)

    try:
        result = collection.delete_one({"keyword": keyword})
        if result.deleted_count:
            return {"data": "Keyword deleted successfully"}, 200
        return {"data": "Keyword not found"}, 404
    except Exception as e:
        logger.error("Error: %s", e)
        return {"data": "Failed to delete keyword"}, 500


def suggest_movies_by_keywords(keywords):
    """Sugere filmes baseado em uma lista de palavras-chave usando OpenAI"""
    if not keywords or not isinstance(keywords, list):
        return {"data": "Lista de keywords é obrigatória"}, 400

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
        logger.error("Error: %s", e)
        return {"data": "Falha ao gerar sugestões de filmes"}, 500
