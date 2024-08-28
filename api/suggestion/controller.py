from flask import request, jsonify
from openai import OpenAI 
import os

client = OpenAI(
  api_key=os.getenv("OPENAI_API_KEY")
)

def search_movie_suggestion():
  # Obtém o parâmetro de query (opcionalmente descomentado para permitir entrada do usuário)
  # query = request.args.get("query")
  # if not query:
  #   return jsonify({"error": "query parameter is required"}), 400
  
  try:
    response = client.chat.completions.create(
      model="gpt-4",
      messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": (
          "Liste os filmes exibidos no Festival de Cinema de Toronto "
          "da última edição, incluindo seus códigos do IMDb. "
          "Apresente a resposta em formato JSON com a estrutura: "
          "[{'title': 'Nome do Filme', 'imdbId': 'Código do IMDb'}]."
        )}
      ],
      max_tokens=1000  # Ajuste para limitar o tamanho da resposta
    )

    if response.choices:
      choice = response.choices[0]

      # Verifica a presença de atributos para garantir a estrutura correta
      if hasattr(choice, "message") and hasattr(choice.message, "content"):
        content = choice.message.content.strip()
        
        # Tenta converter a resposta para JSON
        try:
          movie_data = eval(content)  # Use json.loads() se estiver seguro que a resposta é JSON
          return jsonify({"data": movie_data})
        except (SyntaxError, ValueError):
          # Se falhar, retorna o conteúdo como texto
          return jsonify({"data": content})
      else:
        return jsonify({"error": "Invalid response format from OpenAI"}), 500
    else:
      return jsonify({"error": "No choices in response"}), 500

  except Exception as error:
    print(f"Exception: {error}")
    return jsonify({"error": str(error)}), 500
