# Imagens

Módulo: `main_images/` (`routes.py`, `controller.py`). Coleção: `main-images`. Armazenamento: AWS S3.

## O que faz

Permite anexar imagens a um filme. Cada imagem é reduzida e comprimida, enviada ao S3 com um nome sequencial por filme, e descrita por um documento no MongoDB com as legendas em inglês e em português. A listagem devolve a URL pública de cada imagem.

O `tconst` do caminho não é conferido contra os favoritos. As rotas aceitam qualquer valor.

## Rotas

Prefixo: `/api/main-images`.

| Método | Caminho | O que faz |
|---|---|---|
| `GET` | `/<tconst>` | Lista as imagens de um filme. |
| `POST` | `/<tconst>` | Envia uma imagem. |
| `DELETE` | `/<tconst>/<filename>` | Remove uma imagem. |

Nenhuma dessas rotas usa `@api.expect`, portanto as regras de `415` e `400` do flask-restx não se aplicam aqui.

### `POST /main-images/<tconst>`

Corpo `multipart/form-data`.

| Campo do formulário | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `file` | arquivo | sim | |
| `subtitle_en` | texto | não | `""` |
| `subtitle_pt` | texto | não | `""` |

Exemplo:

```bash
curl -X POST http://localhost:5000/api/main-images/tt0053198 \
  -F "file=@cena.jpg" \
  -F "subtitle_en=Antoine at the beach" \
  -F "subtitle_pt=Antoine na praia"
```

Exemplo de resposta `200`:

```json
{
  "message": "Upload realizado com sucesso",
  "object_name": "main-images/tt0053198/1.jpg",
  "filename": "1.jpg",
  "sequential_id": 1
}
```

| Status | Quando | Corpo |
|---|---|---|
| `200` | Imagem enviada e metadado gravado. | Como no exemplo. |
| `400` | O formulário não tem o campo `file`. | `{"message": "Arquivo não encontrado"}` |
| `500` | Qualquer exceção durante a otimização, o envio, a gravação das tags ou a gravação do metadado. | `{"message": "Erro ao fazer upload para S3"}` |
| `503` | Credenciais da AWS ausentes, ou MongoDB indisponível. | `{"message": "Credenciais AWS não configuradas"}` ou `{"message": "MongoDB Atlas indisponível"}` |

O sucesso responde `200`, e não `201`.

Passo a passo (`upload_image_to_s3`):

1. Cria o cliente S3. Sem credenciais, levanta `StorageUnavailable` antes de qualquer outra coisa.
2. Calcula o próximo id sequencial: busca a imagem do filme com o maior `sequential_id` e soma 1. A primeira imagem recebe 1.
3. Monta o nome: `<sequential_id><extensão>`, com a extensão do arquivo original em minúsculas. A chave no S3 é `main-images/<tconst>/<nome>`.
4. Define o `Content-Type` pela extensão, com `mimetypes.types_map`. Uma extensão desconhecida recebe `application/octet-stream`.
5. Otimiza a imagem com `utils.optimize_image(file, max_width=800, quality=85)`.
6. Envia com `upload_fileobj`.
7. Se há ao menos uma legenda, grava as duas como tags do objeto (`subtitle_en` e `subtitle_pt`), depois de passar por `sanitize_tag_value`.
8. Insere o metadado no Mongo, com as legendas originais.

Regras e casos de borda:

- **Otimização.** Imagens com mais de 800 px de largura são reduzidas para 800 px, mantendo a proporção. Imagens menores não são ampliadas. PNG continua PNG. JPEG é salvo com qualidade 85. Qualquer outro formato é salvo como JPEG. Se a otimização falha (por exemplo, o arquivo não é uma imagem), o arquivo original é enviado como veio.
- **Extensão e conteúdo.** O nome e o `Content-Type` vêm da extensão do arquivo original, enquanto o conteúdo pode ter sido convertido para JPEG na otimização. Um arquivo `.webp`, por exemplo, é gravado com bytes JPEG sob uma chave `.webp`.
- **Legendas nas tags.** `sanitize_tag_value` remove tudo que não é letra, número, sublinhado, espaço ou hífen, e corta o valor em 256 caracteres. O corte é feito no fim de uma palavra quando há mais de uma. O Mongo guarda a legenda original, sem cortes.
- **Sem legendas.** Se as duas legendas estão vazias, o objeto não recebe tags.
- **Falha parcial.** As etapas 5 a 8 estão no mesmo `try`. Se o envio dá certo e a gravação das tags ou do metadado falha, a resposta é `500` (ou `503` se foi o Mongo que caiu na abertura da conexão), e o objeto já enviado permanece no S3 sem metadado. Não há código que desfaça o envio.
- **Sequência.** O id vem do maior `sequential_id` existente. Depois de remover a imagem de maior id, o próximo envio reutiliza esse número e, se a extensão for a mesma, a mesma chave no S3.
- **Envios simultâneos.** O cálculo do id e a gravação do metadado são operações separadas, sem trava nem índice único. Dois envios simultâneos para o mesmo filme podem receber o mesmo id.

### `GET /main-images/<tconst>`

Exemplo de resposta `200`:

```json
{
  "images": [
    {
      "url": "https://themoviesearch.s3.us-east-2.amazonaws.com/main-images/tt0053198/1.jpg",
      "filename": "1.jpg",
      "sequential_id": 1,
      "subtitle_en": "Antoine at the beach",
      "subtitle_pt": "Antoine na praia"
    }
  ]
}
```

| Status | Quando | Corpo |
|---|---|---|
| `200` | Sempre que o Mongo responde. | `{"images": [...]}` |
| `503` | MongoDB indisponível. | |

Regras e casos de borda:

- A lista vem em ordem crescente de `sequential_id`.
- Um filme sem imagens recebe `200` com `{"images": []}`. O Swagger da rota declara um `404`, que o controller não produz.
- A rota lê só o Mongo. Não consulta o S3 e não precisa de credenciais.
- A URL é montada por `public_url` no formato `https://<bucket>.s3.<região>.amazonaws.com/main-images/<tconst>/<arquivo>`. Para que funcione, os objetos precisam ser legíveis publicamente. O código não define ACL no envio, então isso depende da configuração do bucket, que não foi verificada.

### `DELETE /main-images/<tconst>/<filename>`

| Status | Quando | Corpo |
|---|---|---|
| `200` | O S3 aceitou a remoção. | `{"message": "Imagem '1.jpg' deletada com sucesso"}` |
| `500` | O S3 devolveu um `ClientError`. | `{"message": "Erro ao deletar imagem"}` |
| `503` | Credenciais da AWS ausentes, ou MongoDB indisponível. | |

Passo a passo (`delete_image_from_s3`):

1. Chama `delete_object` no S3 com a chave `main-images/<tconst>/<filename>`.
2. Se o S3 devolve `ClientError`, responde `500` e mantém o metadado no Mongo.
3. Remove do Mongo o documento com esse `tconst` e esse `filename`.

Regras e casos de borda:

- O S3 é apagado antes do Mongo. Se o S3 falha, o metadado fica, e a imagem continua aparecendo na listagem.
- O controller não confere se a imagem existia. O Swagger declara um `404` que o código não produz. O `delete_one` do Mongo não tem o resultado checado.
- Só `ClientError` é capturado. Outras exceções do boto3 (por exemplo, falha de conexão) não têm tratamento e resultam em `500` genérico.
