"""Formato único de resposta da API.

Todo endpoint devolve `{"data": <payload ou mensagem>}` junto do status HTTP,
na tupla que o flask-restx espera. Antes existiam três formatos convivendo -
`{"data": ...}`, `{"status": ..., "message": ...}` e `{"message": ...}` - e o
frontend precisava tentar mais de uma chave para achar a mensagem de erro.
"""


def ok(data, status=200):
    """Resposta de sucesso. `data` é o payload."""
    return {"data": data}, status


def fail(message, status):
    """Resposta de erro. `message` é o texto exibido ao usuário."""
    return {"data": message}, status
