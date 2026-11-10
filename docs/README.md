# Documentação técnica

Esta pasta descreve o backend do Movie Search em mais detalhe do que o [README](../README.md) da raiz. Tudo o que está aqui foi escrito a partir da leitura do código. Onde um comportamento depende de algo que o código não mostra (configuração do bucket, comportamento de um serviço externo), o texto diz "não verificado".

A API roda localmente (`python app.py`, porta 5000). O repositório não contém configuração de publicação.

## Documentos

| Documento | O que traz |
|---|---|
| [arquitetura.md](arquitetura.md) | As camadas do projeto, o caminho de uma requisição, a inicialização do app, as variáveis de ambiente, o tratamento de erros e o modelo de concorrência, com diagramas. |
| [modelo-de-dados.md](modelo-de-dados.md) | Cada coleção do MongoDB, campo a campo, com a origem de cada valor, e o que é gravado no S3. |
| [integracoes.md](integracoes.md) | Cada serviço externo: como é chamado, o que é guardado em cache, como falha e o que a API responde quando falha. |
| [testes.md](testes.md) | Como a suíte está organizada, o que é simulado, como rodar e o que o CI executa. |

## Funcionalidades

Um documento por módulo. Cada um descreve o que a funcionalidade faz, as rotas (método, caminho, parâmetros, corpo, resposta e códigos de status), o passo a passo interno e os casos de borda que o código trata.

| Documento | Módulo | O que cobre |
|---|---|---|
| [funcionalidades/favoritos.md](funcionalidades/favoritos.md) | `favorites/` | Lista de filmes favoritos: cadastro com coleta de dados no IMDB, leitura em inglês ou português, edição, remoção e busca. |
| [funcionalidades/palavras-chave.md](funcionalidades/palavras-chave.md) | `keywords/` | Palavras-chave favoritas e sugestão de filmes por palavra-chave ou nome de diretor. |
| [funcionalidades/resenhas.md](funcionalidades/resenhas.md) | `write_review/` | Resenhas autorais, uma por filme favorito. |
| [funcionalidades/imagens.md](funcionalidades/imagens.md) | `main_images/` | Envio, listagem e remoção de imagens de um filme no S3. |
| [funcionalidades/series.md](funcionalidades/series.md) | `series/` | Lista de séries de TV, preenchida pela API GraphQL do IMDB. |
| [funcionalidades/belas-artes.md](funcionalidades/belas-artes.md) | `belas_artes/` | Filmes adicionados recentemente ao Belas Artes à la Carte, com a nota do IMDB. |

## Convenções usadas nos documentos

- Todos os caminhos de rota são relativos ao prefixo `/api`, salvo indicação em contrário.
- `tconst` é o identificador de um título no IMDB, por exemplo `tt0053198`.
- Os exemplos de resposta mostram o formato real que o código produz. Os valores são ilustrativos.
