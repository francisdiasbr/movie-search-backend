# Favoritos

Módulo: `favorites/` (`routes.py`, `controller.py`, `scrapper.py`, `translation.py`, `external_requests.py`). Coleção: `favoritelist`.

## O que faz

Mantém a lista de filmes favoritos. Quem usa informa apenas o `tconst` do filme. A API busca no IMDB o título, o ano, a direção, o elenco, a sinopse, curiosidades, uma citação, as palavras-chave, o pôster e uma imagem larga para banner. Também procura um magnet link, uma legenda e a página da Wikipedia, e gera uma versão em português dos textos. Depois disso é possível ler o filme em inglês ou em português, marcar como assistido, anexar referências e trilha sonora, e buscar na lista.

## Rotas

Prefixo: `/api/favorites`.

| Método | Caminho | O que faz |
|---|---|---|
| `POST` | `/search` | Lista os favoritos, com filtros, termo de busca e paginação. |
| `GET` | `/<tconst>` | Devolve um favorito. |
| `POST` | `/<tconst>` | Adiciona um filme aos favoritos. |
| `PUT` | `/<tconst>` | Edita os campos editáveis de um favorito. |
| `DELETE` | `/<tconst>` | Remove um favorito. |
| `POST` | `/<tconst>/translate` | Gera ou refaz a versão em português de um favorito. |

### `POST /favorites/<tconst>`

Não recebe corpo.

| Status | Quando | Corpo |
|---|---|---|
| `201` | Filme adicionado. | `{"data": {...}}` com o documento em inglês e `"lang": "en"`. |
| `404` | O scraper não encontrou o título na página do IMDB. | `{"message": "Título do filme não encontrado no IMDB"}` |
| `409` | Já existe um favorito com esse `tconst`. | `{"message": "Movie already listed"}` |
| `503` | O WAF do IMDB bloqueou todas as tentativas de uma página, ou o MongoDB está indisponível. | `{"message": "IMDB bloqueou o acesso. Renove a sessão com ./verify_imdb.sh"}` |

Exemplo de resposta `201`:

```json
{
  "data": {
    "_id": "665f1c2e9b1e8a0012345678",
    "primaryTitle": "The 400 Blows",
    "tconst": "tt0053198",
    "imdb_url": "https://www.imdb.com/title/tt0053198/",
    "created_at": "2026-11-10T18:49:43.076953",
    "references": [],
    "backdrop_url": "https://m.media-amazon.com/images/M/..._V1_UX1600_.jpg",
    "country": "France",
    "director": "François Truffaut",
    "genres": ["Coming-of-Age", "Drama"],
    "plot": "A young boy, left without attention, delves into a life of petty crime.",
    "plot_keywords": ["french new wave", "childhood"],
    "poster_url": "https://m.media-amazon.com/images/M/....jpg",
    "quote": "Antoine Doinel : ...",
    "stars": ["Jean-Pierre Léaud", "Albert Rémy", "Claire Maurier"],
    "startYear": 1959,
    "title_pt": "Os Incompreendidos",
    "trivia": "...\n\n...",
    "writers": ["François Truffaut", "Marcel Moussy"],
    "wiki": "https://en.wikipedia.org/wiki/The_400_Blows",
    "lang": "en"
  }
}
```

Os campos que não resolveram ficam fora do documento. No exemplo, `magnet_link` e `subtitle_url` não aparecem porque as buscas não devolveram nada.

Passo a passo (`favorite_movie`):

1. Procura um documento com o mesmo `tconst`. Se existe, responde `409`.
2. Chama `get_movie_title(tconst)`, que carrega a página principal do título no IMDB. Sem título, responde `404`.
3. Monta o documento base: `primaryTitle`, `tconst`, `imdb_url`, `created_at` (`datetime.now().isoformat()`) e `references` como lista vazia.
4. Chama `collect_movie_data(tconst, title)`, que executa em sequência cada função do dicionário `SCRAPERS` mais a busca da Wikipedia. Só entram no documento os valores diferentes de `None` e de string vazia.
5. Chama `translate_movie(movie)`. Se a tradução vier, grava em `translations.pt`.
6. Insere no Mongo com `db.insert`.
7. Responde com `localize(movie, "en")`, que remove o mapa `translations` e acrescenta `"lang": "en"`.

