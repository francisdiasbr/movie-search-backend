import sys
import os
import requests
from bs4 import BeautifulSoup
from time import sleep

# Adiciona o diretório pai ao path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_mongo_collection

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_movie_image_url(tconst):
    """Faz scraping da página do IMDb para pegar a URL da imagem principal"""
    url = f"https://www.imdb.com/title/{tconst}/"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"  ❌ Erro HTTP {response.status_code} para {tconst}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Tenta encontrar a imagem principal do filme
        # Método 1: Tag img com class específica do poster
        img_tag = soup.find("img", {"class": "ipc-image"})
        if img_tag and img_tag.get("src"):
            image_url = img_tag["src"]
            # Remove parâmetros de redimensionamento para pegar imagem maior
            if "._V1_" in image_url:
                image_url = image_url.split("._V1_")[0] + "._V1_SY1000_CR0,0,675,1000_AL_.jpg"
            return image_url
        
        # Método 2: Meta tag og:image
        meta_tag = soup.find("meta", {"property": "og:image"})
        if meta_tag and meta_tag.get("content"):
            return meta_tag["content"]
        
        # Método 3: Qualquer imagem com data-testid hero-media
        hero_img = soup.find("img", {"data-testid": "hero-media__poster"})
        if hero_img and hero_img.get("src"):
            return hero_img["src"]
        
        print(f"  ⚠️ Imagem não encontrada para {tconst}")
        return None
        
    except Exception as e:
        print(f"  ❌ Erro ao buscar imagem para {tconst}: {e}")
        return None


def enrich_recommendations_with_images():
    """Enriquece os documentos de recomendações com URLs das imagens"""
    collection = get_mongo_collection("recommendations")
    
    # Busca todos os documentos que não têm image_url ou que têm image_url vazia
    movies = list(collection.find({"$or": [
        {"image_url": {"$exists": False}},
        {"image_url": None},
        {"image_url": ""}
    ]}))
    
    if not movies:
        print("✅ Todos os filmes já possuem image_url!")
        return
    
    total = len(movies)
    print(f"\n🎬 Enriquecendo {total} filmes com URLs de imagens...\n")
    
    success_count = 0
    failed_count = 0
    
    for index, movie in enumerate(movies, 1):
        tconst = movie.get("tconst")
        title = movie.get("title", "Unknown")
        
        print(f"[{index}/{total}] {title} ({tconst})")
        
        image_url = get_movie_image_url(tconst)
        
        if image_url:
            # Atualiza o documento no MongoDB
            collection.update_one(
                {"tconst": tconst},
                {"$set": {"image_url": image_url}}
            )
            print(f"  ✅ Imagem salva: {image_url[:80]}...")
            success_count += 1
        else:
            failed_count += 1
        
        # Delay para não sobrecarregar o servidor do IMDb
        if index < total:
            sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"✅ Enriquecimento concluído!")
    print(f"   Sucessos: {success_count}")
    print(f"   Falhas: {failed_count}")
    print(f"   Total: {total}")
    print(f"{'='*60}\n")


def verify_images():
    """Verifica quantos filmes já têm imagens"""
    collection = get_mongo_collection("recommendations")
    
    total = collection.count_documents({})
    with_images = collection.count_documents({"image_url": {"$exists": True, "$ne": None, "$ne": ""}})
    without_images = total - with_images
    
    print(f"\n📊 Status das imagens:")
    print(f"   Total de filmes: {total}")
    print(f"   Com imagem: {with_images}")
    print(f"   Sem imagem: {without_images}")
    print()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ENRIQUECIMENTO DE RECOMENDAÇÕES COM IMAGENS")
    print("="*60)
    
    # Verifica status atual
    verify_images()
    
    # Confirma antes de executar
    response = input("Deseja continuar com o enriquecimento? (s/n): ")
    
    if response.lower() in ['s', 'sim', 'y', 'yes']:
        enrich_recommendations_with_images()
        verify_images()
    else:
        print("\n❌ Operação cancelada.\n")

