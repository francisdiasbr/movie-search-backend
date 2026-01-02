# 🎬 movie-search-backend

> **📚 Para documentação completa do projeto, consulte o [README-DOCS.md](README-DOCS.md)**

## 📑 Índice
- [Instalação e Configuração](#instalação-e-configuração)
  - [Configuração do Ambiente](#1-configuração-do-ambiente)
  - [Variáveis de Ambiente](#2-variáveis-de-ambiente)
- [Rodando o Projeto](#rodando-o-projeto)
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


### 2. Variáveis de Ambiente

Configure as variáveis de ambiente: crie um arquivo .env na raiz do projeto com as variáveis de ambiente necessárias veja o modelo em env.example.



## Rodando o Projeto

**Opção 1 - Script automatizado (recomendado):**
```bash
runserver
```

**Opção 2 - Manual:**
```bash
python app.py
```

A API estará disponível em `http://localhost:5000`




## Scripts de Automação

O projeto inclui scripts para facilitar o desenvolvimento:

- **`initialize`**: Setup completo do projeto (cria venv, instala dependências e inicia servidor)
- **`runserver`**: Inicia o servidor rapidamente (sem reinstalar dependências)

## Documentação da API

A documentação interativa da API está disponível através do Swagger UI:

- **URL**: `http://localhost:5000/docs`
- Interface interativa para testar endpoints
- Documentação detalhada dos parâmetros e respostas

> **📚 Para informações completas sobre módulos, banco de dados e funcionalidades, consulte o [README-DOCS.md](README-DOCS.md)**