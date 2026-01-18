import time
import boto3
from concurrent.futures import ThreadPoolExecutor
from config import get_mongo_collection, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from utils import sanitize_filters

COLLECTION_NAME = "blogposts"

# Cria cliente S3 uma vez (reutilizável)
_s3_client = None

def get_s3_client():
    """Retorna cliente S3 reutilizável (singleton)"""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name="us-east-2",
        )
    return _s3_client


def get_first_image_url(tconst):
    """Retorna a URL da primeira imagem de um filme, buscando diretamente no S3."""
    BUCKET_NAME = "themoviesearch"
    
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"{tconst}/", MaxKeys=100)
        objects = response.get("Contents", [])
        
        if objects:
            # Filtra apenas imagens (não diretórios)
            image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".avif")
            image_objects = [
                obj for obj in objects
                if obj["Key"].lower().endswith(image_extensions) and not obj["Key"].endswith("/")
            ]
            
            if image_objects:
                # Ordena por LastModified (mais antiga = primeira inserida)
                image_objects.sort(key=lambda x: x.get("LastModified", 0))
                object_key = image_objects[0]["Key"]
                return f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{object_key}"
        
        return None
        
    except Exception as e:
        print(f"Erro ao buscar primeira imagem para {tconst}: {e}")
        return None


def get_blogpost_cards(filters={}, page=1, page_size=10):
    """
    Retorna apenas os dados necessários para exibir cards na Home:
    - tconst (id do filme)
    - primaryTitle (nome do filme)
    - created_at (data de criação)
    - imageUrl (URL da primeira imagem)
    """
    request_start = time.time()
    try:
        conn_start = time.time()
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)
        conn_time = (time.time() - conn_start) * 1000
        
        page = int(page)
        page_size = int(page_size)

        search_filters = {}
        text_fields = ["tconst", "primaryTitle"]

        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                # Copia outros filtros (pode incluir $or, $and, etc.)
                search_filters[key] = value

        # Sanitiza os filtros para garantir que valores $regex sejam strings
        search_filters = sanitize_filters(search_filters)

        count_start = time.time()
        total_documents = blogposts_collection.count_documents(search_filters)
        count_time = (time.time() - count_start) * 1000
        
        skip = (page - 1) * page_size

        projection = {
            "_id": 0,
            "tconst": 1,
            "primaryTitle": 1,
            "created_at": 1,
        }

        find_start = time.time()
        posts = list(
            blogposts_collection.find(search_filters, projection)
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )
        find_time = (time.time() - find_start) * 1000

        # Busca imagens em paralelo (muito mais rápido)
        tconsts = [post.get("tconst") for post in posts if post.get("tconst")]
        image_urls = {}
        images_time = 0
        
        if tconsts:
            images_start = time.time()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(get_first_image_url, tconst): tconst for tconst in tconsts}
                for future in futures:
                    tconst = futures[future]
                    try:
                        image_url = future.result()
                        if image_url:
                            image_urls[tconst] = image_url
                    except Exception as e:
                        print(f"Erro ao buscar imagem para {tconst}: {e}")
            images_time = (time.time() - images_start) * 1000
            print(f"[PERF] Buscar {len(tconsts)} imagens em paralelo: {images_time:.2f}ms (média: {images_time/len(tconsts):.2f}ms por imagem)")

        # Monta cards com imagens já buscadas
        cards = []
        for post in posts:
            tconst = post.get("tconst")
            
            card = {
                "tconst": tconst,
                "primaryTitle": post.get("primaryTitle"),
                "created_at": post.get("created_at"),
            }
            
            if tconst in image_urls:
                card["imageUrl"] = image_urls[tconst]
            
            cards.append(card)

        total_time = (time.time() - request_start) * 1000
        print(f"[PERF] get_blogpost_cards: total={total_time:.2f}ms | conn={conn_time:.2f}ms | count={count_time:.2f}ms | find={find_time:.2f}ms | images={images_time:.2f}ms")

        return {
            "total_documents": total_documents,
            "entries": cards,
        }, 200
    except Exception as e:
        total_time = (time.time() - request_start) * 1000 if 'request_start' in locals() else 0
        print(f"[PERF] get_blogpost_cards ERRO após {total_time:.2f}ms: {e}")
        return {"total_documents": 0, "entries": []}, 500

