from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback
from pydantic import BaseModel, Field
from typing import List, Optional
import time

class Movie(BaseModel):
    """Esquema para um filme"""
    originalTitle: str = Field(description="Nome original do filme")
    primaryTitle: str = Field(description="Nome primário do filme")
    tconst: str = Field(description="Código do filme")
    year: int = Field(description="Ano de exibição do filme")

class PersonalInfo(BaseModel):
    """Esquema para informações pessoais do diretor"""
    age: Optional[int] = Field(description="Idade do diretor")
    birth_date: Optional[str] = Field(description="Data de nascimento do diretor")
    marital_status: Optional[str] = Field(description="Estado civil do diretor")
    relationships: Optional[int] = Field(description="Número de relacionamentos do diretor")
    personal_aspects: Optional[str] = Field(description="Aspectos pessoais do diretor")

class DirectorInfo(BaseModel):
    """Esquema para informações completas do diretor"""
    movies: List[Movie] = Field(description="Lista de filmes dirigidos")
    personal_info: PersonalInfo = Field(description="Informações pessoais do diretor")


# função para recuperar a filmografia e informações pessoais do diretor
def get_director_info(api_key, director_name, model):
    start_time = time.perf_counter()  # Início da medição de tempo
    llm = ChatOpenAI(api_key=api_key, model=model)

    # Criação da instrução dentro da função
    instruction = (
        f"Retorne a filmografia, em ordem ascendente, dos filmes dirigidos pelo diretor {director_name}. "
        "Além disso, forneça a idade, data de nascimento, estado civil, número de relacionamentos e aspectos pessoais do diretor. "
        "Retorne apenas o nome original do filme, o nome primário, o código ID IMDb do filme, e as informações pessoais solicitadas."
    )

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

        llm_router = llm.with_structured_output(schema=DirectorInfo)
        
        llm_chain = route_prompt | llm_router

        response = llm_decorator(llm_chain, data_object)

        director_info = response.dict()  # Acessa todas as informações do diretor

        elapsed_time = time.perf_counter() - start_time  # Fim da medição de tempo
        print(f"Tempo para recuperar filmografia: {elapsed_time:.5f} segundos")

        return {"ok": True, "data": director_info}, 200

    except Exception as error:
        print(f"\nException: {error}\n")
        return {"ok": False, "data": str(error)}, 500

def llm_decorator(func, obj):
    with get_openai_callback() as cb:
        invoked = func.invoke(obj)
        print('\ncallback\n', cb, '\n')
    return invoked 