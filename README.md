# 🎬 movie-search-backend

> **📚 Para documentação completa do projeto, consulte o [README-DOCS.md](README-DOCS.md)**

## 📑 Índice
- [Instalação e Configuração](#instalação-e-configuração)
  - [Configuração do Ambiente](#1-configuração-do-ambiente)
  - [Navegador do Playwright](#2-navegador-do-playwright)
  - [Variáveis de Ambiente](#3-variáveis-de-ambiente)
- [Rodando o Projeto](#rodando-o-projeto)
- [Sessão do IMDB](#sessão-do-imdb)
- [Tradução para português](#tradução-para-português)
- [Sugestão por palavras-chave](#sugestão-por-palavras-chave)
- [Scripts de Automação](#scripts-de-automação)
- [Documentação da API](#documentação-da-api)

---

## Instalação e Configuração

### 1. Configuração do Ambiente

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```


### 2. Navegador do Playwright

O scraper do IMDB usa Playwright, que precisa do binário do Chromium baixado
separadamente do pacote Python:

```bash
./venv/bin/playwright install chromium
```

> ⚠️ Cada versão do Playwright exige uma revisão específica do Chromium. Se o
> scraper parar de funcionar com `Executable doesn't exist`, rode o comando
> acima de novo. A versão está fixada no `requirements.txt` justamente para
> evitar que isso aconteça sozinho num `pip install`.

### 3. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto a partir do modelo em `.env.example`. Só o MongoDB Atlas é obrigatório para a API subir; as chaves de AWS, RapidAPI e OpenSubtitles são exigidas apenas pelas rotas que as usam, que respondem `503` quando faltam.



## Rodando o Projeto

**Opção 1 - Com verificação da sessão do IMDB (recomendado):**
```bash
./verify_imdb.sh
```
Testa a sessão do IMDB, renova se necessário e sobe o servidor. Veja
[Sessão do IMDB](#sessão-do-imdb).

**Opção 2 - Direto:**
```bash
python app.py
```

A API estará disponível em `http://localhost:5000`



## Sessão do IMDB

O cadastro de um filme raspa dados do IMDB, que fica atrás do **AWS WAF**. O
scraper mantém um perfil do Chromium em `~/.cache/movie-search/imdb-profile`
com o token de verificação, reaproveitado entre execuções.

**Sintoma de sessão bloqueada:** ao adicionar um filme que existe, a API
responde `404` com *"Título do filme não encontrado no IMDB"*, e o log mostra:

```
ERROR favorites.scrapper: ... blocked by IMDB's AWS WAF after 3 attempts.
Run 'python imdb_verify.py' to renew the session.
```

**Como resolver:**

```bash
./verify_imdb.sh
```

O script para o backend, testa a sessão e — só se estiver bloqueada — abre uma
janela do navegador para você resolver a verificação manualmente. Depois sobe o
backend de novo. É o mesmo comando para o dia a dia e para quando dá problema.

Se quiser só a janela de verificação, sem mexer no servidor:
`python imdb_verify.py`.

> ⚠️ O Chromium tranca o diretório de perfil: o backend **precisa estar parado**
> enquanto a verificação acontece. O script cuida disso — rodar o
> `imdb_verify.py` na mão com o servidor no ar falha com erro de perfil em uso.

Na maior parte do tempo nada disso é necessário: o token vale dias, e desafios
pontuais do WAF são reprocessados automaticamente pelo próprio scraper antes de
ele desistir.




## Tradução para português

Os textos que o scraper tira do IMDB (sinopse, trivia, citações, gêneros e
palavras-chave) só existem em inglês. O backend gera uma versão em português
com o [Argos Translate](https://github.com/argosopentech/argos-translate), um
tradutor automático de código aberto que roda **offline, na própria máquina**:
é como um Google Tradutor local, sem chave de API, sem cota e sem custo.

- O modelo inglês→português (cerca de 100 MB) é baixado uma única vez, na
  primeira tradução, para `~/.local/share/argos-translate`. Depois disso não há
  mais rede nem download.
- A tradução acontece ao cadastrar o favorito e fica gravada no documento em
  `translations.pt`; o inglês original é mantido. Favoritos antigos são
  traduzidos sob demanda por `POST /api/favorites/<tconst>/translate`.
- O cliente escolhe o idioma na leitura: `GET /api/favorites/<tconst>?lang=pt`
  devolve os textos em português (ou em inglês, com `lang: "en"` na resposta,
  quando ainda não há tradução); sem o parâmetro vem o inglês.
- A qualidade é de tradução de máquina: dá para entender, mas puxa para o
  português de Portugal em alguns pontos e tropeça em expressões idiomáticas.

## Sugestão por palavras-chave

`POST /api/keywords/suggest-movies` busca os filmes que o IMDB associa a cada
palavra-chave usando a API GraphQL do próprio IMDB (a mesma da busca avançada
do site). Não precisa de sessão, chave nem do scraper, e fica fora do WAF. Um
filme que casa com várias palavras-chave aparece antes de um que casa com uma
só; no empate vale a popularidade do IMDB. Palavras-chave viram o identificador
do IMDB automaticamente (`French New Wave` → `french-new-wave`); nomes de
pessoas não são palavras-chave e voltam vazios.

## Scripts de Automação

O projeto inclui scripts para facilitar o desenvolvimento:

- **`./verify_imdb.sh`**: Testa a sessão do IMDB, renova se necessário e sobe o servidor
- **`python imdb_verify.py`**: Só a janela de verificação manual, sem mexer no servidor

## Documentação da API

A documentação interativa da API está disponível através do Swagger UI:

- **URL**: `http://localhost:5000/docs`
- Interface interativa para testar endpoints
- Documentação detalhada dos parâmetros e respostas

> **📚 Para informações completas sobre módulos, banco de dados e funcionalidades, consulte o [README-DOCS.md](README-DOCS.md)**