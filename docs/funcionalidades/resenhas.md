# Resenhas

Módulo: `write_review/` (`routes.py`, `controller.py`). Coleção: `authoralreviewslist`. Namespace: `write-review`.

## O que faz

Guarda resenhas autorais, uma por filme. A resenha só pode ser criada para um filme que já está nos favoritos. O texto em português é obrigatório e o texto em inglês é opcional. A resenha também pode ter uma lista de referências e uma lista de URLs de imagens.

Este módulo não chama nenhum serviço externo.

## Rotas

Prefixo: `/api/write-review`.

| Método | Caminho | O que faz |
|---|---|---|
| `GET` | `/<tconst>` | Devolve a resenha de um filme. |
| `POST` | `/<tconst>` | Cria a resenha de um filme. |
| `PUT` | `/<tconst>` | Edita a resenha de um filme. |
| `DELETE` | `/<tconst>` | Remove a resenha de um filme. |
| `POST` | `/search` | Lista as resenhas, com filtros. |

### `POST /write-review/<tconst>`

Corpo JSON obrigatório, modelo `ReviewInput`.

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `content` | objeto com `pt` e `en`, cada um com `text` (string) | sim | |
| `references` | lista de strings | não | `[]` |
| `images` | lista de strings | não | `[]` |
| `isAiGenerated` | booleano | não | `false` |

O modelo exige `content`. A exigência de `content.pt.text` preenchido é feita pelo controller.

Exemplo de requisição:

```json
{
  "content": {
    "pt": { "text": "Truffaut filma a infância sem sentimentalismo." },
    "en": { "text": "Truffaut films childhood without sentimentality." }
  },
  "references": ["https://www.criterion.com/films/151-the-400-blows"],
  "images": []
}
```

Exemplo de resposta `201`:

```json
{
  "data": {
    "_id": "6af39177c5ec7dffafa34012",
    "tconst": "tt0053198",
    "content": {
      "pt": { "text": "Truffaut filma a infância sem sentimentalismo." },
      "en": { "text": "Truffaut films childhood without sentimentality." }
    },
    "created_at": "2026-11-10T18:49:43.076953",
    "isAiGenerated": false,
    "references": ["https://www.criterion.com/films/151-the-400-blows"],
    "images": [],
    "primaryTitle": "The 400 Blows"
  }
}
```

| Status | Quando | Corpo |
|---|---|---|
| `201` | Resenha criada. | `{"data": {...}}` |
| `400` | `content` ausente ou de tipo errado (validação do modelo). | Erro de validação com `errors`. |
| `400` | `content.pt.text` ausente ou vazio. | `{"message": "Conteúdo da review é obrigatório"}` |
| `404` | O filme não está nos favoritos. | `{"message": "Filme não encontrado nos favoritos"}` |
| `409` | Já existe resenha para o filme. | `{"message": "Já existe uma resenha para este filme"}` |
| `415` | Sem corpo JSON. | |

Passo a passo (`create_and_save_movie_review`):

1. Busca o filme em `favoritelist`. Sem ele, responde `404`.
2. Procura uma resenha com o mesmo `tconst`. Se existe, responde `409`.
3. Confere se `content.pt.text` está preenchido. Se não, responde `400`.
4. Insere o documento com `created_at` (`datetime.now().isoformat()`) e `primaryTitle` copiado do favorito.

A ordem das checagens importa: um corpo sem texto em português para um filme que não é favorito recebe `404`, e não `400`.

O `primaryTitle` é copiado no momento da criação. Não há código que o atualize depois.

### `GET /write-review/<tconst>`

| Status | Quando | Corpo |
|---|---|---|
| `200` | Há resenha para o filme. | `{"total_documents": 1, "entries": [{...}]}` |
| `404` | Não há resenha para o filme. | `{"message": "No reviews found for this movie"}` |

A resposta usa o formato de lista (`total_documents` e `entries`), e não `data`. O modelo `ReviewOutput` declarado no Swagger para essa rota descreve um objeto `data`, que não corresponde ao que o controller devolve.

### `PUT /write-review/<tconst>`

Corpo JSON obrigatório, modelo `ReviewUpdateInput`. Nenhum campo é obrigatório.

| Campo editável | Tipo |
|---|---|
| `content` | objeto com `pt` e `en` |
| `references` | lista de strings |
| `images` | lista de strings |

| Status | Quando | Corpo |
|---|---|---|
| `200` | Resenha atualizada, ou corpo sem campo editável. | `{"data": {...}}` com o documento completo. |
| `400` | Tipo errado num campo do modelo. | Erro de validação. |
| `404` | Não há resenha para o filme. | `{"message": "Review not found"}` |
| `415` | Sem corpo JSON. | |

Regras e casos de borda:

- Só os campos presentes no corpo são alterados (`pick` com `EDITABLE_FIELDS`).
- `content` é substituído inteiro. Enviar só `{"content": {"en": {...}}}` remove o texto em português, porque o `$set` troca o objeto `content` todo. A edição não repete a checagem de `content.pt.text` feita na criação.
- `isAiGenerated` não é editável.
- Um campo com valor `null` é ignorado.

### `DELETE /write-review/<tconst>`

| Status | Quando | Corpo |
|---|---|---|
| `200` | Resenha removida. | `{"message": "Review deleted successfully"}` |
| `404` | Não há resenha para o filme. | `{"message": "Review not found"}` |

### `POST /write-review/search`

Corpo JSON obrigatório (pode ser `{}`), modelo `SearchInput`.

| Campo | Tipo | Usado |
|---|---|---|
| `filters` | objeto | Sim. Filtro do MongoDB aplicado depois de `sanitize_filters`. |
| `page` | inteiro | Não. A rota não repassa o valor ao controller. |
| `page_size` | inteiro | Não. A rota não repassa o valor ao controller. |

| Status | Corpo |
|---|---|
| `200` | `{"total_documents": n, "entries": [...]}` |

A rota chama `get_created_reviews(filters=...)`, que não tem paginação. Todas as resenhas que casam com o filtro são devolvidas, com o documento completo, ordenadas por `_id` decrescente (as mais recentes primeiro).

## Corpo dentro de `data`

A função `review_body()` em `routes.py` aceita os campos da resenha no nível principal do corpo ou dentro de um objeto `data`. O comentário explica que clientes antigos enviavam o envelope.

Na prática, o envelope só funciona no `PUT`. No `POST`, o modelo `ReviewInput` exige `content` no nível principal, e a validação do flask-restx recusa o corpo `{"data": {"content": ...}}` com `400` antes de `review_body()` ser executada.
