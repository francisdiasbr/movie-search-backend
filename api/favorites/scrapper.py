from bs4 import BeautifulSoup
import requests

def get_movie_sm_plot(tconst):
    url = f"https://m.imdb.com/title/{tconst}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        plot_span = soup.find("span", {"data-testid": "plot-xs_to_m"})
        if plot_span:
            plot_text = plot_span.get_text()
            return plot_text if plot_text else "Plot not available"
    return "Plot not available"


def get_movie_poster(tconst):
    url = f"https://m.imdb.com/title/{tconst}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        poster_div = soup.find("div", {"class": "ipc-poster"})

        if poster_div:
            poster_img = poster_div.find("img", {"class": "ipc-image"})
            print('poster_img', poster_img)
            if poster_img:
                return poster_img["src"] if poster_img else "Poster not available"
    return "Poster not available"
            
def get_movie_country(tconst):
    url = f"https://m.imdb.com/title/{tconst}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        country_div = soup.find("div", {"data-testid": "title-details-section"})

        if country_div:
            origin_li = country_div.find("li", {"data-testid": "title-details-origin"})
            if origin_li:
                ul_inline_list = origin_li.find("ul", {"class": "ipc-inline-list"})
                if ul_inline_list:
                    country_link = ul_inline_list.find("a")
                    if country_link:
                        return country_link.get_text(strip=True)
            return "Country not available"
    return "Country not available"

def get_movie_trivia(tconst):
    url = f"https://m.imdb.com/title/{tconst}/trivia"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        content_divs = soup.find_all("div", {"class": "ipc-html-content-inner-div"})

        trivia = []
        for content_div in content_divs[:5]:
            trivia_text = content_div.get_text(separator=" ", strip=True)
            trivia.append(trivia_text)

        return "\n\n".join(trivia) if trivia else "Trivia not available"
    return "Trivia not available"


def get_movie_quote(tconst):
    url = f"https://m.imdb.com/title/{tconst}/quotes/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        content_divs = soup.find_all("div", {"class": "ipc-html-content-inner-div"})

        quotes = []
        for content_div in content_divs[:5]:  # Limita a captura às 2 primeiras divs
            ul_tag = content_div.find("ul")
            if ul_tag:
                quote_text = ul_tag.get_text(separator=" ", strip=True)
                quotes.append(quote_text)

        return "\n\n".join(quotes) if quotes else "Quote not available"
    return "Quote not available"


def get_wikipedia_url(movie_title):
    base_url = f"https://en.wikipedia.org/wiki/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    movie_title_formatted = movie_title.replace(" ", "_")
    url = f"{base_url}{movie_title_formatted}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return url 
    return "Wikipedia page not found"


def get_movie_plot_keywords(tconst):
    url = f"https://m.imdb.com/title/{tconst}/keywords"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        keywords_list = soup.find_all("li", {"data-testid": "list-summary-item"})

        # Extrai apenas strings para garantir que sejam serializáveis
        keywords = [item.find("a").get_text() for item in keywords_list if item.find("a")]

        # Retorna o array de strings diretamente
        return keywords if keywords else ["Keywords not available"]

    return ["Error retrieving keywords"]


def get_director(tconst):
    url = f"https://m.imdb.com/title/{tconst}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        director_section = soup.find("li", {"data-testid": "title-pc-principal-credit"})

        # Extrai o nome do diretor
        if director_section:
            director_name = director_section.find("a").get_text(strip=True)
            return director_name

    return "Director not available"