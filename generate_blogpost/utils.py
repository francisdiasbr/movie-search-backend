from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.callbacks import get_openai_callback
from pydantic import BaseModel, Field
import time
from datetime import datetime
import json
from spotify.controller import get_album_by_movie_title


class MovieReview(BaseModel):
    """Modelo para uma resenha de filme"""

    title: str = Field(
        description="Título do filme em formato de cabeçalho, seguido por uma linha com o ano, país e diretor entre parênteses e separados por bullets",
        min_length=10,
        max_length=110,
        examples=["The Way We Were\n\n(1973) • Estados Unidos • Sydney Pollack"],
    )
    introduction: str = Field(
        description="Parágrafo introdutório pessoal que apresenta o filme de forma íntima e conversacional. Compartilhe como você descobriu o filme e sua primeira impressão",
        min_length=100,
        examples=[
            "Tem filmes que a gente demora anos para assistir e depois fica se perguntando 'por que esperei tanto?'. The Way We Were é um desses. Vi numa sexta à noite, meio por acaso, e saí de lá com aquela sensação de quem acabou de viver algo especial."
        ],
    )
    plot_summary: str = Field(
        description="Breve resumo da história de forma pessoal, focando no que te tocou ou chamou atenção, sem spoilers",
        min_length=100,
        examples=[
            "A história é simples na superfície: Katie (Barbra Streisand) e Hubbell (Robert Redford) se conhecem na faculdade, ela toda engajada politicamente, ele meio 'tanto faz' com a vida. Eles se reencontram anos depois e vivem um amor intenso, mas complicado. O que poderia ser só mais um romance clássico vira algo muito mais profundo sobre como às vezes amamos pessoas que são o nosso oposto completo."
        ],
    )
    acting_analysis: str = Field(
        description="Análise pessoal das atuações, focando em como você se conectou com os personagens e quais momentos mais te impactaram",
        min_length=300,
        examples=[
            "A Barbra Streisand nesse filme é uma força da natureza. Katie é daquelas personagens que poderiam facilmente virar caricatura - a militante chata, sabe? Mas a Streisand faz você entender cada frustração, cada paixão dessa mulher. Tem uma cena onde ela está tentando não chorar que me quebrou completamente.\n\nO Robert Redford... bom, demorei para me conectar com ele. No começo achei o Hubbell meio sem graça, mas foi proposital. Ele é aquele cara bonito e talentoso que a vida sempre foi fácil, então nunca precisou lutar por nada. O contraste com a Katie é perfeito e doloroso ao mesmo tempo."
        ],
    )
    personal_impressions: str = Field(
        description="Seção sobre o que mais te marcou no filme, incluindo aspectos técnicos, emocionais e culturais de forma pessoal",
        min_length=300,
        examples=[
            "Esse filme é sobre tempo - como ele muda as pessoas, como ele pode curar ou destruir relacionamentos. Tem uma melancolia linda em como mostra que nem todo amor é para sempre, e tudo bem. Às vezes amar alguém é também saber quando deixar ir.\n\nA trilha sonora é inesquecível (quem nunca cantarolou 'The Way We Were'?), mas o que mais me impressionou foi como o filme não tem pressa. Ele deixa os momentos respirarem, principalmente os silêncios entre Katie e Hubbell."
        ],
    )
    recommendation: str = Field(
        description="Conclusão pessoal e recomendação sincera sobre quem deve assistir e por quê",
        min_length=100,
        examples=[
            "Se você curte romances que não te entregam um final embrulhadinho para presente, vai amar. É um filme que fica na cabeça por dias, daqueles que você quer discutir com alguém depois.\n\nNão é um filme 'fácil' - vai te fazer pensar sobre seus próprios relacionamentos, sobre as escolhas que fazemos. Mas é lindo, honesto e tem duas atuações que merecem ser vistas.\n\nRecomendo para uma noite que você tem tempo de sentir. Tenha lenço por perto."
        ],
    )


