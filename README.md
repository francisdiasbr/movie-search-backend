# 🎬 movie-search-backend
 
## 📑 Índice
- [Visão Geral](#-movie-search-backend)
  - [Scripts de Ingestão de Dados](#1-ingestão-de-dados-em-bulk)
  - [API](#2-rotas-de-consulta)
  - [Documentação da API (Open API / Swagger)](#3-documentação-da-api-swagger)
- [Como Testar](#como-testar-requisições-no-swagger-ui)
- [Instalação e Configuração](#instalação-e-configuração)
  - [Configuração do Ambiente](#1-crie-e-ative-um-ambiente-virtual-e-instale-as-dependências)
  - [Variáveis de Ambiente](#2-configure-as-variáveis-de-ambiente)
- [Rodando o Projeto](#rodando-o-projeto)
- [Tech Stack](#tech-stack)
- [Estrutura do Projeto](#estrutura-do-projeto)

---

## Visão Geral

Este projeto, construído em Python, [é o backend do projeto MOVIE-SEARCH](https://github.com/francisdiasbr/movie-search-frontend). Está dividido em duas partes/etapas:

1. **Ingestão de Dados**
   - Scripts ETL para processar dados do IMDB Dataset
   - Transformação de arquivos TSV para MongoDB
   - Processamento de metadados de filmes e avaliações
   - Otimização dos dados para consultas eficientes

2. **Módulo API**
   - API RESTful para servir dados de filmes e avaliações
   - Endpoints para busca e filtragem avançada
   - Integração com serviços externos (Spotify, OpenAI)
   - Recursos para:
     - Busca de filmes por diversos critérios
     - Gerenciamento de favoritos
     - Geração de reviews usando IA
     - Recomendações personalizadas
     - Integração com playlists do Spotify

O objetivo é fornecer uma base robusta e escalável para o frontend, permitindo uma experiência rica de busca e descoberta de filmes, enriquecida com recursos de IA e integração com serviços de música.

## 1. Scripts de Ingestão de Dados 

São scripts ETL (Extract, Transform, Load) que processam em batelada os dados do IMDB Dataset para alimentar a base de consulta no MongoDB. Os dados são divididos em dois conjuntos principais:

### Title Basics
- Metadados essenciais dos filmes:
  - 🎬 Título original e alternativo
  - 📅 Ano de lançamento
  - ⏱️ Duração
  - 🎭 Gêneros
  - 📝 Descrição
  - 🎯 Tipo de mídia (filme, série, etc)

### Title Ratings
- Dados de avaliação da comunidade IMDB:
  - ⭐ Média de avaliações (averageRating)
  - 📊 Número de votos (numVotes)
  - 📈 Dados atualizados periodicamente
 
### Processo de Ingestão
1. **Extração**: Leitura dos arquivos TSV do IMDB
2. **Transformação**: 
   - Limpeza e formatação dos dados
   - Validação de campos
   - Estruturação para otimizar consultas
3. **Carga**: 
   - Inserção otimizada no MongoDB
   - Criação de índices para performance
   - Validação de integridade

> 📌 **Nota**: Os scripts podem ser executados independentemente, mas recomenda-se primeiro carregar os dados básicos (Title Basics) seguido das avaliações (Title Ratings).




## 2. API

![Screenshot 2024-11-30 at 20 12 49](https://github.com/user-attachments/assets/9558e339-8ed0-4920-9501-6c35c66c2f3b)


## 3. Documentação da API (Open API / Swagger)
A documentação interativa da API está disponível através do Swagger UI:

- Acesse `/docs` após iniciar o servidor
- Interface interativa para testar endpoints
- Documentação detalhada dos parâmetros e respostas
- Exemplos de uso para cada rota


### Como Testar Requisições no Swagger UI

1. Acesse a documentação Swagger em `http://localhost:5001/docs`

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

## Instalação e Configuração


1. Crie e ative um ambiente virtual e instale as dependências:
```
# Para o data_ingestion
cd data_ingestion
python -m venv venv # criar ambiente virtual
source venv/bin/activate  # No Windows: venv\Scripts\activate # ativar ambiente virtual
pip install -r requirements.txt # instalar dependências
python ingest.title_basics.py # executar o script de ingestão de dados
python ingest.title_basics.py # executar o script de ingestão de metadados de filmes
python ingest.title_ratings.py # executar o script de ingestão de dados de avaliações

# Para a API (em outro terminal)
cd api
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```


2. Configure as variáveis de ambiente: crie um arquivo .env na raiz do projeto e adicione as seguintes variáveis:

```
FLASK_DEBUG=True

MONGODB_CONNECTION_STRING="mongodb://127.0.0.1:27017/"
MONGODB_DATABASE="movie-search"

COLLECTION_NAME_TITLE_BASICS="titlebasics"
COLLECTION_NAME_TITLE_RATINGS="titleratings"

TITLE_BASICS_FILE_PATH="path_do_arquivo_titlebasics_na_máquina_local"
TITLE_RATINGS_FILE_PATH="path_do_arquivo_titleratings_na_máquina_local"

```

## Rodando o projeto

1. Inicie a aplicação Flask

```
python app.py
```

A aplicação estará disponível em `http://127.0.0.1:5001`


## Tech stack
**Flask**: microframework para desenvolvimento web.

**MongoDB**: Banco de dados NoSQL para armazenar as informações dos filmes.

**pandas**: Biblioteca para manipulação e análise de dados.

**pymongo**: Biblioteca para interação com MongoDB.



## Estrutura do Projeto

```
📁 ./
├── 📄 README.md
├── 📁 api/
│   ├── 📄 app.py
│   ├── 📄 config.py
│   ├── 📁 favorites/
│   │   ├── 📄 controller.py
│   │   ├── 📄 routes.py
│   │   └── 📄 scrapper.py
│   ├── 📁 generate_review/
│   │   ├── 📄 controller.py
│   │   └── 📄 routes.py
│   ├── 📁 movies/
│   │   ├── 📄 controller.py
│   │   └── 📄 routes.py
│   ├── 📁 ratings/
│   │   ├── 📄 controller.py
│   │   └── 📄 routes.py
│   ├── 📄 requirements.txt
│   ├── 📁 spotify/
│   │   └── 📄 controller.py
│   ├── 📁 suggestion/
│   │   ├── 📄 controller.py
│   │   └── 📄 routes.py
│   ├── 📄 utils.py
│   └── 📁 write_review/
│       ├── 📄 controller.py
│       └── 📄 routes.py
└── 📁 data_ingestion/
    ├── 📄 ingest.title_basics.py
    ├── 📄 ingest.title_ratings.py
    └── 📄 requirements.txt

```
