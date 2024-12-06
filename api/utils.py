import math


# Substitui valores inválidos ou não-serializáveis por valores aceitáveis em JSON.
def sanitize_movie_data(movie_data):
    for key, value in movie_data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            movie_data[key] = None
        elif isinstance(value, list):
            movie_data[key] = [
                sanitize_movie_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, dict):
            movie_data[key] = sanitize_movie_data(value)
    return movie_data