class SoundtrackInfo(BaseModel):
    """Modelo para informações da trilha sonora"""

    soundtrack: str = Field(
        description="Lista das principais músicas da trilha sonora",
        examples=[
            "1. 'Wake Up' - Rage Against the Machine\n2. 'Rock Is Dead' - Marilyn Manson"
        ],
    )
    video_url: str = Field(
        description="URL do vídeo da trilha sonora principal no YouTube",
        pattern=r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+$",
        examples=["https://youtube.com/watch?v=pFS4zYWxzNA"],
    )
    spotify_album_url: str = Field(
        description="URL do álbum da trilha sonora no Spotify",
        pattern=r"^https?://(?:open\.)?spotify\.com/album/[\w-]+$",
        examples=["https://open.spotify.com/album/4fEGGDaDNDLvXPylhbJdBy"],
    )


class BilingualReview(BaseModel):
    """Modelo para resenha bilíngue"""

    pt: MovieReview = Field(description="Versão em português da resenha")
    en: MovieReview = Field(description="Versão em inglês da resenha")


def generate_blog_post(api_key, movie_data, model, temperature=0.6, max_tokens=3000):
    start_time = time.perf_counter()
    llm = ChatOpenAI(
        api_key=api_key, model=model, temperature=temperature, max_tokens=max_tokens
    )

    try:
        system_prompt = """Você é um crítico de cinema apaixonado e pessoal, que escreve resenhas como se estivesse conversando com um amigo.
Sua tarefa é criar resenhas que fluam naturalmente, usando uma linguagem íntima e conversacional.
Evite estruturas rígidas ou formais - escreva como se estivesse compartilhando suas impressões em um blog pessoal.
Use markdown para formatar o texto, com títulos em # e subtítulos em ##.
Inclua quebras de linha (\\n\\n) entre parágrafos para melhor legibilidade.
Seja honesto e autêntico em suas opiniões, compartilhando suas emoções e conexões pessoais com o filme.
Use expressões coloquiais e uma linguagem mais próxima do dia a dia.
Mantenha um tom íntimo e reflexivo, como se estivesse tendo uma conversa descontraída sobre cinema."""

        print("\nGerando conteúdo em português...")
        pt_response = llm.with_structured_output(MovieReview).invoke(
            f"""Crie uma resenha detalhada em português do filme '{movie_data.get('primaryTitle')}' seguindo a estrutura fornecida."""
        )

        print("\nTraduzindo para inglês...")
        en_response = llm.with_structured_output(MovieReview).invoke(
            f"""Traduza esta resenha para inglês, mantendo o mesmo estilo e qualidade:
            {json.dumps(pt_response.dict(), ensure_ascii=False, indent=2)}"""
        )

        # Obtém a URL do álbum no Spotify
        print("\nBuscando álbum no Spotify...")
        spotify_album_url = get_album_by_movie_title(movie_data.get('primaryTitle'))
        print(f"URL do álbum no Spotify: {spotify_album_url}")

        print("\nObtendo informações da trilha sonora...")
        soundtrack_response = llm.with_structured_output(SoundtrackInfo).invoke(
            f"""Forneça informações sobre a trilha sonora do filme '{movie_data.get('primaryTitle')}'."""
        )

        # Monta o objeto final com a nova estrutura
        blog_post = {
            "content": {
                "pt": {
                    "title": pt_response.title,
                    "introduction": pt_response.introduction,
                    "plot_summary": pt_response.plot_summary,
                    "acting_analysis": pt_response.acting_analysis,
                    "personal_impressions": pt_response.personal_impressions,
                    "recommendation": pt_response.recommendation
                },
                "en": {
                    "title": en_response.title,
                    "introduction": en_response.introduction,
                    "plot_summary": en_response.plot_summary,
                    "acting_analysis": en_response.acting_analysis,
                    "personal_impressions": en_response.personal_impressions,
                    "recommendation": en_response.recommendation
                }
            },
            "original_movie_soundtrack": soundtrack_response.soundtrack,
            "soundtrack_video_url": soundtrack_response.video_url,
            "spotify_album_url": spotify_album_url if spotify_album_url != "No album found" else None,
            "created_at": datetime.now().isoformat(),
        }

        print(f"\nBlog post gerado com sucesso. Spotify URL: {blog_post.get('spotify_album_url')}")
        print(f"Objeto completo do blog post: {json.dumps(blog_post, ensure_ascii=False, indent=2)}")

        return {"ok": True, "data": blog_post}, 200

    except Exception as error:
        print(f"\nErro detalhado: {str(error)}")
        return {"ok": False, "data": str(error)}, 500
