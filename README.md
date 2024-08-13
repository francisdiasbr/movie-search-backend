# 🎬 movie-search-backend

Este projeto, construído em Python, está dividido em:

### 1. Scripts de Ingestão de Dados em Bulk
Scripts para carregar dados em formato TSV no MongoDB:

- **Title Ratings**: Avaliações de filmes (averageRating e numVotes).

- **Title Basics**: Metadados dos filmes.


### 2. Rotas de Consulta
**Title Ratings:**

`GET /ratings/:id` - Retorna a avaliação de um filme específico pelo ID.

`GET /search` - Permite buscar avaliações de filmes com base em critérios específicos.


---


### Tech stack
**Flask**: microframework para desenvolvimento web.

**MongoDB**: Banco de dados NoSQL para armazenar as informações dos filmes.

**pandas**: Biblioteca para manipulação e análise de dados.

**pymongo**: Biblioteca para interação com MongoDB.


---


### Instalação e Configuração

1. Clone o repositório:

```
git clone https://github.com/seu-usuario/movie-search-backend.git
cd movie-search-backend
```

2. Crie e ative um ambiente virtual

```
python3 -m venv venv
source venv/bin/activate  # No Windows use `venv\Scripts\activate`
```


3. Instale as dependências
```
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente: crie um arquivo .env na raiz do projeto e adicione as seguintes variáveis:

```
FLASK_DEBUG=True

MONGODB_CONNECTION_STRING="mongodb://127.0.0.1:27017/"
MONGODB_DATABASE="movie-search"

COLLECTION_NAME_TITLE_BASICS="titlebasics"
COLLECTION_NAME_TITLE_RATINGS="titleratings"

TITLE_BASICS_FILE_PATH="path_do_arquivo_titlebasics_na_máquina_local"
TITLE_RATINGS_FILE_PATH="path_do_arquivo_titleratings_na_máquina_local"

```

### Rodando o projeto

1. Inicie a aplicação Flask

```
python app.py
```

A aplicação estará disponível em `http://127.0.0.1:5000`
