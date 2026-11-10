# Integrações

Este documento descreve cada serviço externo que o backend usa: como é chamado, o que fica em cache, como falha e o que a API responde nesse caso.

## Resumo

| Serviço | Arquivo | Usado por | Precisa de credencial | Quando falha |
|---|---|---|---|---|
| IMDB, páginas HTML | `favorites/scrapper.py` | Cadastro de favorito | Sessão no perfil do Chromium | WAF: `503`. Outras falhas: campo omitido, ou `404` se for o título. |
| IMDB, API GraphQL | `keywords/imdb.py` | Sugestões, banner e título brasileiro, séries, notas | Não | Depende de quem chama. Veja a tabela da seção. |
| AWS S3 | `main_images/controller.py` | Imagens | Chaves da AWS | Sem chaves: `503`. Erro na operação: `500`. |
| Argos Translate | `favorites/translation.py` | Tradução dos favoritos | Não | No cadastro: favorito salvo sem tradução. Em `/translate`: `502`. |
| RapidAPI | `favorites/external_requests.py` | `magnet_link` do favorito | `RAPIDAPI_API_KEY` | Campo omitido. |
| OpenSubtitles | `favorites/external_requests.py` | `subtitle_url` do favorito | `OPEN_SUBTITLES_API_KEY` | Campo omitido. |
| Wikipedia | `favorites/scrapper.py` | `wiki` do favorito | Não | Campo omitido. |
| Belas Artes à la Carte | `belas_artes/catalog.py` | `GET /belas-artes/recent` | Não | `502`. |
| MongoDB Atlas | `config.py` | Todos, menos Belas Artes | String de conexão | `503`. |

O tempo limite das chamadas HTTP feitas com `requests` é `HTTP_TIMEOUT` (15 s), exceto a consulta à Wikipedia, que usa 10 s.

## IMDB: scraper com Playwright

Arquivo: `favorites/scrapper.py`. Usado só pelo cadastro de favoritos (`POST /favorites/<tconst>`).

O IMDB fica atrás do AWS WAF, que apresenta uma verificação humana a clientes automatizados. O scraper contorna isso com um navegador de verdade e um perfil persistente, onde ficam os cookies da verificação feita manualmente uma vez.

### Navegador e perfil

| Item | Valor |
|---|---|
| Navegador | Chromium, via `launch_persistent_context` |
| Diretório do perfil | `~/.cache/movie-search/imdb-profile` (`PROFILE_DIR`) |
| Modo | Sem janela, salvo com `IMDB_HEADLESS=0` |
| `locale` | `en-US` |
| `user_agent` | Chrome 124 em macOS (`USER_AGENT`) |
| `viewport` | 1280 x 800 |

O binário do Chromium é instalado à parte, com `playwright install chromium`.

### Thread dedicada

Toda carga de página passa por uma única thread, `_browser_loop`, que é dona do Playwright. Há dois motivos, registrados no código: a API síncrona do Playwright não pode ser usada fora da thread que a criou, e o Chromium tranca o diretório do perfil.

As threads de requisição põem um trabalho `(url, box, done)` na fila `_jobs` e esperam o evento `done` por até 90 s. A thread do navegador, para cada trabalho:

1. Espera o que falta para completar o intervalo mínimo desde a carga anterior.
2. Abre uma aba nova.
3. Navega com `wait_until="domcontentloaded"` e tempo limite de 30 s.
4. Espera por até 15 s um destes seletores: `[data-testid='hero__pageTitle']`, `[data-testid='title-details-section']` ou `h1`.
5. Guarda o HTML em `box["html"]`, ou a exceção em `box["error"]`.
6. Fecha a aba e sinaliza `done`.

A thread é criada na primeira carga e recriada se tiver morrido (`_ensure_worker`). É uma thread `daemon`, encerrada com um `None` na fila, registrado em `atexit`.

