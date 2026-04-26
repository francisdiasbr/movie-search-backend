from flask import request, jsonify
import math
import requests
from config import get_mongo_collection, RAPIDAPI_API_KEY
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

from favorites.scrapper import (
    get_movie_title,
    get_movie_year,
    get_movie_sm_plot,
    get_movie_quote,
    get_wikipedia_url,
    get_movie_country,
    get_movie_trivia,
    get_movie_plot_keywords,
    get_director,
    get_movie_genres,
    get_movie_principal_stars,
    get_writers,
)
from utils import sanitize_movie_data, sanitize_filters
from favorites.external_requests import get_magnet_link, get_subtitle_url


def favorite_movie(tconst):
    print(f"[FAVORITE] Iniciando processo de favoritar filme com tconst: {tconst}")
    
    if not tconst:
        print("[FAVORITE] Erro: tconst é obrigatório")
        return {"data": "tconst is required"}, 400

    collection_atlas = get_mongo_collection("favoritelist", use_atlas=True)
    collection_local = get_mongo_collection("favoritelist", use_atlas=False)

    if collection_atlas is None:
        print("[FAVORITE] Erro: coleção Atlas indisponível")
        return {"status": 503, "message": "Banco de dados Atlas indisponível"}, 503

    # Verificar em ambas as coleções
    print("[FAVORITE] Verificando se o filme já existe nas coleções...")
    existing_movie_atlas = collection_atlas.find_one({"tconst": tconst})
    existing_movie_local = collection_local.find_one({"tconst": tconst}) if collection_local is not None else None

    if existing_movie_atlas or existing_movie_local:
        print(f"[FAVORITE] Filme {tconst} já existe na lista de favoritos")
        return {"data": "Movie already listed"}, 409

    print("[FAVORITE] Obtendo título do filme...")
    movie_title = get_movie_title(tconst)
    if not movie_title:
        print(f"[FAVORITE] Título do filme {tconst} não encontrado no IMDB")
        return {"data": "Título do filme não encontrado no IMDB"}, 404

    print(f"[FAVORITE] Título obtido: {movie_title}")
    movie_data = {
        "primaryTitle": movie_title,
    }

    print("[FAVORITE] Iniciando coleta de dados em paralelo...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_func = {
            executor.submit(get_magnet_link, tconst): "magnet_link",
            executor.submit(get_subtitle_url, tconst): "subtitle_url",
            executor.submit(get_movie_country, tconst): "country",
            executor.submit(get_director, tconst): "director",
            executor.submit(get_movie_genres, tconst): "genres",
            executor.submit(get_movie_sm_plot, tconst): "plot",
            executor.submit(get_movie_plot_keywords, tconst): "plot_keywords",
            executor.submit(get_movie_quote, tconst): "quote",
executor.submit(get_movie_principal_stars, tconst): "stars",
            executor.submit(get_movie_trivia, tconst): "trivia",
            executor.submit(get_wikipedia_url, movie_title): "wiki",
            executor.submit(get_writers, tconst): "writers",
            executor.submit(get_movie_year, tconst): "startYear",
        }

        for future in as_completed(future_to_func):
            func_name = future_to_func[future]
            try:
                result = future.result()
                if result is not None:
                    movie_data[func_name] = result
                    print(f"[FAVORITE] Dados obtidos com sucesso para {func_name}")
                else:
                    print(f"[FAVORITE] Nenhum dado obtido para {func_name}")
            except Exception as e:
                print(f"[FAVORITE] Erro ao obter {func_name}: {e}")

    print("[FAVORITE] Adicionando dados básicos do filme...")
    # Adiciona dados básicos do filme
    movie_data.update({
        "tconst": tconst,
        "created_at": datetime.now().isoformat(),
        "references": []  # Array vazio para armazenar referências
    })

    # Remove campos vazios ou nulos para economizar espaço
    movie_data = {k: v for k, v in movie_data.items() if v is not None and v != ""}
    print(f"[FAVORITE] Dados finais do filme: {movie_data}")

    try:
        print("[FAVORITE] Iniciando inserção nas coleções...")
        result_atlas = collection_atlas.insert_one(movie_data.copy())
        movie_data["_id"] = str(result_atlas.inserted_id)
        if collection_local is not None:
            collection_local.insert_one(movie_data.copy())
        else:
            print("[FAVORITE] MongoDB local indisponível, inserido apenas no Atlas")
        print(f"[FAVORITE] Filme inserido com sucesso. ID: {movie_data['_id']}")
        return {"data": movie_data}, 201
    except Exception as e:
        print(f"[FAVORITE] Erro ao inserir filme: {e}")
        return {"status": 500, "message": "Erro ao inserir filme"}, 500


