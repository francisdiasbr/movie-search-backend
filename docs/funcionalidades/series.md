# Séries

Módulo: `series/` (`routes.py`, `controller.py`). Coleção: `serieslist`.

## O que faz

Mantém uma lista de séries de TV. Quem usa informa o `tconst`. A API busca todos os dados na API GraphQL do IMDB: títulos original e brasileiro, anos de início e fim, sinopse, gêneros, pôster, nota, número de temporadas e de episódios, criadores e elenco. Depois é possível marcar a série como assistida, buscar na lista e remover.

Não há scraper nem sessão do IMDB envolvida. O cadastro faz duas consultas GraphQL.

## Rotas

Prefixo: `/api/series`.

| Método | Caminho | O que faz |
|---|---|---|
| `POST` | `/search` | Lista as séries, com filtros, termo de busca e paginação. |
| `GET` | `/<tconst>` | Devolve uma série. |
| `POST` | `/<tconst>` | Adiciona uma série. |
| `PUT` | `/<tconst>` | Edita uma série (campo `watched`). |
| `DELETE` | `/<tconst>` | Remove uma série. |

### `POST /series/<tconst>`

Não recebe corpo.

Exemplo de resposta `201`:

```json
{
  "data": {
    "_id": "665f1c2e9b1e8a0012345679",
    "tconst": "tt0903747",
    "primaryTitle": "Breaking Bad",
    "originalTitle": "Breaking Bad",
    "startYear": 2008,
    "endYear": 2013,
    "plot": "A chemistry teacher diagnosed with cancer turns to making drugs.",
    "genres": ["Crime", "Drama", "Thriller"],
    "poster_url": "https://m.media-amazon.com/images/M/..._V1_UX400_.jpg",
    "imdb_rating": 9.5,
    "seasons": 5,
    "episodes": 62,
    "creators": ["Vince Gilligan"],
    "stars": ["Bryan Cranston", "Aaron Paul", "Anna Gunn"],
    "title_pt": "Breaking Bad: A Química do Mal",
    "imdb_url": "https://www.imdb.com/title/tt0903747/",
    "watched": false,
    "created_at": "2026-11-10T18:49:43.076953"
  }
}
```

| Status | Quando | Corpo |
|---|---|---|
| `201` | Série adicionada. | `{"data": {...}}` |
| `400` | O título existe no IMDB, mas não é série. | `{"message": "Esse título não é uma série"}` |
| `404` | O IMDB não tem um título com esse `tconst`. | `{"message": "Título não encontrado no IMDb"}` |
| `409` | A série já está na lista. | `{"message": "Série já está na lista"}` |
| `502` | A API do IMDB falhou. | `{"message": "IMDb não respondeu à consulta da série"}` |
| `503` | MongoDB indisponível. | |

Passo a passo (`add_series`):

1. Procura um documento com o mesmo `tconst`. Se existe, responde `409`.
2. Chama `find_series(tconst)`. Se encontrou o título, chama também `find_brazilian_title(tconst)`. Uma `IMDBSearchError` em qualquer das duas vira `502`.
3. Sem título, responde `404`.
4. Se `is_series` é falso, responde `400`.
5. Insere o documento com os dados do IMDB mais `title_pt`, `imdb_url`, `watched` (`false`) e `created_at`.

Regras e casos de borda:

- **O que conta como série.** `is_series` é verdadeiro quando o tipo do título no IMDB é `tvSeries` ou `tvMiniSeries`. Filmes e episódios recebem `400`.
- **Título brasileiro.** `title_pt` fica como string vazia quando o IMDB não tem um título brasileiro diferente do original.
- **Falha no título brasileiro.** Se `find_series` funciona e `find_brazilian_title` falha, a resposta é `502` e nada é gravado.
- **Campo `is_series`.** É retirado do dicionário antes da gravação e não vai para o banco.
- **Série em exibição.** `endYear` é `null` quando o IMDB não informa o ano de fim.
- A checagem de duplicidade é um `find_one` seguido de `insert_one`, sem índice único.

### `GET /series/<tconst>`

| Status | Quando | Corpo |
|---|---|---|
| `200` | Série encontrada. | `{"data": {...}}` com o documento completo. |
| `404` | Não há série com esse `tconst`. | `{"message": "Série não encontrada"}` |

A leitura não consulta o IMDB. Os dados são os gravados no cadastro, e não há rota que os atualize.

### `PUT /series/<tconst>`

Corpo JSON obrigatório, modelo `SeriesEdit`.

| Campo | Tipo | Obrigatório |
|---|---|---|
| `watched` | booleano | não |

| Status | Quando | Corpo |
|---|---|---|
| `200` | Série atualizada, ou corpo `{}`. | `{"data": {...}}` com o documento completo. |
| `400` | `watched` não é booleano, ou o corpo não é um objeto. | Erro de validação. |
| `404` | Não há série com esse `tconst`. | `{"message": "Série não encontrada"}` |
| `415` | Sem corpo JSON. | |

`watched` é o único campo editável (`EDITABLE_FIELDS`). Um corpo `{}` devolve o documento atual sem alterar nada.

### `DELETE /series/<tconst>`

| Status | Quando | Corpo |
|---|---|---|
| `200` | Série removida. | `{"data": "Series tt0903747 deleted"}` |
| `404` | Não há série com esse `tconst`. | `{"message": "Série não encontrada"}` |

### `POST /series/search`

Corpo JSON obrigatório (pode ser `{}`), modelo `SeriesSearch`.

| Campo | Tipo | Padrão | Significado |
|---|---|---|---|
| `filters` | objeto | `{}` | Filtro do MongoDB aplicado depois de `sanitize_filters`. |
| `page` | inteiro | `1` | Página, começando em 1. |
| `page_size` | inteiro | `0` | Itens por página. `0` devolve tudo. |
| `search_term` | string | `""` | Termo procurado no `tconst` (igualdade), em `primaryTitle` e em `title_pt` (trecho, sem diferenciar maiúsculas). |

Exemplo de resposta `200`:

```json
{
  "total_documents": 1,
  "entries": [
    {
      "_id": "665f1c2e9b1e8a0012345679",
      "endYear": 2013,
      "episodes": 62,
      "genres": ["Crime", "Drama", "Thriller"],
      "imdb_rating": 9.5,
      "poster_url": "https://m.media-amazon.com/images/M/..._V1_UX400_.jpg",
      "primaryTitle": "Breaking Bad",
      "seasons": 5,
      "startYear": 2008,
      "tconst": "tt0903747",
      "title_pt": "Breaking Bad: A Química do Mal",
      "watched": false
    }
  ]
}
```

Regras e casos de borda:

- A lista vem em ordem alfabética de `primaryTitle`.
- A projeção `LIST_PROJECTION` deixa de fora `plot`, `creators`, `stars`, `originalTitle`, `imdb_url` e `created_at`. Esses campos vêm no `GET /<tconst>`.
- Com `search_term`, o `$or` é somado aos demais filtros. Um filtro `{"watched": false}` com um termo devolve só as séries não assistidas que casam com o termo.
- Diferentemente da busca de favoritos, aqui o termo só é lido do campo `search_term` do corpo. Um `search_term` dentro de `filters` é tratado como filtro de campo.
- O comportamento com `page` menor que 1 e `page_size` maior que zero não foi verificado contra um MongoDB real.
