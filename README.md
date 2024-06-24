# movie-search-backend

Este é um backend para uma aplicação de pesquisa de filmes que utiliza a OpenAI e a API do TMDB para sugerir filmes baseados em uma pesquisa.

## Requisitos
Node.js
npm

## Configuração
Clone o repositório:

`git clone https://github.com/seu-usuario/movie-search-backend.git`

`cd movie-search-backend`

Instale as dependências:

`npm install`

Crie um arquivo .env na raiz do projeto e adicione suas chaves da API:


`OPENAI_API_KEY=your_openai_api_key`
`TMDB_API_KEY=your_tmdb_api_key`

Inicie o servidor:

`node src/server.js`

Envie uma requisição GET para http://localhost:3000/api/search?query=your_movie_query para obter sugestões de filmes.