# Recupera um filme favoritado
def get_favorited_movie(tconst):
    collection = get_mongo_collection("favoritelist")

    if not tconst:
        return {"data": "tconst is required"}, 400

    try:
        movie = collection.find_one({"tconst": tconst})
        if movie:
            movie["_id"] = str(movie["_id"])
            return {"data": movie}, 200
        else:
            return {"data": "Movie not found"}, 404
    except Exception as e:
        print(f"{e}")
        return {"data": "Failed to retrieve movie"}, 500


# Edita um filme favoritado
def edit_favorited_movie(tconst, soundtrack=None, wiki=None, watched=None, references=None, magnet_link=None):
    collection = get_mongo_collection("favoritelist")
    update_data = {}

    print(f"[EDIT] Iniciando edição do filme tconst: {tconst}")
    print(f"[EDIT] Dados recebidos - soundtrack: {soundtrack}, wiki: {wiki}, watched: {watched}, references: {references}, magnet_link: {magnet_link}")

    # Busca o filme atual para manter as referências existentes
    current_movie = collection.find_one({"tconst": tconst})
    if not current_movie:
        print(f"[EDIT] Filme {tconst} não encontrado")
        return {"data": f"Movie {tconst} not found"}, 404

    print(f"[EDIT] Filme encontrado: {current_movie}")

    # Sempre inclui as referências no update_data
    if references is not None:
        update_data["references"] = references
        print(f"[EDIT] Novas referências a serem salvas: {references}")
        
        # Atualiza o blogpost se existir
        try:
            blogposts_collection = get_mongo_collection("blogposts")
            blogpost = blogposts_collection.find_one({"tconst": tconst})
            if blogpost:
                blogposts_collection.update_one(
                    {"tconst": tconst},
                    {"$set": {"references": references}}
                )
                print(f"[EDIT] Blogpost atualizado com novas referências: {references}")
        except Exception as e:
            print(f"[EDIT] Erro ao atualizar referências no blogpost: {e}")
    elif "references" in current_movie:
        # Se não houver novas referências, mantém as existentes
        current_references = current_movie["references"]
        update_data["references"] = current_references
        print(f"[EDIT] Mantendo referências existentes: {current_references}")

    if soundtrack is not None:
        update_data["soundtrack"] = soundtrack
        # Atualiza o blogpost se existir
        try:
            blogposts_collection = get_mongo_collection("blogposts")
            blogpost = blogposts_collection.find_one({"tconst": tconst})
            if blogpost:
                blogposts_collection.update_one(
                    {"tconst": tconst},
                    {"$set": {"spotify_album_url": soundtrack}}
                )
                print(f"[EDIT] Blogpost atualizado com nova URL do Spotify: {soundtrack}")
        except Exception as e:
            print(f"[EDIT] Erro ao atualizar blogpost: {e}")

    if wiki is not None:
        update_data["wiki"] = wiki
    if watched is not None:
        update_data["watched"] = watched
    if magnet_link is not None:
        update_data["magnet_link"] = magnet_link

    if not update_data:
        print("[EDIT] Nenhum campo para atualizar")
        return {"data": "No fields to update"}, 400

    try:
        print(f"[EDIT] Dados a serem atualizados: {update_data}")
        result = collection.update_one({"tconst": tconst}, {"$set": update_data})
        print(f"[EDIT] Resultado da atualização - matched: {result.matched_count}, modified: {result.modified_count}")
        
        # Verifica se o filme foi encontrado (matched_count > 0)
        if result.matched_count > 0:
            print(f"[EDIT] Filme {tconst} atualizado com sucesso")
            # Retorna os dados atualizados junto com os dados existentes
            updated_movie = collection.find_one({"tconst": tconst})
            updated_movie["_id"] = str(updated_movie["_id"])
            print(f"[EDIT] Dados atualizados retornados: {updated_movie}")
            return {"data": updated_movie}, 200
        else:
            print(f"[EDIT] Filme {tconst} não encontrado")
            return {"data": f"Movie {tconst} not found"}, 404
    except Exception as e:
        print(f"[EDIT] Erro ao atualizar filme: {e}")
        return {"data": "Failed to update favorited movie"}, 500


