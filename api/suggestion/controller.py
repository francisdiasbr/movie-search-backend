from flask import request, jsonify
from openai import OpenAI 

import os

client = OpenAI(
  api_key = os.getenv("OPENAI_API_KEY")
)

def search_movie_suggestion():
  query = request.args.get("query")
  if not query:
    return jsonify({"error": "query parameter is required"}), 400
  
  try:
    response= client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Sugira filmes baseados na seguinte pesquisa: {query}"}
      ],
      max_tokens=3000
    )
    # print(response)

    if len(response.choices) > 0:
      choice = response.choices[0]
    
      if hasattr(choice, "message") and hasattr(choice.message, "content"):
        content = choice.message.content.strip()
        jsonify_content = jsonify({"data": content})
        # print(jsonify_content.get_json())
        return jsonify_content
      else:
        return jsonify({"error": "Invalid response format from OpenAI"}), 500
    
    else:
      return jsonify({"error": "No choices in response"}), 500

  except Exception as error:
    print(f"Exception: {error}")
    return jsonify({"error": str(error)}), 500

