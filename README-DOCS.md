# 📚 Documentação do Movie Search Backend

> **Para instruções de instalação e execução, consulte o [README.md](README.md)**

## Visão Geral

Este projeto, construído em Python, é o backend do projeto [Movie-Search](https://github.com/francisdiasbr/movie-search-frontend). Para entender e subir o projeto completo, acesse o repositório do [frontend](https://github.com/francisdiasbr/movie-search-frontend).

> Observação: As resenhas geradas são utilizadas para alimentar o Blog The Movie Search [Blog The Movie Search](https://themoviesearchblog.netlify.app/) [(https://themoviesearchblog.netlify.app/)](https://themoviesearchblog.netlify.app/)

## 🗄️ Banco de Dados

- MongoDB: Banco de dados NoSQL para persistência de dados

## 🔌 Integrações com APIs Externas

- OpenAI: Integração com serviços de IA
- Spotify: Integração com streaming de música
- AWS: Serviços em nuvem da Amazon
- Open Subtitles: Acesso a base de legendas

## 🖥️ Ambiente de Desenvolvimento

- Servidor: execução em ambiente local
- Swagger (documentação da API): http://localhost:5001/docs
- Banco de Dados: MongoDB (em execução em um nível gratuito. 512MB de armazenamento. MongoDB Compass para local + MongoDB Atlas para nuvem)

## Base de dados

A base de dados de filmes é obtida através do [IMDB Dataset](https://www.imdb.com/interfaces/) e salva no MongoDB.
Ela está salva no MongoDB através da database <u>movie-search</u> na coleção <u>moviebasics</u>.

### Movie Basics
É uma coleção de mais de 680.000 registros de filmes, representando todos os filmes existentes no catálogo do IMDB (Internet Movie Database).

- Contém metadados essenciais dos filmes:
  - 🆔 tconst (IMDB ID)
  - 🎬 Título original e alternativo
  - 📅 Ano de lançamento
  - 🎭 Tipo de mídia (filme, série, etc)
  

## Módulos do sistema

Para cada módulo, há um arquivo controller.py que contém a lógica de negócio e um arquivo routes.py que contém as rotas da API.

Cada um dos módulos possui uma coleção própria no banco de dados.

### Favoritos
- Sistema de gerenciamento de filmes favoritos que permite:
  - Adicionar/remover filmes da lista de favoritos
  - Buscar e filtrar filmes favoritos
  - Marcar filmes como assistidos
  - Enriquecimento automático de dados com:
    - Links para download (magnet links)
    - Links para legendas
    - Informações detalhadas do filme (diretor, elenco, país, etc.)
    - Trilha sonora via Spotify
    - Citações e curiosidades do filme
    - Links para Wikipedia
    - Palavras-chave e sinopse
    

### Generate Blogpost: resenhas de filmes geradas por IA

Sistema de geração automática de artigos que permite:

  - Criação de análises críticas usando IA:
    - Conteúdo bilíngue (PT/EN)
    - Título criativo e contextualizado
    - Análise de elenco e personagens
    - Contexto histórico e cultural
    - Análise técnica e artística
    - Informações sobre a trilha sonora
    - Galeria de imagens de cenas do filme
    - Marcação de conteúdo gerado por IA

  - CRUD completo para gerenciamento de resenhas:
    - Busca e filtragem de publicações
    - Criação de novas resenhas autorais;
    - Edição de resenhas existentes;
    - Exclusão de resenhas;
    - Pesquisa por título, autor, palavras-chave, etc.

### Write Review: resenhas autorais

- Sistema de criação manual de resenhas que permite:
  - Interface para escrita de análises:
    - Suporte bilíngue (PT/EN)
    - Editor de texto completo
    - Galeria de imagens do filme
    - Marcação de conteúdo original

  - CRUD completo para gerenciamento de resenhas:
    - Busca e filtragem de publicações
    - Criação de novas resenhas autorais;
    - Edição de resenhas existentes;
    - Exclusão de resenhas;
    - Pesquisa por título, autor, palavras-chave, etc.

### Directors: favorita os diretores

## Documentação da API (Open API / Swagger)
A documentação interativa da API está disponível através do Swagger UI:

- Acesse `/docs` após iniciar o servidor
- Interface interativa para testar endpoints
- Documentação detalhada dos parâmetros e respostas
- Exemplos de uso para cada rota

<details>
<summary><strong>Como Testar Requisições no Swagger UI</strong></summary>

1. Acesse a documentação Swagger em `http://localhost:5000/docs`

2. Localize o endpoint que deseja testar (ex: `/movies/search`)

3. Para testar o endpoint de busca de filmes:
   - Clique no endpoint `/movies/search`
   - Clique no botão "Try it out"
   - No corpo da requisição (Request body), insira um JSON com os parâmetros desejados:
   ```json
   {
     "filters": {
       "startYear": {"$gt": 1990}
     },
     "page": 1,
     "page_size": 10,
     "search_term": "Matrix"
   }
   ```
   - Clique em "Execute" para enviar a requisição
   - Os resultados aparecerão abaixo, incluindo:
     - Código de resposta
     - Headers da resposta
     - Corpo da resposta
     - Curl command equivalente

4. Exemplos de filtros úteis:
   ```json
   // Buscar filmes após 1990
   {"filters": {"startYear": {"$gt": 1990}}}

   // Buscar filmes com termo específico
   {"search_term": "Matrix"}

   // Buscar com paginação
   {"page": 2, "page_size": 20}
   ```

</details>
