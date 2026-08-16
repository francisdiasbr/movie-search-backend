"""Structured output schema for the OpenAI movie suggestions.

Passed as `response_format` in the chat completion, so the model is forced to
answer in exactly this shape. It is a contract with OpenAI, not with Mongo -
the Swagger counterpart lives in routes.py as a flask-restx model.
"""

from datetime import date
from typing import List

from pydantic import BaseModel, Field, conint, constr

# Movies get announced before they premiere, so next year is allowed.
LATEST_YEAR = date.today().year + 1


class MovieSuggestion(BaseModel):
    """Modelo para sugestão de filme"""

    title: constr(min_length=1, max_length=200) = Field(
        description="Título do filme", examples=["O Poderoso Chefão", "Fight Club"]
    )
    year: conint(ge=1888, le=LATEST_YEAR) = Field(
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


class MovieSuggestions(BaseModel):
    """Modelo para lista de sugestões de filmes"""

    movies: List[MovieSuggestion] = Field(
        description="Lista de sugestões de filmes", min_items=1, max_items=5
    )
