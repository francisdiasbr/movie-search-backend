from openai import OpenAI
import requests
import json
import os
from config import (
    get_mongo_collection, 
    SERPER_API_KEY
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def generate_review_summary(movie_title, snippets):
    combined_snippets = " ".join(snippets)

    messages = [
        {"role": "system", "content": "Você é um especialista em críticas de filmes e escreverá em português."},
        {"role": "user", "content": f"Baseado nas seguintes informações sobre o filme {movie_title}, escreva uma resenha {combined_snippets}"}
    ]

    response = client.chat.completions.create(
        model="gpt-4", 
        messages=messages,
        max_tokens=500,
        temperature=0.8
    )

    print(f"Response: {response}")
    return response.choices[0].message.content.strip()

def generate_plot_summary(movie_title, snippets):
    combined_snippets = " ".join(snippets)

    messages = [
        {"role": "system", "content": "Você é um especialista em críticas de filmes e escreverá em português."},
        {"role": "user", "content": f"Baseado nas seguintes informações sobre o filme {movie_title}, escreva o enredo do filme: {combined_snippets}, contando a história, sequencialmente. Após, inclua: principais atores e atrizes e seus respectivos papéis. Ao final, fale da importância histórica do filme e o contexto da época na qual o filme fora lançado. Bons sites incluem: wikipedia, imdb, rotten tomatoes, the guardian"}
    ]

    response = client.chat.completions.create(
        model="gpt-4", 
        messages=messages,
        max_tokens=1000,
        temperature=0.5
    )

    print(f"Response: {response}")
    return response.choices[0].message.content.strip()

def search_plot_with_serper(movie_title):
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": f"{movie_title} movie story",
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        data = response.json()
        plot_snippets = []
        for result in data.get('organic', []):
            if "story" in result.get('title', '').lower() or "story" in result.get('snippet', '').lower():
                plot_snippets.append(result.get('snippet'))
        if plot_snippets:
            plot_summary = generate_plot_summary(movie_title, plot_snippets)
            return plot_summary
        else:
            return "No plot found"

    else:
        print(f"Failed to retrieve plot: {response.status_code}")
        return "Error fetching plot"

def search_review_with_serper(movie_title):
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": f"{movie_title} movie review",
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY, 
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 200:
        data = response.json()
        review_snippets = []
        for result in data.get('organic', []):
            if "review" in result.get('title', '').lower() or "review" in result.get('snippet', '').lower():
                review_snippets.append(result.get('snippet'))
        if review_snippets:
            review_summary = generate_review_summary(movie_title, review_snippets)
            return review_summary
        else:
            return "No reviews found"
    else:
        print(f"Failed to retrieve review: {response.status_code}")
        return "Error fetching review"


def create_and_save_movie_review(tconst):
    favoritelist_collection = get_mongo_collection("favoritelist")
    reviewslist_collection = get_mongo_collection("reviewslist")

    movie = favoritelist_collection.find_one({"tconst": tconst})
    if not movie:
        return {"status": 404, "message": "Movie not found in favorites"}

    movie_title = movie.get("primaryTitle", "")
    if not movie_title:
        return {"status": 404, "message": "Movie title not found"}

    # Gera a resenha e o enredo usando Serper e OpenAI
    review = search_review_with_serper(movie_title)
    plot = search_plot_with_serper(movie_title)

    # Atualiza o documento no banco de dados com a resenha e o enredo
    review_data = {
        "tconst": tconst,
        "primaryTitle": movie_title,
        "review": review,
        "plot": plot
    }

    try:
        reviewslist_collection.insert_one(review_data)
        return {"status": 200, "message": "Review and plot created and saved successfully"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}


def get_movie_review(tconst):
    # Conecta-se à coleção de resenhas
    reviewslist_collection = get_mongo_collection("reviewslist")

    # Busca o filme na coleção reviewslist
    try:
        movie_review = reviewslist_collection.find_one({"tconst": tconst}, {"_id": 0})
        if movie_review:
            return {"status": 200, "data": movie_review}
        else:
            return {"status": 404, "message": "Review not found"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Failed to retrieve review"}