Regras e casos de borda:

- Uma falha num scraper isolado (qualquer exceção que não seja `IMDBUnavailable`) é registrada com `logger.warning` e o campo fica de fora. O cadastro continua.
- `IMDBUnavailable` interrompe a coleta. O cache de páginas é limpo e a exceção sobe até o handler de `503`. Nada é gravado.
- O cache de páginas é limpo ao final da coleta, com sucesso ou não.
- Uma tradução que falha não impede o cadastro. O favorito fica sem `translations` até uma chamada a `POST /<tconst>/translate`.
- A checagem de duplicidade é um `find_one` seguido de `insert_one`. O código não cria índice único em `tconst`.
- Uma página do IMDB que não carrega por outro motivo que não o WAF (tempo esgotado, erro de rede, erro do navegador) faz `fetch_soup` devolver `None`. Se isso acontecer na busca do título, a resposta é `404`, e não `503`.

### `GET /favorites/<tconst>`

| Parâmetro de query | Valores | Padrão |
|---|---|---|
| `lang` | `en` ou `pt` | `en` |

| Status | Quando | Corpo |
|---|---|---|
| `200` | Favorito encontrado. | `{"data": {...}}` com o campo `lang` indicando o idioma entregue. |
| `400` | `lang` diferente de `en` e `pt`. | `{"message": "Idioma inválido, use um de: en, pt"}` |
| `404` | Não há favorito com esse `tconst`. | `{"message": "Movie not found"}` |

Passo a passo (`get_favorited_movie`):

1. Valida `lang` contra `LANGUAGES = ("en", "pt")`.
2. Busca o documento e serializa.
3. Para cada campo de `BACKFILLS` (`backdrop_url` e `title_pt`) ausente no documento, chama a consulta correspondente no GraphQL do IMDB e grava o resultado.
4. Aplica `localize(movie, lang)`.

Regras e casos de borda:

- **Preenchimento tardio.** `backdrop_url` e `title_pt` foram acrescentados depois que os primeiros favoritos já existiam. Na primeira leitura de um favorito antigo, a API consulta o IMDB e grava o valor. Quando o IMDB não tem o dado, grava string vazia, para não repetir a consulta. Quando a consulta falha com `IMDBSearchError`, nada é gravado e a próxima leitura tenta de novo. Por causa disso, um `GET` pode escrever no banco.
- **Idioma.** Com `lang=pt`, os campos de `translations.pt` substituem os campos em inglês. Campos sem tradução continuam em inglês. O mapa `translations` nunca aparece na resposta.
- **Campo `lang` da resposta.** Diz o idioma realmente entregue. Se o cliente pede `pt` e o favorito não tem tradução, a resposta vem em inglês com `"lang": "en"`. O cliente pode usar isso para decidir chamar `/translate`.

### `PUT /favorites/<tconst>`

Corpo JSON obrigatório, validado pelo modelo `FavoriteMovie`. Nenhum campo é obrigatório.

Campos que o controller aceita (`EDITABLE_FIELDS`):

| Campo | Tipo no modelo |
|---|---|
| `magnet_link` | string |
| `references` | lista de strings |
| `soundtrack` | string |
| `watched` | booleano |
| `wiki` | string |

O modelo Swagger lista outros campos (`plot`, `director`, `genres` etc.). Eles passam pela validação de tipo, mas o controller os descarta com `pick`.

| Status | Quando | Corpo |
|---|---|---|
| `200` | Favorito atualizado, ou corpo sem nenhum campo editável. | `{"data": {...}}` com o documento completo. |
| `400` | Tipo errado num campo do modelo, ou JSON malformado. | Erro de validação. |
| `404` | Não há favorito com esse `tconst`. | `{"message": "Movie tt0053198 not found"}` |
| `415` | Sem corpo JSON. | |

