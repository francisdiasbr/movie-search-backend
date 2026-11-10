# Palavras-chave

Módulo: `keywords/` (`routes.py`, `controller.py`, `imdb.py`). Coleção: `favorites_keywords`.

## O que faz

Guarda uma lista de palavras-chave de interesse (por exemplo `french new wave`) e sugere filmes a partir de um conjunto delas. A sugestão consulta a API GraphQL do IMDB. Um termo que é o nome de um diretor traz os filmes dirigidos por essa pessoa. Filmes que aparecem para mais de um termo sobem na lista.

O arquivo `keywords/imdb.py` também serve outros módulos (banner e título brasileiro dos favoritos, séries, notas do Belas Artes). Essas consultas estão descritas em [integracoes.md](../integracoes.md).

## Rotas

Prefixo: `/api/keywords`.

| Método | Caminho | O que faz |
|---|---|---|
| `GET` | `/` | Lista as palavras-chave salvas. |
| `POST` | `/` | Salva uma palavra-chave. |
| `DELETE` | `/<keyword>` | Remove uma palavra-chave. |
| `POST` | `/suggest-movies` | Sugere filmes para uma lista de termos. |

### `GET /keywords/`

| Status | Corpo |
|---|---|
| `200` | `{"data": [{"_id": "...", "keyword": "..."}]}` |

A lista vem em ordem alfabética de `keyword`, sem paginação. Sem nenhuma palavra-chave salva, `data` é uma lista vazia.

### `POST /keywords/`

Corpo JSON obrigatório, modelo `KeywordInput`.

| Campo | Tipo | Obrigatório |
|---|---|---|
| `keyword` | string | sim |

| Status | Quando | Corpo |
|---|---|---|
| `201` | Palavra-chave salva. | `{"data": {"_id": "...", "keyword": "noir"}}` |
| `400` | Campo `keyword` ausente (validação do modelo). | `{"message": "Input payload validation failed", "errors": {"keyword": "'keyword' is a required property"}}` |
| `400` | `keyword` vazia ou só com espaços. | `{"message": "Keyword is required"}` |
| `409` | A palavra-chave já está na lista. | `{"message": "Keyword already listed"}` |
| `415` | Sem corpo JSON. | |

Regras:

- O valor é convertido para string e tem os espaços das pontas removidos antes de qualquer checagem.
- A comparação de duplicidade é por igualdade exata. `Noir` e `noir` são palavras-chave diferentes.

### `DELETE /keywords/<keyword>`

| Status | Quando | Corpo |
|---|---|---|
| `200` | Palavra-chave removida. | `{"data": "Keyword deleted successfully"}` |
| `404` | Não há palavra-chave com esse valor exato. | `{"message": "Keyword not found"}` |

### `POST /keywords/suggest-movies`

Corpo JSON obrigatório, modelo `KeywordsInput`.

| Campo | Tipo | Obrigatório |
|---|---|---|
| `keywords` | lista de strings | sim |

Os termos não precisam estar salvos na coleção. A rota usa a lista que recebe.

Exemplo de requisição:

```json
{ "keywords": ["french new wave", "François Truffaut"] }
```

Exemplo de resposta `200`:

```json
{
  "data": {
    "movies": [
      {
        "title": "The 400 Blows",
        "original_title": "Les quatre cents coups",
        "year": 1959,
        "tconst": "tt0053198",
        "description": "A young boy, left without attention, delves into a life of petty crime.",
        "relevance": "Palavras-chave no IMDb: french new wave, François Truffaut",
        "genres": ["Crime", "Drama"]
      }
    ]
  }
}
```

| Status | Quando | Corpo |
|---|---|---|
| `200` | Busca concluída, mesmo sem resultado. | `{"data": {"movies": [...]}}` |
| `400` | Campo `keywords` ausente ou de tipo errado (validação do modelo). | Erro de validação com `errors`. |
| `400` | `keywords` é uma lista vazia. | Veja a observação abaixo. |
| `415` | Sem corpo JSON. | |
| `502` | Todas as buscas no IMDB falharam e não há nenhum filme para devolver. | Veja a observação abaixo. |

Observação sobre o corpo dos erros: o método tem `@api.marshal_with(movie_suggestions_response_model)`, e o flask-restx aplica o modelo de resposta também às tuplas de erro. O controller devolve `{"message": "Falha ao buscar filmes no IMDb"}` e a rota devolve `{"message": "Lista de keywords inválida"}`, mas o corpo que chega ao cliente nesses dois casos é `{"data": {"movies": null}}`. O status (`400` ou `502`) é preservado.

Passo a passo (`suggest_movies_by_keywords`):

1. Converte cada termo para string, remove os espaços das pontas, descarta os vazios e elimina os repetidos, mantendo a ordem.
2. Para cada termo, chama `search_movies_by_director(termo, 15)`. Se a lista vier vazia, chama `search_movies_by_keyword(termo, 15)`.
3. Para cada filme devolvido, cria ou atualiza uma entrada indexada por `tconst`, com o filme, a lista de termos que o trouxeram e a posição (`rank`) em que apareceu pela primeira vez.
4. Se uma busca levanta `IMDBSearchError`, registra o erro, soma uma falha e segue para o próximo termo.
5. Se não há nenhum filme e houve ao menos uma falha, responde `502`.
6. Ordena por número de termos (decrescente) e, no empate, pelo `rank` (crescente).
7. Devolve os 15 primeiros (`SUGGESTION_LIMIT`), cada um com o campo `relevance`.

Regras e casos de borda:

- **Diretor antes de palavra-chave.** A busca por nome só aceita uma pessoa cujo nome, depois de retirar acentos, pontuação e maiúsculas, seja igual ao termo. A busca de nomes do IMDB é aproximada, e essa comparação evita trazer a pessoa errada. Os filmes dessa pessoa vêm ordenados pelo número de votos no IMDB.
- **Formato da palavra-chave.** `keyword_slug` converte o termo para o identificador do IMDB: minúsculas, sem acentos, com hifens no lugar de qualquer sequência que não seja letra ou número. `French New Wave` vira `french-new-wave`. Um termo que resulta em slug vazio não gera consulta.
- **Ordem dentro de uma palavra-chave.** A consulta pede os filmes por popularidade (`sortBy: POPULARITY, sortOrder: ASC`), e só títulos do tipo `movie`.
- **Termo desconhecido.** Um termo que o IMDB não conhece não contribui com nada. Se todos forem desconhecidos e nenhuma busca falhar, a resposta é `200` com `movies` vazio.
- **Falha parcial.** Se parte das buscas falha e outra parte traz filmes, a resposta é `200` com o que veio.
- **Campo `relevance`.** É o texto `Palavras-chave no IMDb: ` seguido dos termos que trouxeram o filme, separados por vírgula.
- **Campos extras.** O modelo de resposta define exatamente os sete campos do exemplo. Qualquer outro campo é descartado na serialização.
