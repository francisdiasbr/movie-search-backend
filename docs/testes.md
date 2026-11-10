# Testes

## Visão geral

A suíte usa pytest e roda sem rede. Nenhum teste acessa o MongoDB Atlas, o S3, o IMDB ou qualquer outro serviço externo. No momento em que este documento foi escrito, a suíte tinha 154 testes e rodava em menos de dois segundos.

| Ferramenta | Versão (`requirements-dev.txt`) | Papel |
|---|---|---|
| pytest | 9.2.0 | Execução dos testes |
| mongomock | 4.3.0 | MongoDB em memória |
| black | 24.10.0 | Formatação, conferida no CI |

O `pytest.ini` define `testpaths = tests` e `pythonpath = .`, o que permite importar os módulos da raiz (`import config`, `import db`) nos testes.

## Como rodar

```bash
pip install -r requirements-dev.txt

python -m pytest                          # a suíte inteira
python -m pytest tests/test_db.py         # um arquivo
python -m pytest -k suggest               # testes cujo nome contém "suggest"

python -m black --check .                 # a mesma conferência de formatação do CI
python -m black .                         # formata
```

Não é preciso `.env`, credenciais nem o Chromium do Playwright. Os pacotes `playwright` e `argostranslate` precisam estar instalados, porque são importados quando os módulos carregam. Eles vêm pelo `requirements.txt`, incluído no `requirements-dev.txt`.

## Organização

Há um arquivo de teste por módulo testado.

| Arquivo | Testes | O que cobre |
|---|---|---|
| `tests/conftest.py` | | Fixtures compartilhadas. |
| `tests/test_utils.py` | 17 | `error`, `json_body`, `pick`, `sanitize_movie_data`, `sanitize_filters` e `optimize_image`. |
| `tests/test_db.py` | 14 | `serialize`, `insert`, `search` (filtro, contagem, paginação, projeção, sanitização), `update` e `delete`. |
| `tests/test_favorites_controller.py` | 32 | `collect_movie_data`, cadastro, leitura com idioma e preenchimento tardio, tradução, edição com espelhamento no blogpost, remoção e busca. |
| `tests/test_keywords_controller.py` | 14 | CRUD de palavras-chave e a ordenação das sugestões. |
| `tests/test_write_review_controller.py` | 13 | Criação com as três recusas (`404`, `409`, `400`), leitura, edição, remoção e busca. |
| `tests/test_main_images_controller.py` | 15 | `s3_client`, envio, sequência, tags, falhas, listagem, remoção e `sanitize_tag_value`. |
| `tests/test_series_controller.py` | 16 | Cadastro com as recusas (`409`, `404`, `400`, `502`), leitura, listagem, edição e remoção. |
| `tests/test_belas_artes_controller.py` | 7 | Montagem da lista, escolha do título de busca, cache das notas, `502` e `404`. |
| `tests/test_app.py` | 26 | O app inteiro pelo cliente de teste do Flask: roteamento, validação do corpo e os handlers de `503`. |

Os testes de controller chamam as funções diretamente e conferem a tupla `(corpo, status)`. Só o `test_app.py` passa pelo HTTP.

### O que não tem teste próprio

Estes módulos não têm arquivo de teste. Nos testes dos controllers, as funções deles são substituídas por mocks:

- `favorites/scrapper.py` (thread do navegador, cache, novas tentativas do WAF e os seletores de cada scraper)
- `keywords/imdb.py` (consultas GraphQL, normalização, `keyword_slug`, escolha do banner e da nota)
- `favorites/translation.py` (`translate_movie`, tradução de citações; `localize` é exercitada indiretamente pelos testes de leitura de favoritos)
- `favorites/external_requests.py`
- `belas_artes/catalog.py` (`load_catalog`; `view_titles` é exercitada indiretamente pelos testes do controller)

## Fixtures

### Compartilhadas (`tests/conftest.py`)

| Fixture | Escopo | O que faz |
|---|---|---|
| `mongo` | `autouse`, por teste | Cria um `mongomock.MongoClient()`, substitui `config.get_mongo_client` por uma função que o devolve e define `config.MONGODB_DATABASE` como `"test"`. Devolve o banco `test`. |
| `favorites` | por teste | A coleção `favoritelist` do banco em memória. |

Como `mongo` é `autouse`, todo teste recebe um banco novo e vazio, mesmo sem pedir a fixture. Os controllers executam o código real de acesso ao Mongo (`find_one`, `insert_one`, `find_one_and_update`, `distinct`) contra esse banco.

A substituição é feita em `config.get_mongo_client`, e não em `get_mongo_collection`. Como `get_mongo_collection` resolve `get_mongo_client` no momento da chamada, a troca alcança todos os controllers sem alterar nenhum deles.

### Por módulo

