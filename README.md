# 🎬 movie-search-backend

Este projeto em Python oferece funcionalidades para busca e avaliação de filmes, com dados carregados em um banco de dados MongoDB.

## Índice
- [Visão Geral](#visão-geral)
- [Features](#features)
- [Rotas da API](#rotas-da-api)
- [Instalação e Configuração](#instalação-e-configuração)
  - [Configuração para a API](#configuração-para-a-api)
  - [Configuração para os Scripts de Ingestão](#configuração-para-os-scripts-de-ingestão)

- [Tech Stack](#tech-stack)

## Visão Geral

O projeto está dividido em duas partes principais, cada uma com seu próprio ambiente virtual (virtualenv):

1. Scripts de Ingestão de Dados em Bulk: Scripts responsáveis pelo carregamento de dados em formato TSV no MongoDB.

2. API de Consulta: API desenvolvida com Flask para consultar informações dos filmes e avaliações.

OBS: É necessário ter os dados dos filmes em formato TSV para executar os scripts de ingestão, possibilitando assim o seu consumo.

# Features


## Rotas da API

### Movies (movies info/metadata)

`POST /movies/search` - Permite buscar filmes com base em critérios específicos. A response inclui metadados dos filmes: tconst, primaryTitle & startYear.


### Ratings (movie rating)

`POST /ratings/search` - Permite buscar avaliações de filmes com base em critérios específicos. A response inclui tconst, averageRating e numVotes.

`GET /ratings/:id` - Retorna a avaliação de um filme específico pelo ID.

`GET /movie-with-rating/:id` - Retorna um filme com sua avaliação (rating) através do ID.


### Favorites

`POST /favorited-movies/search` Filtra os filmes favoritados por termo de busca

`POST /movie/:id` Favorita um filme

`GET /movie/:id` Recupera um filme favoritado

`PUT /movie/:id` Edita um filme

`DELETE /movie/:id` Remove um filme


### Generate review

`POST /favorited-movies/:id/generate-review` Gera uma avaliação para um filme favoritado

`GET /favorited-movies/:id/generate-review` Recupera a review gerada de um filme favoritado

`POST /favorited-movies/generate-review/search` Filtra as a reviews geradas de filmes favoritados por termo de busca

TODO `PUT /favorited-movies/:id/generate-review` Edita a review gerada de um filme favoritado


### Write review

`POST /favorited-movies/write-review/search` Filtra as reviews escritas de filmes favoritados por termo de busca

`POST /favorited-movies/:id/write-review` Escreve uma review para um filme favoritado

`GET /favorited-movies/:id/write-review` Recupera a review escrita de um filme favoritado

`PUT /favorited-movies/:id/write-review` Edita a review escrita de um filme favoritado



## Instalação e Configuração

1. Clone o repositório:

```
git clone https://github.com/seu-usuario/movie-search-backend.git
cd movie-search-backend
```

Passo 2: Configurar as Virtualenvs
Para separar as responsabilidades e garantir um ambiente independente para cada parte do projeto, vamos configurar duas virtualenvs.

### Configuração para a API
1. Navegue até a pasta api:

```
cd api
```
2. Crie e ative o ambiente virtual para a API:

```
  python3 -m venv venv
  source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Instale as dependências da API:

```
  pip install -r requirements.txt
```

4. Inicie a aplicação 

```
python app.py
```

### Configuração para os Scripts de Ingestão
1. Navegue até a pasta scripts:

```
  cd ../scripts
```

2. Crie e ative o ambiente virtual para os scripts:

```
  python3 -m venv venv
  source venv/bin/activate  # Windows: `venv\Scripts\activate`
```

3. Instale as dependências dos scripts de ingestão:

```
  pip install -r requirements.txt
```

2. Inicie a aplicação 

```
python app.py
```


Passo 3: Configurar Variáveis de Ambiente

Na raiz do projeto, crie um arquivo .env e adicione as seguintes variáveis:

```
FLASK_DEBUG=True

MONGODB_CONNECTION_STRING="mongodb://127.0.0.1:27017/"
MONGODB_DATABASE="movie-search"

COLLECTION_NAME_TITLE_BASICS="titlebasics"
COLLECTION_NAME_TITLE_RATINGS="titleratings"

TITLE_BASICS_FILE_PATH="path_do_arquivo_titlebasics_na_máquina_local"
TITLE_RATINGS_FILE_PATH="path_do_arquivo_titleratings_na_máquina_local"

```

## Consumo

É necessário ter os dados dos filmes em formato TSV para executar os scripts de ingestão, possibilitando assim o seu consumo.

### 🗄️ Scripts de Ingestão de Dados em Bulk
Os scripts de ingestão estão configurados para carregar dados de arquivos TSV para as coleções titlebasics e titleratings no MongoDB.

1. Navegue até a pasta scripts e ative a virtualenv:

```
cd scripts
source venv/bin/activate
```

2. Execute os scripts de ingestão conforme necessário:

```
  python import_title_basics.py  # Importa metadados dos filmes
  python import_title_ratings.py  # Importa avaliações dos filmes
```


### 🌐 API de Consulta
A API permite consultar dados de filmes e avaliações, incluindo rotas para busca e filtros específicos.

1. Navegue até a pasta api e ative a virtualenv:

```
cd ../api
source venv/bin/activate
```

2. Inicie a aplicação Flask

```
python app.py
```

A aplicação estará disponível em `http://127.0.0.1:5000`

OBS: Para testar as rotas da API, utilize o Postman ou Insomnia


## Tech Stack

- Flask: Framework web para construção da API.
- MongoDB: Banco de dados NoSQL para armazenar os dados dos filmes.
- pandas: Biblioteca para manipulação e análise de dados.
- pymongo: Biblioteca para conexão e manipulação de dados no MongoDB.