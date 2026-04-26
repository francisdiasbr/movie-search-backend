from flask import request, jsonify
from config import get_mongo_collection
from openai import OpenAI
from pydantic import BaseModel, Field, constr, conint
from typing import List
from config import OPENAI_API_KEY

COLLECTION_NAME = "favorites_keywords"


class MovieSuggestion(BaseModel):
    """Modelo para sugestão de filme"""

    title: constr(min_length=1, max_length=200) = Field(
        description="Título do filme", examples=["O Poderoso Chefão", "Fight Club"]
    )
    year: conint(ge=1888, le=2024) = Field(
        description="Ano de lançamento do filme", examples=[1972, 1999]
    )
    tconst: constr(pattern=r"^tt\d{7,8}$") = Field(
        description="IMDb ID (tconst) do filme", examples=["tt0068646", "tt0137523"]
    )
    description: constr(min_length=50, max_length=500) = Field(
        description="Breve descrição do filme (2-3 linhas)",
        examples=[
            "A saga da família Corleone, uma poderosa dinastia mafiosa italiana nos Estados Unidos, liderada por Don Vito Corleone."
        ],
    )
    relevance: constr(min_length=50, max_length=500) = Field(
        description="Explicação de como o filme se relaciona com as palavras-chave",
        examples=[
            "Dirigido por Francis Ford Coppola, este filme é um clássico absoluto sobre a máfia italiana, explorando temas de poder, família e crime."
        ],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "O Poderoso Chefão",
                "year": 1972,
                "tconst": "tt0068646",
                "description": "A saga da família Corleone, uma poderosa dinastia mafiosa italiana nos Estados Unidos, liderada por Don Vito Corleone.",
                "relevance": "Dirigido por Francis Ford Coppola, este filme é um clássico absoluto sobre a máfia italiana, explorando temas de poder, família e crime.",
            }
        }


class MovieSuggestions(BaseModel):
    """Modelo para lista de sugestões de filmes"""

    movies: List[MovieSuggestion] = Field(
        description="Lista de sugestões de filmes", min_items=1, max_items=5
    )

    class Config:
        json_schema_extra = {
            "example": {
                "movies": [
                    {
                        "title": "O Poderoso Chefão",
                        "year": 1972,
                        "tconst": "tt0068646",
                        "description": "A saga da família Corleone, uma poderosa dinastia mafiosa italiana nos Estados Unidos, liderada por Don Vito Corleone.",
                        "relevance": "Dirigido por Francis Ford Coppola, este filme é um clássico absoluto sobre a máfia italiana, explorando temas de poder, família e crime.",
                    }
                ]
            }
        }


def add_keyword(keyword):
    """Adiciona uma palavra-chave aos favoritos"""
    if not keyword:
        return {"data": "Keyword is required"}, 400

    collection_atlas = get_mongo_collection(COLLECTION_NAME, use_atlas=True)
    collection_local = get_mongo_collection(COLLECTION_NAME, use_atlas=False)

    # Verifica se a palavra-chave já está na lista de favoritos
    existing_keyword_atlas = collection_atlas.find_one({"keyword": keyword})
    existing_keyword_local = collection_local.find_one({"keyword": keyword})

    if existing_keyword_atlas or existing_keyword_local:
        return {"data": "Keyword already listed"}, 409

    try:
        # Insere em ambas as coleções
        result_atlas = collection_atlas.insert_one({"keyword": keyword})
        result_local = collection_local.insert_one({"keyword": keyword})

        inserted_keyword = collection_atlas.find_one({"_id": result_atlas.inserted_id})
        if inserted_keyword:
            return {
                "data": {
                    "_id": str(inserted_keyword["_id"]),
                    "keyword": inserted_keyword["keyword"],
                }
            }, 201
        return {"data": "Failed to retrieve inserted keyword"}, 500
    except Exception as e:
        print(f"Error: {e}")
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
        print(f"Error: {e}")
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
        print(f"Error: {e}")
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
        print(f"Error: {e}")
        return {"data": "Falha ao gerar sugestões de filmes"}, 500
