# Belas Artes à la Carte

Módulo: `belas_artes/` (`routes.py`, `controller.py`, `catalog.py`). Não usa o MongoDB.

## O que faz

Lista os filmes da seção "Adicionados recentemente" do serviço de streaming Belas Artes à la Carte e acrescenta a cada um a nota e o `tconst` do IMDB. O objetivo é ver de uma vez o que entrou no catálogo e como cada filme é avaliado.

O catálogo vem do mesmo JSON público que o site do serviço carrega. A nota vem da API GraphQL do IMDB. Nada é gravado em banco: o catálogo e as notas ficam em memória no processo.

## Rota

### `GET /belas-artes/recent`

Não recebe parâmetros.

Exemplo de resposta `200`:

```json
{
  "data": {
    "movies": [
      {
        "id": 1234,
        "title": "Acossado",
        "original_title": "À bout de souffle",
        "year": 1960,
        "director": "Jean-Luc Godard",
        "tconst": "tt0053472",
        "imdb_rating": 7.7
      },
      {
        "id": 1235,
        "title": "Um Filme Sem Correspondência",
        "original_title": "",
        "year": 1971,
        "director": "Fulano de Tal",
        "tconst": null,
        "imdb_rating": null
      }
    ]
  }
}
```

| Status | Quando | Corpo |
|---|---|---|
| `200` | Catálogo lido. | `{"data": {"movies": [...]}}` |
| `404` | O catálogo não tem a seção `adicionados-recentemente`. | `{"message": "Seção de adicionados recentemente não encontrada"}` |
| `502` | A API ou o armazenamento do Belas Artes não respondeu. | `{"message": "Falha ao buscar o catálogo do Belas Artes"}` |

Campos de cada filme:

| Campo | Origem |
|---|---|
| `id` | Id do título no catálogo. |
| `title` | Título em português do catálogo, sem espaços nas pontas. |
| `original_title` | Título original do catálogo, sem espaços nas pontas. |
| `year` | Ano do catálogo. |
| `director` | Direção, como no catálogo, sem espaços nas pontas. |
| `tconst` | Do IMDB. `null` quando não houve correspondência. |
| `imdb_rating` | Do IMDB. `null` quando não houve correspondência ou o título não tem nota. |

## Passo a passo

`get_recently_added` faz o seguinte:

1. Chama `load_catalog()`, que devolve o catálogo inteiro (veja abaixo).
2. Chama `view_titles(catalog, "adicionados-recentemente")`, que devolve os títulos da seção. Uma `CatalogUnavailable` em qualquer das duas chamadas vira `502`.
3. Se a seção não existe, responde `404`.
4. Com um `ThreadPoolExecutor` de 8 threads, chama `_rating(título, ano)` para cada filme. O título usado na busca é o original quando existe, e o título em português quando não.
5. Monta a lista na ordem do catálogo.

### Carga do catálogo (`load_catalog`)

1. Pede `https://prd-core-alacarte.futuraproducoes.com.br/api/v1/version` e lê `app.url`, que é o endereço do armazenamento.
2. Pede `<armazenamento>/api/prepare/version.json.gz` e lê `version` e `path`.
3. Se a versão é diferente da que está em memória, baixa `<armazenamento>/<path>` e guarda o catálogo e a versão.
4. Devolve o catálogo em memória.

As duas primeiras requisições acontecem em toda chamada da rota. O JSON grande só é baixado quando a versão muda. Uma trava (`_lock`) envolve a comparação e o download.

### Títulos da seção (`view_titles`)

1. Procura em `catalog["views"]` a view cujo `slug` é o pedido. Se não acha, devolve `None`.
2. Junta os ids das listas do tipo `GRID` da view. As listas do tipo `BANNERS` só guardam a imagem do cabeçalho e são ignoradas.
3. Remove os ids repetidos, mantendo a ordem do site.
4. Devolve os títulos correspondentes em `catalog["titles"]`, ignorando ids que não estão lá.

### Busca da nota (`_rating` e `find_rating`)

`find_rating(title, year)` em `keywords/imdb.py`:

1. Normaliza o título procurado: sem acentos, sem pontuação, em minúsculas. Sem título ou sem ano, devolve `None`.
2. Faz uma busca avançada de títulos no IMDB pelo texto, restrita ao intervalo de `ano - 1` a `ano + 1` e aos tipos `movie`, `tvMovie` e `tvMiniSeries`, pedindo os 5 mais populares.
3. Mantém só os candidatos cujo título ou título original, normalizado, é igual ao procurado.
4. Entre os candidatos, escolhe o de ano mais próximo.
5. Devolve `{"tconst", "rating"}`, ou `None` sem candidato.

`_rating` envolve essa busca com um cache em memória:

| Situação | O que é guardado |
|---|---|
| O IMDB devolveu uma correspondência | A correspondência, por 24 horas. |
| O IMDB respondeu sem correspondência | `None`, por 24 horas. |
| A busca levantou `IMDBSearchError` | Nada. A próxima chamada tenta de novo. |

A chave do cache é o par `(título, ano)`.

## Regras e casos de borda

- **Tolerância de um ano.** O comentário no código registra que os catálogos costumam divergir do IMDB em um ano. Por isso a busca cobre três anos e escolhe o mais próximo.
- **Comparação exata depois de normalizar.** A busca de títulos do IMDB é aproximada. Só é aceito um candidato cujo título fique idêntico ao procurado depois da normalização.
- **Falha do IMDB não derruba a rota.** Se a busca de um filme falha, esse filme sai com `tconst` e `imdb_rating` nulos e a resposta continua `200`. Mesmo que todas as buscas falhem, a rota responde `200`.
- **Seção sem títulos.** Uma seção existente e vazia devolve `200` com `movies` vazio. O `404` é só para a seção inexistente.
- **Formato inesperado do catálogo.** O código lê chaves fixas (`app.url`, `version`, `path`, `views`, `titles`, `lists`, `type`, `items`, `slug`). Só `CatalogUnavailable` é capturada. Uma mudança no formato do JSON levantaria `KeyError`, que não tem tratamento e resultaria em `500`.
- **Cache sem limite.** O dicionário `_ratings` não remove entradas antigas. As entradas vencidas são substituídas quando o mesmo título é pedido de novo.
- **Reinício.** O catálogo e as notas vivem na memória do processo e se perdem quando ele reinicia.