O diagrama desse fluxo está em [arquitetura.md](arquitetura.md#a-thread-do-navegador).

### Limite de taxa

| Constante | Valor | Efeito |
|---|---|---|
| `MIN_INTERVAL` | 1,5 s | Intervalo mínimo entre o fim de uma carga e o início da seguinte. |
| Variação aleatória | 0 a 0,5 s | Somada à espera, quando há espera. |

O limite vale para o processo inteiro, porque a thread é única.

### Cache de páginas

`fetch_soup(tconst, path)` guarda o resultado já interpretado pelo BeautifulSoup num dicionário em memória.

| Item | Valor |
|---|---|
| Chave | `(tconst, path)` |
| Validade | `CACHE_TTL`, 600 s |
| O que é guardado | Só páginas carregadas com sucesso e que não são o desafio do WAF |
| Limpeza | `clear_soup_cache()`, chamada por `collect_movie_data` ao terminar ou ao receber `IMDBUnavailable` |
| Proteção | `_cache_lock` |

O cache existe para que os nove scrapers da página principal usem uma única carga durante um cadastro. O cadastro inteiro carrega quatro páginas: a principal, `trivia`, `quotes` e `keywords`.

### Bloqueio do WAF e novas tentativas

`_is_waf_challenge` identifica o desafio pelo título da página: contém `human verification`, sem diferenciar maiúsculas.

| Tentativa | Resultado: desafio do WAF | Espera antes da próxima |
|---|---|---|
| 1 | Registra um aviso e tenta de novo. | 3 s |
| 2 | Registra um aviso e tenta de novo. | 6 s |
| 3 | Registra um erro e levanta `IMDBUnavailable`. | |

A espera é `WAF_RETRY_DELAY * tentativa`. O comentário no código diz que o desafio costuma ser passageiro: o token no perfil continua válido e a nova tentativa passa.

Quando as três tentativas falham, o `app.py` responde:

```json
{ "message": "IMDB bloqueou o acesso. Renove a sessão com ./verify_imdb.sh" }
```

com status `503`. O cadastro é interrompido e nada é gravado.

### Renovação da sessão

| Script | O que faz |
|---|---|
| `imdb_verify.py [tconst]` | Abre o Chromium com janela, no mesmo perfil, na página de um título (padrão `tt0032138`). Espera a pessoa resolver a verificação e apertar Enter. Depois informa se o título da página ainda é o do desafio. |
| `verify_imdb.sh` | Para o processo que está na porta 5000, testa a sessão chamando `fetch_soup('tt0032138')`, roda `imdb_verify.py` se o teste falhar e sobe o backend com `python app.py`. |

O backend precisa estar parado durante a verificação, porque o perfil só pode ser aberto por um processo. O `verify_imdb.sh` cuida dessa ordem.

### Como cada scraper lê a página

Cada função é decorada com `@imdb_page(path)`. O decorador carrega a página e só chama a função se a carga funcionou. Quando a página não carrega, a função devolve `None` sem ser executada.

| Função | Página | O que lê |
|---|---|---|
| `get_movie_title` | principal | `h1[data-testid='hero__pageTitle']`, de preferência o `span[data-testid='hero__primary-text']` dentro dele. |
| `get_movie_year` | principal | Primeiro item da primeira `ul.ipc-inline-list` depois do título. Convertido para inteiro quando possível. |
| `get_movie_sm_plot` | principal | `span[data-testid='plot-xs_to_m']`. |
| `get_movie_country` | principal | Primeiro link em `[data-testid='title-details-origin']`, dentro da seção de detalhes. |
| `get_director` | principal | Primeiro link da 1ª seção `li[data-testid='title-pc-principal-credit']`. |
| `get_writers` | principal | Todos os links da 2ª seção de créditos. |
| `get_movie_principal_stars` | principal | Os links da 3ª seção de créditos. |
| `get_movie_genres` | principal | Os `span.ipc-chip__text` dentro de `div[data-testid='interests']`. |
| `get_movie_poster` | principal | Três tentativas em ordem: imagem em `hero-media__poster` ou `hero__poster`; link `a.ipc-lockup-overlay` com `aria-label` contendo `poster` ou `pôster`; primeira `img.ipc-image` dentro de `.ipc-poster`. |
| `get_movie_trivia` | `trivia` | As cinco primeiras `div.ipc-html-content-inner-div`, unidas por linha em branco. |
| `get_movie_quote` | `quotes` | A `ul` dentro da primeira `div.ipc-html-content-inner-div`. |
| `get_movie_plot_keywords` | `keywords` | O link de cada `li[data-testid='list-summary-item']`. |

Os créditos dependem da posição das seções na página (0 direção, 1 roteiro, 2 elenco). Se a página tem menos seções que o índice pedido, a função registra um aviso e devolve `None`.

### Como falha

| Situação | O que `fetch_soup` faz | O que a API responde |
|---|---|---|
| Desafio do WAF nas três tentativas | Levanta `IMDBUnavailable`. | `503`. |
| A thread do navegador não responde em 90 s | Devolve `None`. | Se for a busca do título: `404 Título do filme não encontrado no IMDB`. Nos demais campos: o campo é omitido. |
| Erro na navegação ou na espera do seletor | Registra o erro e devolve `None`, sem nova tentativa. | Igual à linha anterior. |
| A página carrega, mas o elemento não existe | A função devolve `None`. | O campo é omitido. Se for o título: `404`. |

A terceira linha merece atenção: uma página que não é o desafio do WAF mas também não tem nenhum dos seletores esperados cai no tempo limite de 15 s e é tratada como falha comum, e não como bloqueio. Se a página de desafio do WAF contém ou não um `h1` (o que determinaria qual caminho ela segue) não foi verificado.

## IMDB: API GraphQL

Arquivo: `keywords/imdb.py`. Endereço: `https://api.graphql.imdb.com/`.

É a API por trás da busca avançada do site do IMDB. Segundo a docstring do módulo, não exige sessão nem chave e não está atrás do WAF que bloqueia o scraper. O único requisito é o cabeçalho `x-imdb-client-name`: sem ele a resposta é `403`.

### Cabeçalhos

| Cabeçalho | Valor padrão (`HEADERS`) | Valor para o Brasil (`BRAZIL_HEADERS`) |
|---|---|---|
| `Content-Type` | `application/json` | igual |
| `User-Agent` | Chrome 130 em macOS | igual |
| `x-imdb-client-name` | `imdb-web-next-localized` | igual |
| `x-imdb-user-country` | `US` | `BR` |
| `x-imdb-user-language` | `en-US` | `pt-BR` |

A API localiza o campo `titleText` de acordo com esses cabeçalhos. Os valores padrão devolvem o título em inglês. `BRAZIL_HEADERS` é usado só por `find_brazilian_title`.

### Consultas

| Constante | Operação GraphQL | Função | Para que serve |
|---|---|---|---|
| `SEARCH_QUERY` | `advancedTitleSearch` com `keywordConstraint` | `search_movies_by_keyword` | Filmes (`movie`) com uma palavra-chave, por popularidade. |
| `DIRECTOR_QUERY` | `mainSearch` com `type: NAME`, 5 resultados | `search_movies_by_director` | Encontrar a pessoa pelo nome. |
| `DIRECTED_QUERY` | `name.credits` com categoria `director` e tipo `movie`, até 250 | `search_movies_by_director` | Filmes dirigidos pela pessoa, com o número de votos. |
| `RATING_QUERY` | `advancedTitleSearch` com `titleTextConstraint` e `releaseDateConstraint`, 5 resultados | `find_rating` | Nota e `tconst` de um título, dado o nome e o ano. |
| `IMAGES_QUERY` | `title.images`, 50 primeiras | `find_backdrop` | Imagem larga para o banner do favorito. |
| `LOCALIZED_TITLE_QUERY` | `title.titleText` e `originalTitleText` | `find_brazilian_title` | Título do filme no Brasil. |
| `SERIES_QUERY` | `title` com tipo, anos, sinopse, gêneros, imagem, nota, episódios e créditos | `find_series` | Todos os dados de uma série. |

### Regras de cada função

**`search_movies_by_keyword(keyword, first)`**. Converte o termo com `keyword_slug` (minúsculas, sem acentos, hifens entre as palavras). Um slug vazio devolve lista vazia sem consultar. Cada filme sai com `tconst`, `title`, `original_title`, `year`, `description` e `genres`.

**`search_movies_by_director(name, first)`**. Busca até cinco pessoas pelo nome e aceita a primeira cujo nome normalizado é igual ao termo normalizado. Sem pessoa, devolve lista vazia. Depois busca os créditos de direção em filmes, ordena pelo número de votos (decrescente) e devolve os `first` primeiros.

**`find_rating(title, year)`**. Busca pelo texto do título entre `ano - 1` e `ano + 1`, nos tipos `movie`, `tvMovie` e `tvMiniSeries`. Aceita só candidatos cujo título ou título original normalizado é igual ao procurado. Escolhe o de ano mais próximo.

**`find_backdrop(tconst)`**. Entre as 50 primeiras imagens do título, considera só as do tipo `still_frame` com largura e altura informadas e proporção largura/altura de pelo menos 1,4 (`BACKDROP_MIN_RATIO`). Escolhe a mais larga e troca `._V1_.` por `._V1_UX1600_.` na URL, para pedir a imagem com 1600 px de largura. Devolve `None` sem imagem adequada. A docstring explica a escolha: pôsteres e capas são verticais, e fotos de divulgação costumam ser montagens.

**`find_brazilian_title(tconst)`**. Pede o título com os cabeçalhos do Brasil. Devolve `None` quando o título localizado é vazio ou igual ao original.

**`find_series(tconst)`**. Devolve `None` quando o IMDB não tem o título. Caso contrário devolve um dicionário com os campos descritos em [modelo-de-dados.md](modelo-de-dados.md#serieslist), mais `is_series`.

A normalização (`_normalize`) remove acentos, passa para minúsculas e elimina tudo que não é letra ou número. `The Cook, the Thief, His Wife & Her Lover` vira `thecookthethiefhiswifeherlover`.

### Novas tentativas

O módulo usa uma `requests.Session` compartilhada, com um adaptador `HTTPAdapter(max_retries=Retry(connect=3, backoff_factor=0.5))`. Só falhas de conexão são refeitas. O comentário explica o motivo: as buscas de nota em paralelo às vezes falham ao resolver o host na primeira rajada.

Não há cache neste módulo. O cache de notas fica em `belas_artes/controller.py`.

### Como falha

`_post` levanta `IMDBSearchError` em três casos: erro de rede ou status HTTP de erro, resposta que não é JSON, e resposta JSON com o campo `errors` preenchido. O que acontece depois depende de quem chamou.

| Quem chama | Função | Resposta da API |
|---|---|---|
| `POST /keywords/suggest-movies` | `search_movies_by_director`, `search_movies_by_keyword` | O termo é ignorado. `502` só se nenhum filme foi encontrado e houve ao menos uma falha. |
| `POST /favorites/<tconst>` | `find_backdrop`, `find_brazilian_title` | O campo é omitido e o cadastro continua. O campo é preenchido numa leitura posterior. |
| `GET /favorites/<tconst>` | `find_backdrop`, `find_brazilian_title` | A leitura responde `200` sem o campo. Nada é gravado, e a próxima leitura tenta de novo. |
| `POST /series/<tconst>` | `find_series`, `find_brazilian_title` | `502 IMDb não respondeu à consulta da série`. |
| `GET /belas-artes/recent` | `find_rating` | O filme sai com `tconst` e `imdb_rating` nulos. A falha não é guardada em cache. |

## AWS S3

Arquivo: `main_images/controller.py`. É o único serviço da AWS usado.

`s3_client()` é o único ponto que cria o cliente, com `boto3.client("s3", ...)` e as credenciais explícitas de `config.py`. Um cliente novo é criado a cada chamada.

| Operação | Chamada do boto3 | Rota |
|---|---|---|
| Envio | `upload_fileobj` com `ExtraArgs={"ContentType": ...}` | `POST /main-images/<tconst>` |
| Tags | `put_object_tagging` | `POST /main-images/<tconst>`, quando há legenda |
| Remoção | `delete_object` | `DELETE /main-images/<tconst>/<filename>` |

A listagem não chama o S3. As URLs são montadas a partir do Mongo.

As chaves, o bucket e as tags estão descritos em [modelo-de-dados.md](modelo-de-dados.md#aws-s3).

### Como falha

| Situação | Resposta da API |
|---|---|
| `AWS_ACCESS_KEY_ID` ou `AWS_SECRET_ACCESS_KEY` vazias | `503 Credenciais AWS não configuradas`, no envio e na remoção. |
| Qualquer exceção no envio ou nas tags | `500 Erro ao fazer upload para S3`. |
| `ClientError` na remoção | `500 Erro ao deletar imagem`. O metadado no Mongo é mantido. |
| Outra exceção do boto3 na remoção | Sem tratamento: `500 Internal Server Error`. |

Credenciais presentes mas inválidas não são detectadas por `s3_client()`. O erro aparece na operação e segue as linhas 2 a 4.

## Argos Translate

Arquivo: `favorites/translation.py`. Biblioteca: `argostranslate` 1.11.0.

O Argos Translate roda um modelo de tradução local. Não usa chave de API. A docstring do módulo informa que o pacote en→pt tem cerca de 100 MB e é baixado para `~/.local/share/argos-translate` na primeira tradução. Depois disso a tradução não usa rede.

### Inicialização

`_get_translator()` é protegida por `_translator_lock` e guarda o tradutor em `_translator`. Na primeira chamada do processo:

1. Lista os idiomas instalados.
2. Se `en` e `pt` não estão ambos instalados, atualiza o índice de pacotes, procura o pacote de `en` para `pt`, baixa e instala.
3. Obtém a tradução `en` → `pt`.

A primeira tradução de uma instalação nova precisa de rede e demora mais, por causa do download.

O módulo também reduz o volume de log do Argos: os loggers `argostranslate.utils` e `stanza` são ajustados para `WARNING` e `ERROR`.

### O que é traduzido

Os campos e a forma de traduzir cada tipo estão em [funcionalidades/favoritos.md](funcionalidades/favoritos.md#tradução).

### Como falha

`translate_movie` captura qualquer exceção (falha no download do pacote, erro do tradutor), registra o erro e devolve `None`.

| Onde | Resposta da API |
|---|---|
| `POST /favorites/<tconst>` | `201`. O favorito é salvo sem `translations`. |
| `POST /favorites/<tconst>/translate` | `502 Falha ao traduzir o filme`. |
| `GET /favorites/<tconst>?lang=pt` de um favorito sem tradução | `200`, em inglês, com `"lang": "en"`. |

## RapidAPI: magnet link

Arquivo: `favorites/external_requests.py`, função `get_magnet_link(tconst)`.

| Item | Valor |
|---|---|
| Requisição | `GET https://movie_torrent_api1.p.rapidapi.com/search/<tconst>` |
| Cabeçalhos | `x-rapidapi-key` (`RAPIDAPI_API_KEY`), `x-rapidapi-host`, `x-rapidapi-ua: RapidAPI-Playground` |
| Resposta esperada | Objeto com `data`, uma lista de resultados com `seeds` e `magnet` |
| Escolha | O resultado com mais `seeds` |

Devolve `None`, e o campo `magnet_link` fica fora do favorito, quando: a requisição falha ou devolve status de erro, a resposta não é JSON, `data` não é uma lista com itens, ou o resultado escolhido não tem `magnet`. As falhas são registradas com `logger.warning`.

Sem a chave configurada, a requisição é enviada do mesmo jeito. O resultado esperado é um status de erro e o campo omitido. A API não responde `503` por falta dessa chave.

## OpenSubtitles: legenda

Arquivo: `favorites/external_requests.py`, função `get_subtitle_url(tconst)`.

| Item | Valor |
|---|---|
| Requisição | `GET https://api.opensubtitles.com/api/v1/subtitles` |
| Parâmetros | `imdb_id` (o `tconst` sem o prefixo `tt`) e `languages=en` |
| Cabeçalhos | `Api-Key` (`OPEN_SUBTITLES_API_KEY`), `User-Agent: Movie-Search-API/1.0` |
| Escolha | `attributes.url` do primeiro resultado em `data` |

Devolve `None`, e o campo `subtitle_url` fica fora do favorito, nos mesmos tipos de falha do magnet link. O comportamento sem a chave é o mesmo.

## Wikipedia

Arquivo: `favorites/scrapper.py`, função `get_wikipedia_url(movie_title)`.

Monta a URL `https://en.wikipedia.org/wiki/<título com sublinhados no lugar dos espaços>` e faz um `GET` com tempo limite de 10 s. Se o status é `200`, devolve a URL. Em qualquer outro caso devolve `None`, e o campo `wiki` fica fora do favorito.

É uma checagem de existência, e não uma busca. O código não confere se a página encontrada é sobre o filme. Um título que coincide com outro assunto resulta numa URL que existe e aponta para esse outro assunto. O campo `wiki` é editável pelo `PUT /favorites/<tconst>`.

## Belas Artes à la Carte

Arquivo: `belas_artes/catalog.py`.

A docstring do módulo explica a origem: o site `www.belasartesalacarte.com.br` é uma aplicação de página única que pergunta a uma API onde fica o armazenamento e depois baixa um JSON público com todos os títulos, seções e pessoas. Não há login, chave nem HTML para interpretar.

| Passo | Requisição | O que é lido |
|---|---|---|
| 1 | `GET https://prd-core-alacarte.futuraproducoes.com.br/api/v1/version` | `app.url`, o endereço do armazenamento |
| 2 | `GET <armazenamento>/api/prepare/version.json.gz` | `version` e `path` |
| 3 | `GET <armazenamento>/<path>`, só quando `version` mudou | O catálogo: `titles`, `views` e outros |

O catálogo fica em memória, com a versão. Os passos 1 e 2 se repetem a cada chamada da rota.

### Como falha

`_get_json` levanta `CatalogUnavailable` em erro de rede, status HTTP de erro ou resposta que não é JSON.

| Situação | Resposta da API |
|---|---|
| Qualquer um dos três passos falha | `502 Falha ao buscar o catálogo do Belas Artes` |
| A seção `adicionados-recentemente` não existe no catálogo | `404 Seção de adicionados recentemente não encontrada` |
| O JSON muda de formato e falta uma chave esperada | Sem tratamento: `500 Internal Server Error` |

Se o passo 1 ou o 2 falha, a rota responde `502` mesmo que haja um catálogo válido em memória. O catálogo em memória não é usado como reserva.

## MongoDB Atlas

Arquivo: `config.py`.

`get_mongo_client()` cria o `MongoClient` com `serverSelectionTimeoutMS=5000` e chama `server_info()` para testar a conexão. O cliente é guardado em `_mongo_client` e reutilizado por todas as requisições. O comentário registra que o `MongoClient` mantém o próprio pool de conexões.

### Como falha

| Situação | Resposta da API |
|---|---|
| `PyMongoError` ao criar o cliente ou no teste de conexão | `DatabaseUnavailable`, que vira `503 MongoDB Atlas indisponível`. O cliente não é guardado, e a próxima requisição tenta conectar de novo. |
| Erro do pymongo numa operação, com o cliente já guardado | Sem tratamento específico: `500 Internal Server Error`. |

A segunda linha decorre da leitura do código: `DatabaseUnavailable` só é levantada dentro de `get_mongo_client`, e o cliente guardado é devolvido sem novo teste.