| Arquivo | Fixture | O que faz |
|---|---|---|
| `test_favorites_controller.py` | `imdb` | Substitui `get_movie_title`, `collect_movie_data` e `translate_movie` no controller por atributos de um `Mock` com respostas prontas. |
| | `no_backfill` | Esvazia `BACKFILLS`, para que a leitura não tente consultar o IMDB. |
| | `catalog` | Insere um conjunto de favoritos para os testes de busca. |
| `test_keywords_controller.py` | `imdb` | Substitui as duas buscas por mocks que respondem a partir de dois dicionários (`by_keyword` e `by_director`) que cada teste preenche. |
| `test_main_images_controller.py` | `s3` | Substitui `s3_client` por uma função que devolve um `Mock`, e `optimize_image` por uma função que devolve o arquivo sem alterar. |
| | `images` | A coleção `main-images` do banco em memória. |
| `test_series_controller.py` | `imdb` | Substitui `find_series` e `find_brazilian_title`. |
| | `series`, `listed` | A coleção `serieslist`, vazia ou com séries inseridas. |
| `test_write_review_controller.py` | `reviews`, `favorite` | A coleção de resenhas e um favorito já inserido. |
| `test_belas_artes_controller.py` | `find_rating` | Substitui `find_rating` por um `Mock`, zera o cache `_ratings` e troca `load_catalog` por uma função que devolve um catálogo fixo. |
| `test_db.py` | `movies` | Uma coleção com cinco filmes, para os testes de busca e paginação. |
| `test_app.py` | `client` | `app.test_client()`. |

## O que é simulado e como

| Dependência | Como é simulada |
|---|---|
| MongoDB | `mongomock`, pela fixture `autouse`. O código de acesso a dados é o real. |
| S3 | `unittest.mock.Mock` devolvido por um `s3_client` substituído. Os testes conferem as chamadas `upload_fileobj`, `put_object_tagging` e `delete_object`, e usam `side_effect` para simular falhas (`ClientError`). |
| boto3 | Num teste, o próprio `boto3` do controller é trocado por um `Mock`, para conferir que `s3_client` passa as credenciais configuradas. |
| Scraper do IMDB | As funções são substituídas no controller. O Playwright nunca é iniciado. |
| GraphQL do IMDB | As funções de `keywords/imdb.py` são substituídas no controller que as importa. |
| Argos Translate | `translate_movie` é substituída no controller de favoritos. |
| Catálogo do Belas Artes | `load_catalog` é substituída por um catálogo fixo. `view_titles` roda de verdade. |
| Pillow | `optimize_image` é testada de verdade em `test_utils.py`, com imagens geradas em memória. Nos testes de envio ela é substituída. |
| Tempo | O teste de expiração do cache de notas recua o campo `at` de cada entrada de `_ratings` além de `RATING_TTL`, em vez de esperar ou simular o relógio. |

### Regras seguidas pelos mocks

O `CLAUDE.md` do repositório registra duas convenções, que os testes seguem:

- **Substituir onde o nome é procurado.** O mock é aplicado no módulo do controller (`monkeypatch.setattr(controller, "find_series", ...)`), e não no módulo que define a função. O controller importa o nome com `from ... import`, então é a referência dele que precisa ser trocada.
- **Dicionários de funções são trocados inteiros.** `SCRAPERS` e `BACKFILLS` guardam referências diretas às funções. Trocar a função no módulo não alteraria o dicionário, por isso os testes substituem o dicionário.

## Testes pelo cliente HTTP (`test_app.py`)

Este arquivo confere o que só existe com o app montado.

| Teste | O que garante |
|---|---|
| `test_home_reports_the_api_online` | `GET /` responde `200` com `status: online`. |
| `test_keyword_round_trip_through_the_routes` | Criar, repetir (`409`), listar e remover uma palavra-chave pelas rotas. |
| `test_swagger_model_validates_the_body` | Tipo errado e corpo que não é objeto recebem `400`. `{}` é uma edição válida. |
| `test_unknown_route_is_404_with_a_message` | Rota desconhecida recebe `404` em JSON com `message`. |
| `test_database_down_is_503` | `DatabaseUnavailable` vira `503` com a mensagem da exceção. |
| `test_storage_without_credentials_is_503` | `StorageUnavailable` vira `503`. |
| `test_blocked_imdb_is_503_and_not_404` | `IMDBUnavailable` no cadastro de favorito vira `503`, e não `404`. |
| `test_upload_without_a_file_is_400` | Envio de imagem sem o campo `file` recebe `400`. |
| `test_request_without_a_json_body_is_415` | Parametrizado: cada rota com `@api.expect` responde `415` sem corpo JSON. |
| `test_malformed_json_is_400` | Parametrizado: cada rota com `@api.expect` responde `400` com JSON malformado. |

Os dois últimos usam a lista `ROUTES_WITH_A_BODY`, com as nove rotas que declaram `@api.expect`. Uma rota nova com corpo deve ser acrescentada a essa lista.

## Integração contínua

Arquivo: `.github/workflows/ci.yml`. O fluxo se chama `CI` e roda a cada `push` e a cada `pull_request`, em qualquer branch.

Há um único job, `test`, em `ubuntu-latest`:

| Passo | O que faz |
|---|---|
| `actions/checkout@v4` | Baixa o repositório. |
| `actions/setup-python@v5` | Instala o Python 3.11, com cache do pip baseado nos arquivos `requirements*.txt`. |
| Install dependencies | `pip install -r requirements-dev.txt` |
| Check formatting | `black --check .` |
| Run tests | `python -m pytest` |

O fluxo não usa segredos e não instala o Chromium do Playwright. O comentário no arquivo explica que não é necessário, porque a suíte é offline.

O CI não publica nada: só confere a formatação e roda os testes.

### Formatação

O Black usa a configuração de `pyproject.toml`, que exclui a pasta `.claude/` (cópias de trabalho que não fazem parte do projeto). A mesma versão do Black está fixada em três lugares: `requirements-dev.txt`, `.pre-commit-config.yaml` e, por consequência, no CI. O `.pre-commit-config.yaml` permite rodar o Black antes de cada commit, para quem instalar o `pre-commit`.