Exemplo de requisição:

```json
{ "watched": true, "soundtrack": "https://open.spotify.com/album/..." }
```

Regras e casos de borda:

- Só os campos presentes no corpo são alterados. Os demais ficam como estão.
- Um campo enviado como `null` é ignorado (`db.update` descarta `None`). Valores falsos que não são `None`, como `false` e `[]`, são gravados.
- Um corpo `{}` é uma edição válida e idempotente: a resposta é `200` com o documento atual.
- A resposta traz o documento como está no banco, inclusive o mapa `translations`, e sem o campo `lang`. É diferente do `GET`, que aplica `localize`.
- **Espelhamento no blogpost.** Quando o corpo traz `references` ou `soundtrack`, `sync_blogpost` procura na coleção `blogposts` um documento com o mesmo `tconst`. Se existe, grava `references` em `references` e `soundtrack` em `spotify_album_url`. Se não existe, nada é criado. Uma falha nesse espelhamento é registrada no log e não muda a resposta, que continua `200`.

### `DELETE /favorites/<tconst>`

| Status | Quando | Corpo |
|---|---|---|
| `200` | Favorito removido. | `{"data": "Movie tt0053198 deleted"}` |
| `404` | Não há favorito com esse `tconst`. | `{"message": "Movie tt0053198 not found"}` |

A remoção apaga só o documento do favorito. A resenha (`authoralreviewslist`), as imagens (`main-images` e S3) e o blogpost do mesmo filme não são tocados.

### `POST /favorites/<tconst>/translate`

Não recebe corpo. Serve para favoritos criados antes de a tradução existir, ou cuja tradução falhou no cadastro. Chamar de novo refaz a tradução.

| Status | Quando | Corpo |
|---|---|---|
| `200` | Tradução gerada e gravada. | `{"data": {...}}` em português, com `"lang": "pt"`. |
| `404` | Não há favorito com esse `tconst`. | `{"message": "Movie not found"}` |
| `502` | O tradutor falhou, ou o favorito não tem nenhum campo traduzível preenchido. | `{"message": "Falha ao traduzir o filme"}` |

### `POST /favorites/search`

Corpo JSON obrigatório (pode ser `{}`), validado pelo modelo `FavoriteSearch`.

| Campo | Tipo | Padrão aplicado pela rota | Significado |
|---|---|---|---|
| `filters` | objeto | `{}` | Filtro do MongoDB aplicado como veio, depois de `sanitize_filters`. |
| `page` | inteiro | `1` | Página, começando em 1. |
| `page_size` | inteiro | `0` | Itens por página. `0` desliga a paginação e devolve tudo. |
| `search_term` | string | `""` | Termo procurado no `tconst` (igualdade), no título e no diretor (trecho, sem diferenciar maiúsculas). |

O modelo Swagger declara `default=10` para `page_size`. A rota usa `0` quando o campo não vem.

Exemplo de requisição:

```json
{ "filters": { "country": "France" }, "search_term": "truffaut", "page": 1, "page_size": 20 }
```

Exemplo de resposta `200`:

```json
{
  "total_documents": 2,
  "entries": [
    {
      "_id": "665f1c2e9b1e8a0012345678",
      "poster_url": "https://m.media-amazon.com/images/M/....jpg",
      "primaryTitle": "The 400 Blows",
      "startYear": 1959,
      "tconst": "tt0053198",
      "watched": true
    }
  ],
  "countries": ["France", "Italy", "Japan"],
  "years": [1959, 1960, 1962]
}
```

Passo a passo (`get_favorited_movies`):

1. Copia `filters`, para não alterar o corpo da requisição.
2. Define o termo de busca nesta ordem: o campo `search_term` do corpo; se vazio, `filters.search_term` (que é retirado de `filters`); se vazio, `filters.tconst` quando é uma string.
3. Com um termo, acrescenta a `filters` um `$or` com três condições: `tconst` igual ao termo, `primaryTitle` contendo o termo e `director` contendo o termo.
4. Chama `db.search` com a projeção `LIST_PROJECTION` e a ordenação padrão, `_id` decrescente (os mais recentes primeiro).
5. Acrescenta `countries` e `years`.

