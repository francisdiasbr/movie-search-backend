from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback
from pydantic import BaseModel, Field
from typing import List, Optional
import time

class BlogPostTrivia(BaseModel):
    """Esquema para o trívia de uma postagem de blog"""
    director_history: str = Field(description="História do diretor e relação do filme com ele", min_length=100)
    director_quotes: str = Field(description="Citações. Extraia do IMDb", min_length=100)
    curiosities: str = Field(description="Curiosidades sobre o filme", min_length=100)
    reception: str = Field(description="Recepção do filme", min_length=100)
    highlights: str = Field(description="Destaques do filme. Fale sobre os pontos fortes do filme e em como ele ficou conhecido", min_length=100)
    plot: str = Field(description="Enredo do filme", min_length=100)


# Função para geraro trivia de uma postagem de blog
def generate_blog_post_trivia(api_key, movie_data, model, temperature=0.5, max_tokens=3000):
    start_time = time.perf_counter()  # Início da medição de tempo
    llm = ChatOpenAI(api_key=api_key, model=model, temperature=temperature, max_tokens=max_tokens)

    # Criação da instrução dentro da função
    instruction = (
        f"Comente sobre o filme {movie_data.get('primaryTitle')} usando as informações fornecidas."
    )

    data_object = {
        "movie_data": movie_data,
        "instruction": instruction
    }

    try:
        conversation = []

        human_message = f"Filme: {movie_data.get('primaryTitle')}"
        system_message = f"Instrução: {instruction}"

        conversation.append(("human", human_message))
        conversation.append(("system", system_message))

        route_prompt = ChatPromptTemplate.from_messages(conversation)

        llm_router = llm.with_structured_output(schema=BlogPostTrivia)
        
        llm_chain = route_prompt | llm_router

        response = llm_decorator(llm_chain, data_object)

        # Verifica se a resposta contém os dados necessários
        if not response:
            raise ValueError("Dados incompletos recebidos do LLM")

        blog_post_trivia = response.dict()  # Acessa todas as informações da postagem

        elapsed_time = time.perf_counter() - start_time  # Fim da medição de tempo
        print(f"Tempo para gerar postagem de blog: {elapsed_time:.5f} segundos")

        return {"ok": True, "data": blog_post_trivia}, 200

    except Exception as error:
        print(f"\nException: {error}\n")
        return {"ok": False, "data": str(error)}, 500

def llm_decorator(func, obj):
    with get_openai_callback() as cb:
        invoked = func.invoke(obj)
        print('\ncallback\n', cb, '\n')
    return invoked 