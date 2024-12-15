import requests
from bs4 import BeautifulSoup

def get_google_images(query, num_images=5):
    """Busca as primeiras imagens em tamanho original do Google Imagens para um dado título."""
    search_url = f"https://www.google.com/search?tbm=isch&q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Encontra os elementos que contêm as URLs das imagens em tamanho original
    image_elements = soup.find_all('img', limit=num_images)
    image_urls = []
    
    for img in image_elements:
        # Tenta encontrar a URL da imagem em tamanho original
        if 'data-src' in img.attrs:
            image_urls.append(img['data-src'])
        elif 'src' in img.attrs:
            image_urls.append(img['src'])
    
    return image_urls 