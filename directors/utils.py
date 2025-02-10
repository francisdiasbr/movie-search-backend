from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback
from pydantic import BaseModel, Field
from typing import List, Optional
import json

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
    personal_aspects: Optional[str] = Field(description="Gênero e tema dos filmes dirigidos")
    career_start_year: Optional[int] = Field(description="Ano em que o diretor começou a carreira")
    directed_movies: Optional[int] = Field(description="Número total de filmes dirigidos")

class DirectorInfo(BaseModel):
    """Esquema para informações completas do diretor"""
    movies: List[Movie] = Field(description="Lista dos filmes dirigidos")
    personal_info: PersonalInfo = Field(description="Informações pessoais do diretor")

def get_director_info(api_key, director_name, model):
    """Recupera informações do diretor usando o LLM"""
    try:
        llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0
        )
        
        system_message = """Você é um assistente especializado em cinema com conhecimento profundo sobre diretores.
        Ao fornecer informações sobre filmografia, inclua TODOS os filmes que o diretor dirigiu E escreveu.
        Retorne APENAS um objeto JSON válido, sem formatação adicional ou quebras de linha."""
        
        human_message = f"""Forneça um JSON completo sobre {director_name} incluindo:
        1. Todos os filmes que ele dirigiu
        2. Todos os filmes que ele escreveu
        3. Informações pessoais precisas

        Use exatamente este formato, preenchendo com dados reais, consultados do IMDb:
        {{
            "movies": [
                {{
                    "originalTitle": "Título Original",
                    "primaryTitle": "Título em Português",
                    "tconst": "ID do IMDb",
                    "year": ano de lançamento
                }}
            ],
            "personal_info": {{
                "age": idade atual,
                "birth_date": "data de nascimento",
                "marital_status": "estado civil",
                "relationships": número de casamentos,
                "personal_aspects": "aspectos da carreira e estilo de direção",
                "career_start_year": ano de início da carreira,
                "directed_movies": número total de filmes dirigidos e escritos
            }}
        }}

        Importante:
        - Inclua TODOS os filmes listados no IMDb
        - Inclua curtas-metragens e documentários
        - Use os IDs corretos do IMDb (tconst)
        - Mantenha a precisão das datas e números"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "human", "content": human_message}
        ]

        response = llm.invoke(messages)
        print(f"\nResposta do LLM:\n{response.content}\n")
        
        if not response or not response.content:
            raise ValueError("Resposta vazia do LLM")

        content = response.content.strip()
        if not content.startswith("{"):
            content = content[content.find("{"):]
        if not content.endswith("}"):
            content = content[:content.rfind("}")+1]

        json_response = json.loads(content)
        director_info = DirectorInfo(**json_response)
        result = director_info.model_dump()
        
        return {"data": result}, 200

    except json.JSONDecodeError as e:
        print(f"\nErro ao decodificar JSON: {str(e)}")
        print(f"Conteúdo que causou o erro: {response.content if 'response' in locals() else 'N/A'}\n")
        return {"data": "Erro ao processar resposta do LLM: formato JSON inválido"}, 500
    except Exception as e:
        print(f"\nErro ao processar informações do diretor: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        if 'response' in locals():
            print(f"Conteúdo da resposta: {response.content}\n")
        return {"data": f"Erro ao processar informações do diretor: {str(e)}"}, 500

def llm_decorator(func, obj):
    with get_openai_callback() as cb:
        invoked = func.invoke(obj)
        print('\ncallback\n', cb, '\n')
    return invoked