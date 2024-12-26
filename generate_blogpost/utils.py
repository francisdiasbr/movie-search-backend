from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.callbacks import get_openai_callback
from pydantic import BaseModel, Field
import time
from datetime import datetime
import json

class MovieReview(BaseModel):
    """Modelo para uma resenha de filme"""
    title: str = Field(
        description="Título criativo da resenha",
        min_length=10,
        max_length=100,
        examples=["'Matrix': Uma Revolução Digital que Transcende o Tempo"]
    )
    introduction: str = Field(
        description="Parágrafo introdutório que apresenta o filme e desperta interesse",
        min_length=100,
        examples=["Em 1999, os irmãos Wachowski apresentaram ao mundo uma obra que revolucionaria não apenas o cinema de ficção científica, mas a própria forma de contar histórias..."]
    )
    stars_and_characters: str = Field(
        description="Análise detalhada dos atores e seus personagens",
        min_length=300,
        examples=["Keanu Reeves entrega uma performance memorável como Neo, um programador comum que descobre ser 'O Escolhido'..."]
    )
    historical_context: str = Field(
        description="Contextualização histórica do filme",
        min_length=100,
        examples=["Lançado no final dos anos 90, o filme capturou perfeitamente a ansiedade da era digital nascente..."]
    )
    cultural_importance: str = Field(
        description="Discussão sobre o impacto cultural do filme",
        min_length=100,
        examples=["Matrix redefiniu o gênero de ação e ficção científica, influenciando inúmeras produções subsequentes..."]
    )
    technical_analysis: str = Field(
        description="Análise dos aspectos técnicos e artísticos",
        min_length=100,
        examples=["A revolucionária técnica do 'bullet time' e os efeitos visuais inovadores estabeleceram novos padrões..."]
    )
    conclusion: str = Field(
        description="Conclusão que convida à reflexão",
        min_length=100,
        examples=["Mais que um filme de ação, Matrix nos convida a questionar nossa própria realidade..."]
    )

class SoundtrackInfo(BaseModel):
    """Modelo para informações da trilha sonora"""
    soundtrack: str = Field(
        description="Lista das principais músicas da trilha sonora",
        examples=["1. 'Wake Up' - Rage Against the Machine\n2. 'Rock Is Dead' - Marilyn Manson"]
    )
    video_url: str = Field(
        description="URL do vídeo da trilha sonora principal no YouTube",
        pattern=r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+$",
        examples=["https://youtube.com/watch?v=pFS4zYWxzNA"]
    )

class BilingualReview(BaseModel):
    """Modelo para resenha bilíngue"""
    pt: MovieReview = Field(description="Versão em português da resenha")
    en: MovieReview = Field(description="Versão em inglês da resenha")

def generate_blog_post(api_key, movie_data, model, temperature=0.5, max_tokens=3000):
    start_time = time.perf_counter()
    llm = ChatOpenAI(api_key=api_key, model=model, temperature=temperature, max_tokens=max_tokens)

    try:
        system_prompt = """Você é um crítico de cinema bilíngue especializado.
Sua tarefa é gerar conteúdo seguindo EXATAMENTE a estrutura solicitada.
Forneça respostas detalhadas e bem elaboradas para cada campo."""

        print("\nGerando conteúdo em português...")
        pt_response = llm.with_structured_output(MovieReview).invoke(
            f"""Crie uma resenha detalhada em português do filme '{movie_data.get('primaryTitle')}' seguindo a estrutura fornecida."""
        )

        print("\nTraduzindo para inglês...")
        en_response = llm.with_structured_output(MovieReview).invoke(
            f"""Traduza esta resenha para inglês, mantendo o mesmo estilo e qualidade:
            {json.dumps(pt_response.dict(), ensure_ascii=False, indent=2)}"""
        )

        print("\nObtendo informações da trilha sonora...")
        soundtrack_response = llm.with_structured_output(SoundtrackInfo).invoke(
            f"""Forneça informações sobre a trilha sonora do filme '{movie_data.get('primaryTitle')}'."""
        )

        # Monta o objeto final
        blog_post = {
            "content": {
                "pt": pt_response.dict(),
                "en": en_response.dict()
            },
            "original_movie_soundtrack": soundtrack_response.soundtrack,
            "soundtrack_video_url": soundtrack_response.video_url,
            "created_at": datetime.now().isoformat()
        }

        return {"ok": True, "data": blog_post}, 200

    except Exception as error:
        print(f"\nErro detalhado: {str(error)}")
        return {"ok": False, "data": str(error)}, 500 