Regras e casos de borda:

- A listagem devolve só `_id`, `poster_url`, `primaryTitle`, `startYear`, `tconst` e `watched`. Os textos longos ficam para o `GET /<tconst>`.
- `total_documents` conta todos os documentos que casam com o filtro, independentemente da página.
- `countries` e `years` são calculados sobre a coleção inteira, e não sobre o resultado filtrado. Servem para o cliente montar as opções de filtro.
- `years` só inclui valores que são dígitos. Um `startYear` gravado como texto não numérico fica de fora.
- Um filtro `tconst` com operador, como `{"tconst": {"$in": [...]}}`, não vira termo de busca e é aplicado como filtro normal.
- `sanitize_filters` garante que todo valor de `$regex` seja string, inclusive dentro de `$or`. Os demais operadores passam como vieram.
- O comportamento com `page` menor que 1 e `page_size` maior que zero não foi verificado contra um MongoDB real. O código calcula `skip((page - 1) * page_size)`, que fica negativo.

## Coleta de dados: o dicionário `SCRAPERS`

Cada campo coletado tem uma entrada em `SCRAPERS`, com a função que o preenche. Acrescentar um campo ao favorito significa acrescentar uma entrada.

| Campo | Função | Fonte |
|---|---|---|
| `backdrop_url` | `find_backdrop` | GraphQL do IMDB |
| `country` | `get_movie_country` | Página principal do IMDB |
| `director` | `get_director` | Página principal do IMDB |
| `genres` | `get_movie_genres` | Página principal do IMDB |
| `magnet_link` | `get_magnet_link` | RapidAPI |
| `plot` | `get_movie_sm_plot` | Página principal do IMDB |
| `plot_keywords` | `get_movie_plot_keywords` | Página `keywords` do IMDB |
| `poster_url` | `get_movie_poster` | Página principal do IMDB |
| `quote` | `get_movie_quote` | Página `quotes` do IMDB |
| `stars` | `get_movie_principal_stars` | Página principal do IMDB |
| `startYear` | `get_movie_year` | Página principal do IMDB |
| `subtitle_url` | `get_subtitle_url` | OpenSubtitles |
| `title_pt` | `find_brazilian_title` | GraphQL do IMDB |
| `trivia` | `get_movie_trivia` | Página `trivia` do IMDB |
| `writers` | `get_writers` | Página principal do IMDB |
| `wiki` | `get_wikipedia_url` | Wikipedia (recebe o título, e não o `tconst`) |

Os seletores de cada scraper e o comportamento de cada fonte estão em [integracoes.md](../integracoes.md).

## Tradução

`favorites/translation.py` traduz cinco campos (`TRANSLATED_FIELDS`): `plot`, `trivia`, `quote`, `genres` e `plot_keywords`. Só os campos preenchidos entram.

| Tipo de valor | Como é traduzido |
|---|---|
| Lista (`genres`, `plot_keywords`) | Item por item, com o resultado em minúsculas. |
| `quote` | A expressão regular `QUOTE_LINE` separa `Personagem : fala`. Só as falas são traduzidas, e os nomes dos personagens ficam como estão. Se a expressão não casa, o texto inteiro é traduzido. |
| Demais textos (`plot`, `trivia`) | Linha por linha. As linhas em branco são mantidas, o que preserva a separação entre as curiosidades. |

`translate_movie` devolve `None` em dois casos: quando não há nenhum campo a traduzir e quando o tradutor levanta qualquer exceção. No cadastro, `None` significa apenas que o favorito fica sem tradução. Em `/translate`, `None` vira `502`.

O inglês é sempre o original gravado. A tradução fica à parte, em `translations.pt`, e é aplicada na leitura por `localize`.
