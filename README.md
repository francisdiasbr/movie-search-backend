# 🎬 movie-search-backend

> **📚 Para documentação completa do projeto, consulte o [README-DOCS.md](README-DOCS.md)**

## 📑 Índice
- [Instalação e Configuração](#instalação-e-configuração)
  - [Configuração do Ambiente](#1-configuração-do-ambiente)
  - [Navegador do Playwright](#2-navegador-do-playwright)
  - [Variáveis de Ambiente](#3-variáveis-de-ambiente)
- [Rodando o Projeto](#rodando-o-projeto)
- [Sessão do IMDB](#sessão-do-imdb)
- [Scripts de Automação](#scripts-de-automação)
- [Documentação da API](#documentação-da-api)

---

## Instalação e Configuração

### 1. Configuração do Ambiente

**Opção 1 - Script automatizado (recomendado):**
```bash
initialize
```

**Opção 2 - Manual:**
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

Configure as variáveis de ambiente: crie um arquivo .env na raiz do projeto com as variáveis de ambiente necessárias veja o modelo em env.example.



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
backend de novo.

```bash
./verify_imdb.sh              # testa e renova só se precisar
./verify_imdb.sh --force      # abre a janela de verificação de qualquer jeito
./verify_imdb.sh --no-start   # não reinicia o backend ao final
./verify_imdb.sh tt0017136    # usa outro título no teste
```

> ⚠️ O Chromium tranca o diretório de perfil: o backend **precisa estar parado**
> enquanto a verificação acontece. O script cuida disso — rodar o
> `imdb_verify.py` na mão com o servidor no ar falha com erro de perfil em uso.

Na maior parte do tempo nada disso é necessário: o token vale dias, e desafios
pontuais do WAF são reprocessados automaticamente pelo próprio scraper antes de
ele desistir.




## Scripts de Automação

O projeto inclui scripts para facilitar o desenvolvimento:

- **`initialize`**: Setup completo do projeto (cria venv, instala dependências e inicia servidor)
- **`runserver`**: Inicia o servidor rapidamente (sem reinstalar dependências)
- **`./verify_imdb.sh`**: Testa a sessão do IMDB, renova se necessário e sobe o servidor
- **`python imdb_verify.py`**: Só a janela de verificação manual, sem mexer no servidor

## Documentação da API

A documentação interativa da API está disponível através do Swagger UI:

- **URL**: `http://localhost:5000/docs`
- Interface interativa para testar endpoints
- Documentação detalhada dos parâmetros e respostas

> **📚 Para informações completas sobre módulos, banco de dados e funcionalidades, consulte o [README-DOCS.md](README-DOCS.md)**