# Remove um filme dos favoritos
def delete_favorited_movie(tconst):
    collection_atlas = get_mongo_collection("favoritelist", use_atlas=True)
    collection_local = get_mongo_collection("favoritelist", use_atlas=False)

    try:
        # Tenta deletar em ambas as coleções
        result_atlas = collection_atlas.delete_one({"tconst": tconst})
        result_local = collection_local.delete_one({"tconst": tconst})

        # Verifica se foi deletado em AMBAS as coleções
        if result_atlas.deleted_count == 1 and result_local.deleted_count == 1:
            print(f"Filme {tconst} deletado com sucesso de ambas as coleções")
            return {"data": f"Movie {tconst} deleted"}, 200
        else:
            # Se falhou em alguma das coleções, informa qual
            error_msg = []
            if result_atlas.deleted_count == 0:
                error_msg.append("Atlas")
            if result_local.deleted_count == 0:
                error_msg.append("Local")

            error_locations = " and ".join(error_msg)
            print(f"Falha ao deletar filme {tconst} em: {error_locations}")
            return {
                "data": f"Failed to delete movie from {error_locations} database"
            }, 500
    except Exception as e:
        print(f"Erro ao deletar filme: {e}")
        return {"data": "Failed to delete listed movie"}, 500


# Recupera os filmes favoritados
def get_favorited_movies(
    filters={}, sorters=["_id", -1], page=1, page_size=0, search_term=""
):
    collection = get_mongo_collection("favoritelist")

    search_term = search_term or filters.get("search_term") or filters.get("tconst")

    # Filtra `search_term` no campo `tconst` ou `primaryTitle`
    if search_term:
        # Garante que search_term seja uma string para usar com $regex
        search_term_str = str(search_term) if search_term else ""
        if search_term_str:
            filters["$or"] = [
                {"tconst": search_term},
                {"primaryTitle": {"$regex": search_term_str, "$options": "i"}},
                {"director": {"$regex": search_term_str, "$options": "i"}},
            ]

    country = filters.get("country")
    if country:
        filters["country"] = country

    # Sanitiza os filtros para garantir que valores $regex sejam strings
    filters = sanitize_filters(filters)

    unique_countries = collection.distinct("country")
    unique_years = [
        int(year) for year in collection.distinct("startYear") 
        if year is not None and str(year).isdigit()
    ]

    try:
        total_documents = collection.count_documents(filters)
        skip = (page - 1) * page_size if page_size else 0
        query = collection.find(filters).sort(sorters[0], sorters[1]).skip(skip)
        if page_size:
            query = query.limit(page_size)
        items = list(query)

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        return {
            "total_documents": total_documents,
            "entries": items,
            "countries": unique_countries,
            "years": unique_years,
        }, 200
    except Exception as e:
        print(f"Error: {e}")
        return {"status": 500, "message": "Internal server error"}, 500
