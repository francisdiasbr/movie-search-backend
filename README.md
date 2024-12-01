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
   - Scripts contendo o processo de ingestão dos dados do IMDB Dataset para o MongoDB.
   - Dados divididos em dois conjuntos principais: 
     - Title Basics (id + metadados dos filmes: ano, título, duração, gêneros, etc)
     - Title Ratings (id + avaliações da comunidade)

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


## 1. Scripts de Ingestão de Dados 

São scripts ETL (Extract, Transform, Load) que processam em batelada os dados do IMDB Dataset para alimentar a base de consulta no MongoDB. Os dados são divididos em duas coleções:

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
  - ⭐ Média de avaliações
  - 📊 Número de votos
 
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

![API Documentation](assets/swagger.png)


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

### 1. Configuração do Ambiente

Crie e ative um ambiente virtual e instale as dependências:

```
# Para o data_ingestion
cd data_ingestion
python -m venv venv # criar ambiente virtual
source venv/bin/activate  # No Windows: venv\Scripts\activate # ativar ambiente virtual
pip install -r requirements.txt # instalar dependências


# Para a API (em outro terminal)
cd api
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```


### 2. Variáveis de Ambiente

Configure as variáveis de ambiente: crie um arquivo .env na raiz do projeto com as variáveis de ambiente necessárias (env.example).



##  Rodando o Projeto

### 1. Ingestão de Dados
```bash
# No diretório data_ingestion/
python ingest.title_basics.py  # Carrega metadados dos filmes
python ingest.title_ratings.py # Carrega avaliações
```

### 2. Subindo a API
```bash
# No diretório api/
python app.py
```
A API estará disponível em `http://localhost:5001`

> 📌 **Nota**: Certifique-se de que a ingestão de dados foi concluída antes de subir a API.


## Tech stack

**Flask**: framework web para a construção da API.

**Flask-RESTX**: Extensão para APIs RESTful com Swagger UI integrado.

**MongoDB**: Banco de dados NoSQL para armazenar as informações dos filmes.

**pandas**: Biblioteca para manipulação e análise de dados.

**pymongo**: Biblioteca para interação com MongoDB.

**OpenAI**: Biblioteca para interação com a API da OpenAI.

**Spotify**: Biblioteca para interação com a API do Spotify.




## Estrutura do Projeto

```
📁 ./
├── 📄 README.md
├── 📁 assets/
    ├── 📄 swagger.png
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
