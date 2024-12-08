from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback
from pydantic import BaseModel, Field
from typing import List

class Movie(BaseModel):
    """Esquema para um filme"""
    originalTitle: str = Field(description="Nome original do filme")
    primaryTitle: str = Field(description="Nome primário do filme")
    tconst: str = Field(description="Código do filme")
    year: int = Field(description="Ano de exibição do filme")

class MoviesList(BaseModel):
    """Esquema para uma lista de filmes"""
    movies: List[Movie] = Field(description="Lista de filmes dirigidos")

def get_filmography(api_key, director_name, instruction, model):
    llm = ChatOpenAI(api_key=api_key, model=model)

    data_object = {
        "director": director_name,
        "instruction": instruction
    }

    try:
        conversation = []

        human_message = f"Diretor: {director_name}"
        system_message = f"Instrução: {instruction}"

        conversation.append(("human", human_message))
        conversation.append(("system", system_message))

        route_prompt = ChatPromptTemplate.from_messages(conversation)

        llm_router = llm.with_structured_output(schema=MoviesList)
        
        llm_chain = route_prompt | llm_router

        response = llm_decorator(llm_chain, data_object)

        movies_list = [movie.dict() for movie in response.movies]

        return {"ok": True, "data": movies_list}, 200

    except Exception as error:
        print(f"\nException: {error}\n")
        return {"ok": False, "data": str(error)}, 500

def llm_decorator(func, obj):
    with get_openai_callback() as cb:
        invoked = func.invoke(obj)
        print('\ncallback\n', cb, '\n')
    return invoked 